"""Publish service — orchestrates content publishing to channels.

Manages the lifecycle of PublishJobs:
    load → validate → format → send → update status.

Can be called from Celery tasks, API endpoints, or tests.
"""

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy.orm import Session

from app.models.channel import Channel
from app.models.channel_adaptation import ChannelAdaptation
from app.models.publish_job import PublishJob
from app.services.telegram_client import TelegramClient

log = structlog.get_logger()


class PublishError(Exception):
    """Non-retryable publish error."""


class PublishRetryError(Exception):
    """Retryable publish error — task should retry."""


class PublishService:
    """Service for publishing adapted content to channels.

    Handles the full publish lifecycle: loading data, formatting,
    sending via platform clients, and updating statuses.
    Works with a sync SQLAlchemy session (for Celery workers).
    """

    def __init__(self, session: Session):
        """Initialize with a database session.

        Args:
            session: Sync SQLAlchemy session.
        """
        self.session = session

    def execute(self, publish_job_id: str) -> dict:
        """Execute a publish job end-to-end.

        Args:
            publish_job_id: UUID of the PublishJob to execute.

        Returns:
            Dict with status, message_id, and chat_id on success.

        Raises:
            PublishError: On non-retryable failures.
            PublishRetryError: On transient failures that should be retried.
        """
        job = self._load_job(publish_job_id)
        adaptation = self._load_adaptation(job)
        channel = self._load_channel(job)

        bot_token, chat_id = self._validate_config(channel, language=adaptation.language)
        content_format = adaptation.content_format or "short_post"
        message_html = self._format_message(adaptation, bot_token, content_format)

        # Flash posts NEVER have covers
        if content_format == "flash":
            cover_data = None
        else:
            # Check for cover image: adaptation-level first, then material fallback
            cover_data = self._get_cover_image(adaptation)

        if cover_data:
            result = self._send_with_photo(bot_token, chat_id, message_html, cover_data)
        else:
            result = self._send(
                bot_token, chat_id, message_html,
                disable_web_page_preview=(content_format == "flash"),
            )

        self._mark_published(job, adaptation, result, chat_id)
        return result

    def _load_job(self, job_id: str) -> PublishJob:
        """Load and validate the publish job."""
        job = self.session.get(PublishJob, uuid.UUID(job_id))
        if not job:
            raise PublishError(f"PublishJob {job_id} not found")

        job.status = "publishing"
        self.session.commit()
        return job

    def _load_adaptation(self, job: PublishJob) -> ChannelAdaptation:
        """Load the adaptation linked to the job."""
        adaptation = self.session.get(ChannelAdaptation, job.content_id)
        if not adaptation:
            self._fail_job(job, "Adaptation not found")
            raise PublishError("Adaptation not found")
        return adaptation

    def _load_channel(self, job: PublishJob) -> Channel:
        """Load the channel linked to the job."""
        channel = self.session.get(Channel, job.channel_id)
        if not channel:
            self._fail_job(job, "Channel not found")
            raise PublishError("Channel not found")
        return channel

    def _validate_config(self, channel: Channel, language: str | None = None) -> tuple[str, str]:
        """Extract and validate bot_token and chat_id from channel config.

        Supports per-language endpoints: if config.endpoints.<lang>.chat_id exists,
        it is used instead of the top-level chat_id.  This enables publishing
        the same content to different Telegram chats per language.

        Config format::

            {
                "bot_token": "123:ABC...",
                "chat_id": "@fallback",           # default
                "endpoints": {
                    "ru": {"chat_id": "@chan_ru"},
                    "en": {"chat_id": "@chan_en"},
                    "el": {"chat_id": "@chan_el"}
                }
            }

        Args:
            channel: Channel model instance.
            language: Target language code (e.g. "ru", "en", "el").
                      Used to resolve per-language chat_id from endpoints.

        Returns:
            Tuple of (bot_token, chat_id).

        Raises:
            PublishError: If config is incomplete.
        """
        config = channel.config or {}
        bot_token = config.get("bot_token", "")

        # Per-language endpoint resolution
        chat_id = ""
        endpoints = config.get("endpoints", {})
        if language and language in endpoints:
            chat_id = endpoints[language].get("chat_id", "")
            log.debug(
                "publish.resolved_endpoint",
                language=language,
                chat_id=chat_id,
                channel=channel.name,
            )

        # Fallback to top-level chat_id
        if not chat_id:
            chat_id = config.get("chat_id", "")

        if not bot_token or not chat_id:
            log.error(
                "publish.missing_config",
                channel_id=str(channel.id),
                channel_name=channel.name,
                language=language,
            )
            raise PublishError(
                f"Channel '{channel.name}' missing bot_token or chat_id"
                f" for language '{language or 'default'}'"
            )

        return bot_token, chat_id

    def _format_message(
        self, adaptation: ChannelAdaptation, bot_token: str,
        content_format: str = "short_post",
    ) -> str:
        """Format the adaptation into a Telegram-ready HTML message.

        Args:
            adaptation: The content adaptation to format.
            bot_token: Bot token for TelegramClient initialization.
            content_format: Content format (flash, short_post, longread).

        Returns:
            HTML-formatted message string.
        """
        client = TelegramClient(bot_token)
        return client.format_post(
            headline=adaptation.headline or "",
            body=adaptation.body or "",
            content_format=content_format,
        )

    def _get_cover_image(self, adaptation) -> bytes | None:
        """Try to load cover image from MinIO.

        Priority: adaptation cover → material cover (fallback).
        Returns image bytes if a cover exists, None otherwise.
        """
        cover_url = None

        # 1. Check adaptation-level cover first
        if getattr(adaptation, 'cover_image_url', None) and getattr(adaptation, 'cover_status', None) == 'ready':
            cover_url = adaptation.cover_image_url

        # 2. Fallback: material-level cover
        if not cover_url:
            from app.models.material import RawMaterial
            material = self.session.get(RawMaterial, adaptation.material_id)
            if material:
                meta = material.metadata_ or {}
                cover_info = meta.get("cover_image", {})
                url = cover_info.get("url", "")
                if url and meta.get("cover_status") == "ready":
                    cover_url = url

        if not cover_url:
            return None

        # Extract MinIO object name from URL like /api/v1/files/covers/xxx.png
        object_name = cover_url.replace("/api/v1/files/", "")
        if not object_name:
            return None

        try:
            from app.services.storage import get_file_bytes
            data, _ct = get_file_bytes(object_name)
            log.info("publish.cover_loaded", object_name=object_name, size=len(data))
            return data
        except Exception as e:
            log.warning("publish.cover_load_failed", error=str(e))
            return None

    def _send_with_photo(
        self, bot_token: str, chat_id: str, html_text: str, photo_data: bytes
    ) -> dict:
        """Send a photo with caption via Telegram.

        If the message is too long for a caption (>1024 chars), sends photo
        first, then a follow-up text message.

        Args:
            bot_token: Telegram bot token.
            chat_id: Target chat/channel ID.
            html_text: Formatted message.
            photo_data: Cover image bytes.

        Returns:
            Dict with message_id and raw_response.

        Raises:
            PublishRetryError: On transient failures.
            PublishError: On permanent failures.
        """
        client = TelegramClient(bot_token)

        if len(html_text) <= 1024:
            # Fits in photo caption — send as single message
            result = client.send_photo(chat_id, photo_data, html_text)
        else:
            # Too long for caption — send photo with short caption, then full text
            # Take first paragraph as caption
            short = html_text[:1021] + "..."
            result = client.send_photo(chat_id, photo_data, short)

            if result.success:
                # Send remaining text as follow-up (not critical if fails)
                try:
                    client.send_message(chat_id, html_text)
                except Exception:
                    log.warning("publish.followup_text_failed", chat_id=chat_id)

        if result.success:
            return {
                "message_id": result.message_id,
                "raw_response": result.raw_response,
            }

        if result.retryable:
            raise PublishRetryError(result.error)

        raise PublishError(result.error)

    def _send(
        self, bot_token: str, chat_id: str, html_text: str,
        disable_web_page_preview: bool = False,
    ) -> dict:
        """Send the message via Telegram.

        Args:
            bot_token: Telegram bot token.
            chat_id: Target chat/channel ID.
            html_text: Formatted message.
            disable_web_page_preview: Disable link previews (used for flash).

        Returns:
            Dict with message_id and raw_response.

        Raises:
            PublishRetryError: On transient failures.
            PublishError: On permanent failures.
        """
        client = TelegramClient(bot_token)
        result = client.send_message(
            chat_id, html_text,
            disable_web_page_preview=disable_web_page_preview,
        )

        if result.success:
            return {
                "message_id": result.message_id,
                "raw_response": result.raw_response,
            }

        if result.retryable:
            raise PublishRetryError(result.error)

        raise PublishError(result.error)

    def _mark_published(
        self,
        job: PublishJob,
        adaptation: ChannelAdaptation,
        result: dict,
        chat_id: str,
    ) -> None:
        """Mark job and adaptation as published.

        Args:
            job: The PublishJob to update.
            adaptation: The ChannelAdaptation to update.
            result: Send result with message_id and raw_response.
            chat_id: Chat ID where message was sent.
        """
        job.status = "published"
        job.published_at = datetime.now(timezone.utc)
        job.platform_post_id = result["message_id"]
        job.platform_response = result["raw_response"]
        job.error_message = None

        adaptation.status = "published"

        # Update editorial pipeline status so published posts
        # appear in the "Published" tab for ALL publish paths
        # (manual batch-publish AND autopilot)
        from sqlalchemy import select, update as sa_update
        from app.models.project_score import MaterialProjectScore

        self.session.execute(
            sa_update(MaterialProjectScore)
            .where(
                MaterialProjectScore.material_id == adaptation.material_id,
                MaterialProjectScore.editorial_status != "published",
            )
            .values(editorial_status="published")
        )

        self.session.commit()

        log.info(
            "publish.success",
            message_id=result["message_id"],
            chat_id=chat_id,
        )

    def _fail_job(self, job: PublishJob, error: str) -> None:
        """Mark a job as failed.

        Args:
            job: The PublishJob to mark.
            error: Error message to store.
        """
        job.status = "failed"
        job.error_message = error
        job.retry_count += 1
        self.session.commit()
