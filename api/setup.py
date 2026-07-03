import asyncio
import logging
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from telegram import Update

from bot_core import build_application
from config import get_bot_token, get_setup_secret, get_webhook_secret, get_webhook_url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _respond(handler: BaseHTTPRequestHandler, status: int, body: str) -> None:
    handler.send_response(status)
    handler.send_header("Content-Type", "text/plain; charset=utf-8")
    handler.end_headers()
    handler.wfile.write(body.encode("utf-8"))


async def _register_webhook() -> str:
    application = build_application()
    webhook_url = get_webhook_url()
    secret = get_webhook_secret()

    async with application:
        await application.bot.set_webhook(
            url=webhook_url,
            secret_token=secret or None,
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )
        webhook_info = await application.bot.get_webhook_info()

    lines = [
        "Webhook успешно установлен.",
        f"URL: {webhook_info.url}",
        f"Pending updates: {webhook_info.pending_update_count}",
    ]
    if webhook_info.last_error_message:
        lines.append(f"Last error: {webhook_info.last_error_message}")
    return "\n".join(lines)


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        query = parse_qs(urlparse(self.path).query)
        provided_secret = query.get("secret", [""])[0]
        expected_secret = get_setup_secret()

        if not expected_secret or provided_secret != expected_secret:
            _respond(self, 403, "Forbidden. Укажите ?secret=ваш_SETUP_SECRET")
            return

        try:
            get_bot_token()
            message = asyncio.run(_register_webhook())
            _respond(self, 200, message)
        except Exception as exc:
            logger.exception("Setup error")
            _respond(self, 500, f"Ошибка: {exc}")
