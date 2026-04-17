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
