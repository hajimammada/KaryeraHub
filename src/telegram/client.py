"""
Telegram Bot API Client.
Provides safe HTTP communication with Telegram servers.
"""
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)

class TelegramClient:
    """Wrapper for Telegram Bot HTTP API."""

    API_BASE = "https://api.telegram.org/bot"

    def __init__(self, bot_token: str):
        self.bot_token = bot_token.strip()
        self.endpoint = f"{self.API_BASE}{self.bot_token}"

    def get_me(self) -> Dict[str, Any]:
        """Fetches the bot's identity and checks token validity."""
        url = f"{self.endpoint}/getMe"
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("ok"):
                    return data.get("result", {})
                else:
                    raise ValueError(f"Telegram API returned not ok: {data}")
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="ignore")
            logger.error(f"Telegram getMe failed (HTTP {e.code}): {err_msg}")
            raise
        except Exception as e:
            logger.error(f"Telegram connection error in getMe: {e}")
            raise

    def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "HTML",
        disable_web_page_preview: bool = True
    ) -> Dict[str, Any]:
        """
        Sends a message to the specified chat or channel.
        """
        url = f"{self.endpoint}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview
        }

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                if result.get("ok"):
                    logger.debug(f"Message successfully sent to {chat_id}")
                    return result.get("result", {})
                else:
                    logger.error(f"Telegram sendMessage returned error: {result}")
                    return {}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            logger.error(f"Telegram HTTP Error {e.code} while sending to {chat_id}: {err_body}")
            raise RuntimeError(f"Telegram HTTP {e.code}: {err_body}")
        except Exception as e:
            logger.error(f"Failed to send Telegram message to {chat_id}: {e}")
            raise
