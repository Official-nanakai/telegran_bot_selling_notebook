import asyncio
import json
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


def _respond(
    handler: BaseHTTPRequestHandler,
    status: int,
    body: str,
    content_type: str = "text/plain; charset=utf-8",
) -> None:
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.end_headers()
    handler.wfile.write(body.encode("utf-8"))


async def _process_update(raw_body: bytes) -> None:
    payload = json.loads(raw_body.decode("utf-8"))
    application = build_application()

    async with application:
        update = Update.de_json(payload, application.bot)
        await application.process_update(update)


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


def _is_setup_request(path: str, query: dict[str, list[str]]) -> bool:
    return path.rstrip("/").endswith("/setup") or query.get("action") == ["setup"]


class handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        expected_secret = get_webhook_secret()
        if expected_secret:
            received_secret = self.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
            if received_secret != expected_secret:
                _respond(self, 403, "Forbidden")
                return

        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length)

        try:
            asyncio.run(_process_update(raw_body))
            _respond(self, 200, "OK")
        except Exception:
            logger.exception("Webhook error")
            _respond(self, 500, "Internal Server Error")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if _is_setup_request(parsed.path, query):
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
            return

        _respond(self, 200, "Telegram bot webhook is running.")
