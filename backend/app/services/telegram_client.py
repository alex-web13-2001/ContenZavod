"""Telegram Bot API client.

Thin wrapper around Telegram Bot API for sending messages.
Handles formatting, character limits, and error classification.
"""

import re

import httpx
import structlog

log = structlog.get_logger()

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"

# Telegram message limit
MAX_MESSAGE_LENGTH = 4096


def markdown_to_telegram_html(text: str) -> str:
    """Convert simple markdown to Telegram-safe HTML.

    Telegram supports: <b>, <i>, <a>, <code>, <pre>.
    We convert common markdown patterns while stripping unsupported ones.

    Args:
        text: Markdown-formatted text.

    Returns:
        HTML string safe for Telegram's parse_mode="HTML".
    """
    # Bold: **text** or __text__
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)

    # Italic: *text* or _text_ (not inside bold)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)

    # Links: [text](url)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)

    # Strip markdown headers: ## Header → Header
    text = re.sub(r"^#{1,3}\s*", "", text, flags=re.MULTILINE)

    # Strip section markers like [Хук: 0-5 секунд]
    text = re.sub(r"^\[.+?\]\s*", "", text, flags=re.MULTILINE)

    return text.strip()


class TelegramSendResult:
    """Result of a Telegram send operation."""

    def __init__(
        self,
        success: bool,
        message_id: str | None = None,
        error: str | None = None,
        status_code: int | None = None,
        raw_response: dict | None = None,
        retryable: bool = False,
    ):
        self.success = success
        self.message_id = message_id
        self.error = error
        self.status_code = status_code
        self.raw_response = raw_response or {}
        self.retryable = retryable


class TelegramClient:
    """Client for Telegram Bot API.

    Sends messages to channels/chats using a bot token.
    Handles text formatting and length constraints.
    """

    def __init__(self, bot_token: str, timeout: int = 30):
        """Initialize the client.

        Args:
            bot_token: Telegram bot token from @BotFather.
            timeout: HTTP request timeout in seconds.
        """
        self.bot_token = bot_token
        self.timeout = timeout

    def format_post(self, headline: str, body: str) -> str:
        """Format headline + body into a Telegram-ready HTML message.

        Args:
            headline: Post headline (will be bolded).
            body: Post body in markdown.

        Returns:
            HTML string within Telegram's 4096-char limit.
        """
        raw_text = f"**{headline}**\n\n{body}" if headline else body
        html_text = markdown_to_telegram_html(raw_text)

        if len(html_text) > MAX_MESSAGE_LENGTH:
            html_text = html_text[: MAX_MESSAGE_LENGTH - 3] + "..."

        return html_text

    def send_message(self, chat_id: str, text: str) -> TelegramSendResult:
        """Send a text message to a Telegram chat/channel.

        Args:
            chat_id: Target chat ID (@channel_name or numeric ID).
            text: HTML-formatted message text.

        Returns:
            TelegramSendResult with success status and message_id or error.
        """
        url = TELEGRAM_API.format(token=self.bot_token, method="sendMessage")

        log.info(
            "telegram.sending",
            chat_id=chat_id,
            text_len=len(text),
        )

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    url,
                    json={
                        "chat_id": chat_id,
                        "text": text,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": False,
                    },
                )

            data = resp.json()

            if resp.status_code == 200 and data.get("ok"):
                message = data["result"]
                message_id = str(message.get("message_id", ""))
                log.info("telegram.sent", chat_id=chat_id, message_id=message_id)
                return TelegramSendResult(
                    success=True,
                    message_id=message_id,
                    raw_response=data,
                )

            error_msg = data.get("description", str(data))
            retryable = resp.status_code in (429, 500, 502, 503)
            log.error(
                "telegram.api_error",
                chat_id=chat_id,
                error=error_msg,
                status_code=resp.status_code,
            )
            return TelegramSendResult(
                success=False,
                error=error_msg,
                status_code=resp.status_code,
                raw_response=data,
                retryable=retryable,
            )

        except httpx.HTTPError as e:
            log.error("telegram.http_error", error=str(e))
            return TelegramSendResult(
                success=False,
                error=str(e),
                retryable=True,
            )
