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
}

# Explicitly register task modules
celery_app.conf.include = [
    "workers.scrape_tasks",
    "workers.ai_tasks",
]
