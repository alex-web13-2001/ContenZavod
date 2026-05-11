"""Celery application factory with queue configuration.

Five dedicated queues for different task types:
- scrape_queue:    Heavy browser tasks (prefork, limited concurrency)
- ai_queue:        I/O-bound API calls (gevent-friendly, high concurrency)
- publish_queue:   Critical publishing tasks (high priority)
- media_queue:     Image/video generation (can wait)
- analytics_queue: Background stats collection (lowest priority)
"""

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "contenzavod",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task routing
    task_routes={
        "workers.scrape_tasks.*": {"queue": "scrape_queue"},
        "workers.ai_tasks.*": {"queue": "ai_queue"},
        "workers.publish_tasks.*": {"queue": "publish_queue"},
        "workers.media_tasks.*": {"queue": "media_queue"},
        "workers.analytics_tasks.*": {"queue": "analytics_queue"},
        "digest.*": {"queue": "ai_queue"},
        # Autopilot routes per-task (mixed queues)
        "workers.autopilot_tasks.autopilot_rank_and_queue": {"queue": "ai_queue"},
        "workers.autopilot_tasks.autopilot_publish_next": {"queue": "publish_queue"},
        "workers.autopilot_tasks.autopilot_retry_covers": {"queue": "media_queue"},
        "workers.autopilot_tasks.autopilot_expire_stale": {"queue": "ai_queue"},
        "workers.autopilot_tasks.autopilot_archive_stale_drafts": {"queue": "ai_queue"},
    },

    # Default queue
    task_default_queue="ai_queue",

    # Retry policy
    task_acks_late=True,  # Acknowledge after task completes (not before)
    worker_prefetch_multiplier=1,  # Don't prefetch too many tasks

    # Result expiration
    result_expires=3600,  # 1 hour

    # Task time limits
    task_soft_time_limit=300,  # 5 minutes soft limit
    task_time_limit=600,  # 10 minutes hard limit
)

# Beat schedule (periodic tasks)
celery_app.conf.beat_schedule = {
    # Scrape all active sources every 2 hours
    "scrape-all-sources": {
        "task": "workers.scrape_tasks.scrape_all_active_sources",
        "schedule": crontab(minute=0, hour="*/2"),
    },
    # Classify new materials every 30 minutes
    "classify-new-materials": {
        "task": "workers.ai_tasks.classify_new_materials",
        "schedule": crontab(minute="*/30"),
        "options": {"queue": "ai_queue"},
    },
    # Evaluate classified materials for projects every 15 minutes
    "evaluate-classified-materials": {
        "task": "workers.ai_tasks.evaluate_classified_materials",
        "schedule": crontab(minute="*/15"),
        "options": {"queue": "ai_queue"},
    },
    # Sync Telegram post stats (views, reactions, forwards) every 30 minutes
    "sync-telegram-stats": {
        "task": "workers.publish_tasks.sync_telegram_stats",
        "schedule": crontab(minute="*/30"),
        "options": {"queue": "publish_queue"},
    },
    # === AUTOPILOT TASKS ===
    # Rank and queue new adaptations every 15 minutes
    "autopilot-rank-and-queue": {
        "task": "workers.autopilot_tasks.autopilot_rank_and_queue",
        "schedule": crontab(minute="*/15"),
        "options": {"queue": "ai_queue"},
    },
    # Publish next item from queue every 5 minutes
    "autopilot-publish-next": {
        "task": "workers.autopilot_tasks.autopilot_publish_next",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": "publish_queue"},
    },
    # Retry failed cover generations every 10 minutes
    "autopilot-retry-covers": {
        "task": "workers.autopilot_tasks.autopilot_retry_covers",
        "schedule": crontab(minute="*/10"),
        "options": {"queue": "media_queue"},
    },
    # Expire stale queue items every hour
    "autopilot-expire-stale": {
        "task": "workers.autopilot_tasks.autopilot_expire_stale",
        "schedule": crontab(minute=0),
        "options": {"queue": "ai_queue"},
    },
    # Archive draft adaptations whose source material is stale (every hour, offset 30 min)
    "autopilot-archive-stale-drafts": {
        "task": "workers.autopilot_tasks.autopilot_archive_stale_drafts",
        "schedule": crontab(minute=30),
        "options": {"queue": "ai_queue"},
    },
}

# Explicitly register task modules
celery_app.conf.include = [
    "workers.scrape_tasks",
    "workers.ai_tasks",
    "workers.publish_tasks",
    "workers.digest_tasks",
    "workers.autopilot_tasks",
]
