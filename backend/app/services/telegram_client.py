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

    def send_photo(
        self,
        chat_id: str,
        photo_data: bytes,
        caption: str,
        filename: str = "cover.png",
    ) -> TelegramSendResult:
        """Send a photo with caption to a Telegram chat/channel.

        Args:
            chat_id: Target chat ID (@channel_name or numeric ID).
            photo_data: Raw image bytes.
            caption: HTML-formatted caption text (max 1024 chars).
            filename: Filename for the upload.

        Returns:
            TelegramSendResult with success status and message_id or error.
        """
        url = TELEGRAM_API.format(token=self.bot_token, method="sendPhoto")

        # Telegram photo caption limit is 1024 chars
        if len(caption) > 1024:
            caption = caption[:1021] + "..."

        log.info(
            "telegram.sending_photo",
            chat_id=chat_id,
            caption_len=len(caption),
            photo_size=len(photo_data),
        )

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    url,
                    data={
                        "chat_id": chat_id,
                        "caption": caption,
                        "parse_mode": "HTML",
                    },
                    files={
                        "photo": (filename, photo_data, "image/png"),
                    },
                )

            data = resp.json()

            if resp.status_code == 200 and data.get("ok"):
                message = data["result"]
                message_id = str(message.get("message_id", ""))
                log.info("telegram.photo_sent", chat_id=chat_id, message_id=message_id)
                return TelegramSendResult(
                    success=True,
                    message_id=message_id,
                    raw_response=data,
                )

            error_msg = data.get("description", str(data))
            retryable = resp.status_code in (429, 500, 502, 503)
            log.error(
                "telegram.photo_api_error",
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
            log.error("telegram.photo_http_error", error=str(e))
            return TelegramSendResult(
                success=False,
                error=str(e),
                retryable=True,
            )

    def get_message_stats(
        self, chat_id: str, message_id: str
    ) -> dict | None:
        """Fetch view/reaction/forward/comment counts for a channel post.

        Uses Telegram's public embed page to scrape views, reactions, forwards.
        Uses Bot API to count comments via linked discussion group.

        Args:
            chat_id: Channel username (e.g. "@ecocyprus") or numeric ID.
            message_id: Telegram message ID.

        Returns:
            Dict with views, reactions, forwards, comments or None on failure.
        """
        # Resolve username from chat_id
        username = chat_id.lstrip("@") if chat_id.startswith("@") else None
        linked_chat_id = None

        if not username:
            # Try to get channel info via Bot API for numeric chat_id
            try:
                url = TELEGRAM_API.format(token=self.bot_token, method="getChat")
                with httpx.Client(timeout=10) as client:
                    resp = client.post(url, json={"chat_id": chat_id})
                data = resp.json()
                if data.get("ok"):
                    username = data["result"].get("username")
                    linked_chat_id = data["result"].get("linked_chat_id")
            except Exception as e:
                log.warning("telegram.stats.get_chat_failed", error=str(e))

        if not username:
            log.warning("telegram.stats.no_username", chat_id=chat_id)
            return None

        # Scrape the embed page
        embed_url = f"https://t.me/{username}/{message_id}?embed=1&mode=tme"
        try:
            with httpx.Client(timeout=15, follow_redirects=True) as client:
                resp = client.get(embed_url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; ContenZavod/1.0)"
                })
            html = resp.text

            views = 0
            reactions = 0
            forwards = 0
            comments = 0

            # Parse views: <span class="tgme_widget_message_views">1.2K</span>
            views_match = re.search(
                r'class="tgme_widget_message_views"[^>]*>([^<]+)', html
            )
            if views_match:
                views = _parse_tg_number(views_match.group(1).strip())

            # Parse forwards/shares
            forwards_match = re.search(
                r'class="tgme_widget_message_forwards"[^>]*>([^<]+)', html
            )
            if forwards_match:
                forwards = _parse_tg_number(forwards_match.group(1).strip())

            # Parse reactions — actual HTML structure:
            # <span class="tgme_reaction"><i class="emoji">😢</i>1</span>
            # Sum all reaction counts across all emoji types
            reaction_matches = re.findall(
                r'class="tgme_reaction"[^>]*>.*?</i>\s*(\d[\d.,KkMm]*)\s*</span>',
                html, re.DOTALL
            )
            for r_text in reaction_matches:
                reactions += _parse_tg_number(r_text.strip())

            # If no individual reactions found, try alternative format
            # Some embeds use: <span class="tgme_widget_message_reactions">
            if reactions == 0:
                alt_match = re.findall(
                    r'class="tgme_reaction"[^>]*>[^<]*<[^>]*>[^<]*</[^>]*>\s*'
                    r'(\d[\d.,KkMm]*)',
                    html
                )
                for r_text in alt_match:
                    reactions += _parse_tg_number(r_text.strip())

            # Try to get comment count via Bot API
            # Telegram channels with discussion groups have comments
            comments = self._get_comment_count(chat_id, message_id)

            log.info(
                "telegram.stats.scraped",
                username=username,
                message_id=message_id,
                views=views,
                reactions=reactions,
                forwards=forwards,
                comments=comments,
            )
            return {
                "views": views,
                "reactions": reactions,
                "forwards": forwards,
                "comments": comments,
            }

        except Exception as e:
            log.warning("telegram.stats.scrape_failed", error=str(e), url=embed_url)
            return None

    def _get_comment_count(self, chat_id: str, message_id: str) -> int:
        """Get comment count for a channel post via Bot API.

        Uses getChat to find linked discussion group, then
        checks the message's reply thread for replies.

        Args:
            chat_id: Channel chat ID or @username.
            message_id: Message ID in the channel.

        Returns:
            Number of comments (0 if no discussion group or error).
        """
        try:
            # Get the channel info to find linked discussion group
            url = TELEGRAM_API.format(token=self.bot_token, method="getChat")
            with httpx.Client(timeout=10) as client:
                resp = client.post(url, json={"chat_id": chat_id})
            data = resp.json()

            if not data.get("ok"):
                return 0

            linked_chat_id = data["result"].get("linked_chat_id")
            if not linked_chat_id:
                return 0  # No discussion group linked

            # Use getChatMemberCount as a proxy — not ideal
            # Better: use forwardMessage trick or getForumTopicIconStickers
            # For now, we can try getUpdates on the discussion group
            # Actually, the best approach: use Telegram's web embed
            # for the discussion group to count replies
            discuss_url = (
                f"https://t.me/{chat_id.lstrip('@')}/{message_id}"
                f"?comment=1&embed=1&mode=tme"
            )
            with httpx.Client(timeout=10, follow_redirects=True) as client:
                resp = client.get(discuss_url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; ContenZavod/1.0)"
                })

            # Look for comment count in the embed
            # Structure: <a class="tgme_widget_message_comments">Leave a comment</a>
            # or: <span class="tgme_widget_message_comments_count">5</span>
            comment_match = re.search(
                r'comments["\s][^>]*>(\d[\d.,KkMm]*)\s*(?:comment|комментар)',
                resp.text, re.IGNORECASE
            )
            if comment_match:
                return _parse_tg_number(comment_match.group(1))

            return 0

        except Exception as e:
            log.debug("telegram.stats.comments_failed", error=str(e))
            return 0


def _parse_tg_number(text: str) -> int:
    """Parse Telegram's abbreviated numbers like '1.2K', '3.5M'."""
    text = text.strip().replace(",", ".").upper()
    if not text:
        return 0
    try:
        if text.endswith("K"):
            return int(float(text[:-1]) * 1000)
        if text.endswith("M"):
            return int(float(text[:-1]) * 1_000_000)
        return int(float(text))
    except (ValueError, TypeError):
        return 0
