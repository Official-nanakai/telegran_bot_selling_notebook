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

from app import build_application
from config import get_webhook_secret

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _respond(handler: BaseHTTPRequestHandler, status: int, body: str, content_type: str = "text/plain") -> None:
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
        _respond(self, 200, "Telegram bot webhook is running.")
