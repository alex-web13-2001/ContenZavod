"""Publish tasks — send approved adaptations to platform channels.

Tasks:
    publish_to_telegram  — Send a message to a Telegram channel using Bot API.
"""

import uuid
from datetime import datetime, timezone

import httpx
import structlog
from celery import shared_task
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_sync_session
from app.models.channel import Channel
from app.models.channel_adaptation import ChannelAdaptation
from app.models.publish_job import PublishJob

log = structlog.get_logger()

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _markdown_to_telegram_html(text: str) -> str:
    """Convert simple markdown to Telegram-safe HTML.

    Telegram supports: <b>, <i>, <a>, <code>, <pre>.
    We convert common markdown patterns.
    """
    import re

    # Bold: **text** or __text__
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)

    # Italic: *text* or _text_
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)

    # Links: [text](url)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)

    # Strip markdown headers: ## Header → Header
    text = re.sub(r"^#{1,3}\s*", "", text, flags=re.MULTILINE)

    # Strip section markers like [Хук: 0-5 секунд]
    text = re.sub(r"^\[.+?\]\s*", "", text, flags=re.MULTILINE)

    return text.strip()


@shared_task(
    name="workers.publish_tasks.publish_to_telegram",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def publish_to_telegram(self, publish_job_id: str):
    """Publish an adaptation to Telegram.

    Flow:
        1. Load PublishJob → ChannelAdaptation → Channel
        2. Extract bot_token and chat_id from channel.config
        3. Format the message (headline + body → HTML)
        4. Send via Telegram Bot API
        5. Update PublishJob status → published
        6. Update ChannelAdaptation status → published
    """
    with get_sync_session() as session:
        job = session.get(PublishJob, uuid.UUID(publish_job_id))
        if not job:
            log.error("publish.job_not_found", job_id=publish_job_id)
            return {"status": "error", "detail": "Job not found"}

        # Mark as publishing
        job.status = "publishing"
        session.commit()

        adaptation = session.get(ChannelAdaptation, job.content_id)
        if not adaptation:
            job.status = "failed"
            job.error_message = "Adaptation not found"
            session.commit()
            return {"status": "error", "detail": "Adaptation not found"}

        channel = session.get(Channel, job.channel_id)
        if not channel:
            job.status = "failed"
            job.error_message = "Channel not found"
            session.commit()
            return {"status": "error", "detail": "Channel not found"}

        # Extract credentials
        config = channel.config or {}
        bot_token = config.get("bot_token", "")
        chat_id = config.get("chat_id", "")

        if not bot_token or not chat_id:
            job.status = "failed"
            job.error_message = "Channel config missing bot_token or chat_id"
            session.commit()
            log.error(
                "publish.missing_config",
                channel_id=str(channel.id),
                channel_name=channel.name,
            )
            return {"status": "error", "detail": "Missing bot_token or chat_id"}

        # Format message
        headline = adaptation.headline or ""
        body = adaptation.body or ""

        # Build the message: bold headline + body
        raw_text = f"**{headline}**\n\n{body}" if headline else body
        html_text = _markdown_to_telegram_html(raw_text)

        # Telegram limit: 4096 chars
        if len(html_text) > 4096:
            html_text = html_text[:4090] + "..."

        log.info(
            "publish.sending",
            channel=channel.name,
            chat_id=chat_id,
            text_len=len(html_text),
        )

        try:
            url = TELEGRAM_API.format(token=bot_token, method="sendMessage")
            with httpx.Client(timeout=30) as client:
                resp = client.post(
                    url,
                    json={
                        "chat_id": chat_id,
                        "text": html_text,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": False,
                    },
                )

            data = resp.json()

            if resp.status_code == 200 and data.get("ok"):
                # Success
                message = data["result"]
                job.status = "published"
                job.published_at = datetime.now(timezone.utc)
                job.platform_post_id = str(message.get("message_id", ""))
                job.platform_response = data
                job.error_message = None

                adaptation.status = "published"

                session.commit()

                log.info(
                    "publish.success",
                    channel=channel.name,
                    message_id=job.platform_post_id,
                )
                return {
                    "status": "published",
                    "message_id": job.platform_post_id,
                    "chat_id": chat_id,
                }
            else:
                # API error
                error_msg = data.get("description", str(data))
                job.status = "failed"
                job.error_message = error_msg
                job.retry_count += 1
                job.platform_response = data
                session.commit()

                log.error(
                    "publish.api_error",
                    channel=channel.name,
                    error=error_msg,
                    status_code=resp.status_code,
                )

                # Retry on rate limit (429) or server error (5xx)
                if resp.status_code in (429, 500, 502, 503):
                    raise self.retry(countdown=60 * (self.request.retries + 1))

                return {"status": "failed", "error": error_msg}

        except httpx.HTTPError as e:
            job.status = "failed"
            job.error_message = str(e)
            job.retry_count += 1
            session.commit()

            log.error("publish.http_error", error=str(e))
            raise self.retry(exc=e, countdown=30)
