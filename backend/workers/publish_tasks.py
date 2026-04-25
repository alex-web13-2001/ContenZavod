"""Publish tasks — Celery task wrappers for publishing.

Tasks are thin orchestrators: load session → call service → handle retries.
All business logic lives in app.services.publish_service.
"""

import structlog
from celery import shared_task

from app.database import get_sync_session
from app.services.publish_service import PublishError, PublishRetryError, PublishService

log = structlog.get_logger()


@shared_task(
    name="workers.publish_tasks.publish_to_telegram",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def publish_to_telegram(self, publish_job_id: str):
    """Publish an adaptation to Telegram.

    Delegates all logic to PublishService. Only handles
    Celery-specific concerns: session lifecycle and retries.

    Args:
        publish_job_id: UUID of the PublishJob to execute.
    """
    with get_sync_session() as session:
        service = PublishService(session)
        try:
            result = service.execute(publish_job_id)
            return {"status": "published", **result}

        except PublishRetryError as e:
            log.warning(
                "publish.retrying",
                job_id=publish_job_id,
                error=str(e),
                attempt=self.request.retries + 1,
            )
            raise self.retry(
                exc=e,
                countdown=60 * (self.request.retries + 1),
            )

        except PublishError as e:
            log.error(
                "publish.failed",
                job_id=publish_job_id,
                error=str(e),
            )
            return {"status": "failed", "error": str(e)}


@shared_task(
    name="workers.publish_tasks.sync_telegram_stats",
    bind=True,
    max_retries=1,
)
def sync_telegram_stats(self):
    """Sync Telegram post statistics for recent publications.

    Scrapes the public embed page for each published post from the
    last 7 days and updates views, reactions, and forwards in DB.
    """
    import time
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select

    from app.models.publish_job import PublishJob
    from app.models.channel import Channel
    from app.models.channel_adaptation import ChannelAdaptation
    from app.services.telegram_client import TelegramClient

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    with get_sync_session() as session:
        # Get all published jobs from the last 7 days that have a message_id
        jobs = session.execute(
            select(PublishJob)
            .where(
                PublishJob.status == "published",
                PublishJob.published_at >= cutoff,
                PublishJob.platform_post_id.isnot(None),
            )
            .order_by(PublishJob.published_at.desc())
        ).scalars().all()

        if not jobs:
            log.info("stats.sync.no_jobs")
            return {"status": "ok", "updated": 0}

        log.info("stats.sync.start", job_count=len(jobs))

        # Group by channel to reuse TelegramClient
        channel_cache: dict[str, tuple[str, str]] = {}  # channel_id → (bot_token, chat_id)
        updated = 0

        for job in jobs:
            try:
                ch_key = str(job.channel_id)

                if ch_key not in channel_cache:
                    channel = session.get(Channel, job.channel_id)
                    if not channel:
                        continue
                    config = channel.config or {}
                    bot_token = config.get("bot_token", "")

                    # Resolve chat_id for the adaptation's language
                    adaptation = session.get(ChannelAdaptation, job.content_id)
                    lang = adaptation.language if adaptation else None
                    chat_id = ""
                    endpoints = config.get("endpoints", {})
                    if lang and lang in endpoints:
                        chat_id = endpoints[lang].get("chat_id", "")
                    if not chat_id:
                        chat_id = config.get("chat_id", "")

                    if bot_token and chat_id:
                        channel_cache[ch_key] = (bot_token, chat_id)
                    else:
                        continue

                bot_token, chat_id = channel_cache[ch_key]
                client = TelegramClient(bot_token)
                stats = client.get_message_stats(chat_id, job.platform_post_id)

                if stats:
                    job.views = stats["views"]
                    job.reactions = stats["reactions"]
                    job.forwards = stats["forwards"]
                    job.comments = stats["comments"]
                    job.stats_updated_at = datetime.now(timezone.utc)
                    updated += 1

                # Rate limit: don't hammer t.me
                time.sleep(1.5)

            except Exception as e:
                log.warning(
                    "stats.sync.job_failed",
                    job_id=str(job.id),
                    error=str(e),
                )
                continue

        session.commit()
        log.info("stats.sync.done", updated=updated, total=len(jobs))
        return {"status": "ok", "updated": updated, "total": len(jobs)}
