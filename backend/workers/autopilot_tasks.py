"""Autopilot tasks — automated content ranking, scheduling, and publishing.

Four periodic tasks:
- autopilot_rank_and_queue:  Rank new adaptations, add to queue (every 15 min)
- autopilot_publish_next:    Publish the next item if slot is available (every 5 min)
- autopilot_retry_covers:    Retry failed cover generations (every 10 min)
- autopilot_expire_stale:    Remove expired items from queue (every hour)
"""

import uuid
from datetime import datetime, timedelta, timezone

import structlog
from celery import shared_task
from sqlalchemy import and_, case, func, or_, select

from app.database import get_sync_session

from ai.deduplicator import compute_uniqueness_score

log = structlog.get_logger()

# Time slots for Cyprus (UTC+3 = EEST), stored as UTC hours
SCHEDULE_SLOTS = {
    "morning":  (5, 6),   # 08:00–09:00 Cyprus = 05:00–06:00 UTC
    "lunch":    (9, 10),  # 12:30–13:30 Cyprus ≈ 09:00–10:00 UTC
    "evening":  (15, 16), # 18:00–19:00 Cyprus = 15:00–16:00 UTC
    "night":    (18, 19), # 21:00–22:00 Cyprus = 18:00–19:00 UTC
}

# Category freshness TTL (hours) — after this, material is too stale
DEFAULT_TTL = {
    "politics": 12,
    "economy": 24,
    "society": 18,
    "sport": 8,
    "culture": 36,
    "tech": 48,
    "lifestyle": 48,
    "crime": 12,
    "health": 24,
    "environment": 36,
    "world": 18,
    "opinion": 48,
    "default": 24,
}


def _get_autopilot_config(channel) -> dict:
    """Get autopilot config with defaults merged in."""
    defaults = {
        "enabled": False,
        "strategies": ["smart_queue", "express"],
        "max_posts_per_day": 10,
        "min_interval_minutes": 45,
        "min_score_threshold": 7.0,
        "cover_policy": "short_post_optional",
        "schedule_slots": ["morning", "lunch", "evening", "night"],
        "category_limits": {},
        "ttl_hours": {},
        "shadow_mode": True,
    }
    cfg = channel.autopilot_config or {}
    return {**defaults, **cfg}


def _compute_freshness(scraped_at: datetime, category: str, ttl_overrides: dict) -> float:
    """Compute freshness score (0–10) based on age and category TTL."""
    now = datetime.now(timezone.utc)

    # Defensive: ensure tz-aware comparison
    if scraped_at.tzinfo is None:
        scraped_at = scraped_at.replace(tzinfo=timezone.utc)

    hours_old = (now - scraped_at).total_seconds() / 3600

    ttl = ttl_overrides.get(category, DEFAULT_TTL.get(category, DEFAULT_TTL["default"]))

    if hours_old >= ttl:
        return 0.0

    # Linear decay
    return round(max(0, 10.0 * (1.0 - hours_old / ttl)), 2)


def _compute_final_score(
    relevance: int,
    hype: int,
    freshness: float,
    uniqueness: float = 10.0,
    engagement: float = 5.0,
) -> float:
    """Compute multi-signal final score.

    5-signal ranking (Phase 2):
      relevance:    0.30  — topic fit for the project
      hype:         0.25  — viral potential
      freshness:    0.20  — how recent the material is
      uniqueness:   0.15  — semantic deduplication (Jaccard)
      engagement:   0.10  — predicted engagement (placeholder until Phase 4)
    """
    return round(
        0.30 * relevance
        + 0.25 * hype
        + 0.20 * freshness
        + 0.15 * uniqueness
        + 0.10 * engagement,
        2,
    )


# Default category limits per day per channel
DEFAULT_CATEGORY_LIMITS = {
    "politics": 3,
    "economy": 2,
    "society": 3,
    "sport": 2,
    "lifestyle": 2,
    "crime": 2,
    "culture": 2,
    "tech": 2,
    "health": 2,
    "environment": 2,
    "world": 2,
    "opinion": 1,
    "default": 3,
}


def _find_next_slot(config: dict, already_scheduled: int = 0) -> datetime:
    """Find the next available publication slot based on config schedule.

    Uses already_scheduled to spread posts across time slots with min_interval.
    """
    now = datetime.now(timezone.utc)
    allowed = config.get("schedule_slots", ["morning", "lunch", "evening", "night"])
    min_interval = config.get("min_interval_minutes", 45)

    candidates = []
    for day_offset in range(2):  # today + tomorrow
        for slot_name in allowed:
            if slot_name not in SCHEDULE_SLOTS:
                continue
            start_h, end_h = SCHEDULE_SLOTS[slot_name]
            # Candidate = midpoint of the slot window
            candidate = now.replace(
                hour=start_h, minute=30, second=0, microsecond=0
            ) + timedelta(days=day_offset)
            if candidate > now:
                candidates.append(candidate)

    if not candidates:
        base = now + timedelta(minutes=15)
    else:
        base = min(candidates)

    # Spread: offset by min_interval × already_scheduled count
    return base + timedelta(minutes=min_interval * already_scheduled)


@shared_task(
    bind=True,
    name="workers.autopilot_tasks.autopilot_rank_and_queue",
    max_retries=1,
    queue="ai_queue",
)
def autopilot_rank_and_queue(self):
    """Rank new recommended adaptations and add them to the autopilot queue.

    Runs every 15 minutes. For each active channel with autopilot enabled:
    1. Find adaptations in 'draft' status that aren't already queued
    2. Compute multi-signal score (relevance + hype + freshness)
    3. Filter by threshold
    4. Add to autopilot_queue with scheduled_at
    """
    from app.models.channel import Channel
    from app.models.channel_adaptation import ChannelAdaptation
    from app.models.autopilot_queue import AutopilotQueueItem
    from app.models.project_score import MaterialProjectScore
    from app.models.material import RawMaterial

    with get_sync_session() as session:
        # Find channels with autopilot enabled
        channels = session.execute(
            select(Channel).where(Channel.is_active == True)
        ).scalars().all()

        total_queued = 0

        for channel in channels:
            config = _get_autopilot_config(channel)
            if not config["enabled"]:
                continue

            threshold = config["min_score_threshold"]
            max_per_day = config["max_posts_per_day"]
            ttl_overrides = config.get("ttl_hours", {})
            shadow = config.get("shadow_mode", True)
            strategies = config.get("strategies", ["smart_queue"])

            # Count how many already queued/published today
            today_start = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            today_count = session.execute(
                select(func.count(AutopilotQueueItem.id)).where(
                    AutopilotQueueItem.channel_id == channel.id,
                    AutopilotQueueItem.created_at >= today_start,
                    AutopilotQueueItem.status.in_(
                        ["queued", "shadow", "approved", "publishing", "published"]
                    ),
                )
            ).scalar() or 0

            if today_count >= max_per_day:
                continue

            remaining = max_per_day - today_count

            # Find draft adaptations for this channel not yet in queue
            already_queued_ids = session.execute(
                select(AutopilotQueueItem.adaptation_id).where(
                    AutopilotQueueItem.channel_id == channel.id,
                    AutopilotQueueItem.status.in_(
                        ["queued", "shadow", "approved", "publishing"]
                    ),
                )
            ).scalars().all()
            already_queued_set = set(already_queued_ids)

            # Get draft adaptations with their scores
            adaptations = session.execute(
                select(ChannelAdaptation).where(
                    ChannelAdaptation.channel_id == channel.id,
                    ChannelAdaptation.status == "draft",
                )
            ).scalars().all()

            # Pre-compute category counts for today (anti-spam) — one query
            cat_limits = config.get("category_limits", DEFAULT_CATEGORY_LIMITS)
            category_counts_today: dict[str, int] = {}
            cat_rows = session.execute(
                select(
                    RawMaterial.metadata_["ai_classification"]["category"].astext.label("cat"),
                    func.count(AutopilotQueueItem.id).label("cnt"),
                )
                .join(
                    ChannelAdaptation,
                    AutopilotQueueItem.adaptation_id == ChannelAdaptation.id,
                )
                .join(
                    RawMaterial,
                    ChannelAdaptation.material_id == RawMaterial.id,
                )
                .where(
                    AutopilotQueueItem.channel_id == channel.id,
                    AutopilotQueueItem.created_at >= today_start,
                    AutopilotQueueItem.status.in_(
                        ["queued", "shadow", "approved", "publishing", "published"]
                    ),
                )
                .group_by("cat")
            ).all()
            for cat_name, cnt in cat_rows:
                if cat_name:
                    category_counts_today[cat_name] = cnt

            scored_items = []
            for adapt in adaptations:
                if adapt.id in already_queued_set:
                    continue

                # Get project score for this material
                score = session.execute(
                    select(MaterialProjectScore).where(
                        MaterialProjectScore.material_id == adapt.material_id,
                        MaterialProjectScore.project_id == channel.project_id,
                    )
                ).scalar_one_or_none()

                if not score or not score.is_recommended:
                    continue

                # Get material for freshness calc
                material = session.get(RawMaterial, adapt.material_id)
                if not material:
                    continue

                category = (material.metadata_ or {}).get(
                    "ai_classification", {}
                ).get("category", "default")

                freshness = _compute_freshness(
                    material.scraped_at,
                    category,
                    ttl_overrides,
                )

                # Skip expired materials
                if freshness <= 0:
                    continue

                # Phase 2: Compute real uniqueness score via semantic fingerprint
                fingerprint = (material.metadata_ or {}).get("semantic_fingerprint", [])
                uniqueness = compute_uniqueness_score(
                    material.id, fingerprint, session, adapt.tenant_id
                )

                # Skip near-duplicates (uniqueness < 2.0 = similarity > 0.8)
                if uniqueness < 2.0:
                    log.info(
                        "autopilot.skip_duplicate",
                        material_id=str(material.id),
                        uniqueness=uniqueness,
                        title=material.title[:60],
                    )
                    continue

                final = _compute_final_score(
                    score.relevance_score, score.hype_score,
                    freshness, uniqueness,
                )

                # Express check
                is_express = (
                    "express" in strategies
                    and (
                        score.hype_score >= 9
                        or (material.metadata_ or {}).get(
                            "ai_classification", {}
                        ).get("is_breaking", False)
                    )
                )

                if not is_express and final < threshold:
                    continue

                # Anti-spam: category balance check (pre-computed)
                cat_max = cat_limits.get(category, cat_limits.get("default", 3))
                cat_today = category_counts_today.get(category, 0)

                if cat_today >= cat_max:
                    log.debug(
                        "autopilot.skip_category_limit",
                        category=category,
                        count=cat_today,
                        limit=cat_max,
                    )
                    continue

                scored_items.append({
                    "adaptation": adapt,
                    "score": score,
                    "final": final,
                    "freshness": freshness,
                    "uniqueness": uniqueness,
                    "strategy": "express" if is_express else "smart_queue",
                    "category": category,
                })

            # Sort by final score descending
            scored_items.sort(key=lambda x: x["final"], reverse=True)

            # Take only remaining slots
            for item in scored_items[:remaining]:
                adapt = item["adaptation"]

                # Determine status based on shadow mode
                initial_status = "shadow" if shadow else "queued"

                # Express items skip shadow mode
                if item["strategy"] == "express":
                    initial_status = "queued"

                scheduled = (
                    datetime.now(timezone.utc) + timedelta(minutes=2)
                    if item["strategy"] == "express"
                    else _find_next_slot(config, already_scheduled=total_queued)
                )

                queue_item = AutopilotQueueItem(
                    tenant_id=adapt.tenant_id,
                    channel_id=channel.id,
                    adaptation_id=adapt.id,
                    project_id=channel.project_id,
                    final_score=item["final"],
                    freshness_score=item["freshness"],
                    uniqueness_score=item["uniqueness"],
                    engagement_predict=5.0,  # Phase 4: feedback loop
                    strategy=item["strategy"],
                    scheduled_at=scheduled,
                    status=initial_status,
                )
                session.add(queue_item)
                total_queued += 1

                # Always dispatch cover generation for queued items
                # cover_policy only controls whether PUBLISHING requires a cover
                # We always generate covers so users can preview them
                needs_cover = True
                if config.get("cover_policy") == "never":
                    needs_cover = False

                if needs_cover and not adapt.cover_status:
                    adapt.cover_status = "generating"
                    adapt.cover_retry_count = 0
                    session.flush()

                    from workers.ai_tasks import generate_adaptation_cover
                    generate_adaptation_cover.delay(
                        str(adapt.id), str(adapt.tenant_id)
                    )
                    log.info(
                        "autopilot.cover_dispatched",
                        adaptation_id=str(adapt.id),
                    )

                log.info(
                    "autopilot.queued",
                    adaptation_id=str(adapt.id),
                    channel=channel.name,
                    language=adapt.language,
                    strategy=item["strategy"],
                    final_score=item["final"],
                    status=initial_status,
                )

        session.commit()
        log.info("autopilot.rank_done", total_queued=total_queued)
        return {"status": "ok", "queued": total_queued}


@shared_task(
    bind=True,
    name="workers.autopilot_tasks.autopilot_publish_next",
    max_retries=1,
    queue="publish_queue",
)
def autopilot_publish_next(self):
    """Publish the next item from the autopilot queue if a slot is available.

    Runs every 5 minutes. Checks:
    1. scheduled_at <= now
    2. Anti-spam: min interval since last publish
    3. Daily limit not exceeded
    4. Cover readiness (longread requires cover)
    5. Dispatches publish_to_telegram task
    """
    from app.models.autopilot_queue import AutopilotQueueItem
    from app.models.channel import Channel
    from app.models.channel_adaptation import ChannelAdaptation
    from app.models.publish_job import PublishJob

    now = datetime.now(timezone.utc)
    published_count = 0

    with get_sync_session() as session:
        # Get items ready to publish (queued or approved, scheduled_at <= now)
        # Express first (strategy priority), then by final_score
        strategy_priority = case(
            (AutopilotQueueItem.strategy == "express", 0),
            else_=1,
        )
        items = session.execute(
            select(AutopilotQueueItem)
            .where(
                AutopilotQueueItem.status.in_(["queued", "approved"]),
                AutopilotQueueItem.scheduled_at <= now,
            )
            .order_by(
                strategy_priority.asc(),
                AutopilotQueueItem.final_score.desc(),
            )
            .limit(5)
        ).scalars().all()

        if not items:
            return {"status": "ok", "published": 0}

        for item in items:
            channel = session.get(Channel, item.channel_id)
            if not channel:
                item.status = "skipped"
                item.skip_reason = "channel_not_found"
                continue

            config = _get_autopilot_config(channel)

            # Anti-spam: check min interval
            min_interval = config.get("min_interval_minutes", 45)
            last_published = session.execute(
                select(AutopilotQueueItem.published_at)
                .where(
                    AutopilotQueueItem.channel_id == channel.id,
                    AutopilotQueueItem.status == "published",
                )
                .order_by(AutopilotQueueItem.published_at.desc())
                .limit(1)
            ).scalar()

            if last_published and (now - last_published).total_seconds() < min_interval * 60:
                # Too soon — reschedule
                item.scheduled_at = last_published + timedelta(minutes=min_interval)
                log.debug(
                    "autopilot.rescheduled",
                    adaptation_id=str(item.adaptation_id),
                    next_at=item.scheduled_at.isoformat(),
                )
                continue

            # Daily limit check
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_published = session.execute(
                select(func.count(AutopilotQueueItem.id)).where(
                    AutopilotQueueItem.channel_id == channel.id,
                    AutopilotQueueItem.status == "published",
                    AutopilotQueueItem.published_at >= today_start,
                )
            ).scalar() or 0

            if today_published >= config.get("max_posts_per_day", 10):
                item.status = "skipped"
                item.skip_reason = f"daily_limit ({today_published}/{config['max_posts_per_day']})"
                continue

            # Cover readiness check
            adaptation = session.get(ChannelAdaptation, item.adaptation_id)
            if not adaptation:
                item.status = "skipped"
                item.skip_reason = "adaptation_not_found"
                continue

            cover_policy = config.get("cover_policy", "short_post_optional")
            needs_cover = True
            if cover_policy == "short_post_optional" and adaptation.content_format == "short_post":
                needs_cover = False
            if item.strategy == "express":
                needs_cover = False

            if needs_cover and adaptation.cover_status != "ready":
                # Cover not ready — keep in queue, don't skip
                log.debug(
                    "autopilot.waiting_cover",
                    adaptation_id=str(adaptation.id),
                    cover_status=adaptation.cover_status,
                )
                continue

            # Create PublishJob and dispatch
            idempotency_key = f"autopilot-{item.adaptation_id}-{channel.id}"

            # Check for existing job with same key
            existing_job = session.execute(
                select(PublishJob).where(PublishJob.idempotency_key == idempotency_key)
            ).scalar_one_or_none()

            if existing_job:
                item.status = "skipped"
                item.skip_reason = "already_published"
                item.publish_job_id = existing_job.id
                continue

            job = PublishJob(
                tenant_id=item.tenant_id,
                content_id=adaptation.id,
                channel_id=channel.id,
                status="scheduled",
                idempotency_key=idempotency_key,
            )
            session.add(job)
            session.flush()  # Get job.id

            item.status = "publishing"
            item.publish_job_id = job.id

            published_count += 1
            log.info(
                "autopilot.dispatching",
                adaptation_id=str(item.adaptation_id),
                channel=channel.name,
                strategy=item.strategy,
                score=float(item.final_score),
                job_id=str(job.id),
            )

        # Single commit for all changes in this cycle
        session.commit()

        # Dispatch publish tasks AFTER commit (so PublishJobs exist in DB)
        for item in items:
            if item.status == "publishing" and item.publish_job_id:
                from workers.publish_tasks import publish_to_telegram
                publish_to_telegram.delay(str(item.publish_job_id))

    log.info("autopilot.publish_done", published=published_count)
    return {"status": "ok", "published": published_count}


@shared_task(
    bind=True,
    name="workers.autopilot_tasks.autopilot_retry_covers",
    max_retries=1,
    queue="media_queue",
)
def autopilot_retry_covers(self):
    """Retry failed cover image generations AND generate missing covers.

    Runs every 10 minutes. Handles:
    1. Adaptations with cover_status = 'error' and retry_count < 3
    2. Adaptations in autopilot queue with NO cover (NULL cover_status)
    Re-dispatches the cover generation task.
    """
    from app.models.channel_adaptation import ChannelAdaptation
    from app.models.autopilot_queue import AutopilotQueueItem

    max_retries = 10
    # Only retry covers that failed recently (within 48h)
    age_cutoff = datetime.now(timezone.utc) - timedelta(hours=48)

    with get_sync_session() as session:
        retried = 0

        # 1. Retry failed covers
        failed = session.execute(
            select(ChannelAdaptation).where(
                ChannelAdaptation.cover_status == "error",
                ChannelAdaptation.cover_retry_count < max_retries,
                ChannelAdaptation.updated_at >= age_cutoff,
            )
        ).scalars().all()

        for adapt in failed:
            adapt.cover_status = "generating"
            adapt.cover_retry_count += 1
            session.flush()

            # Dispatch cover generation
            from workers.ai_tasks import generate_adaptation_cover
            generate_adaptation_cover.delay(
                str(adapt.id), str(adapt.tenant_id)
            )

            retried += 1
            log.info(
                "autopilot.cover_retry",
                adaptation_id=str(adapt.id),
                retry_count=adapt.cover_retry_count,
            )

        # 2. Generate covers for queued items with no cover at all
        missing_cover = session.execute(
            select(ChannelAdaptation)
            .join(
                AutopilotQueueItem,
                AutopilotQueueItem.adaptation_id == ChannelAdaptation.id,
            )
            .where(
                AutopilotQueueItem.status.in_(["queued", "shadow", "approved", "publishing"]),
                ChannelAdaptation.cover_status.is_(None),
            )
        ).scalars().all()

        generated = 0
        for adapt in missing_cover:
            adapt.cover_status = "generating"
            adapt.cover_retry_count = 0
            session.flush()

            from workers.ai_tasks import generate_adaptation_cover
            generate_adaptation_cover.delay(
                str(adapt.id), str(adapt.tenant_id)
            )

            generated += 1
            log.info(
                "autopilot.cover_generate_missing",
                adaptation_id=str(adapt.id),
            )

        # 3. Reset stuck covers for items still in active queue
        #    Catches: permanently_failed OR error with exhausted retries
        #    This handles API outages — when the API comes back, covers retry
        active_statuses = ["queued", "shadow", "approved", "publishing"]
        stuck_covers = session.execute(
            select(ChannelAdaptation)
            .join(
                AutopilotQueueItem,
                AutopilotQueueItem.adaptation_id == ChannelAdaptation.id,
            )
            .where(
                AutopilotQueueItem.status.in_(active_statuses),
                or_(
                    ChannelAdaptation.cover_status == "permanently_failed",
                    and_(
                        ChannelAdaptation.cover_status == "error",
                        ChannelAdaptation.cover_retry_count >= max_retries,
                    ),
                ),
            )
        ).scalars().all()

        reset_count = 0
        for adapt in stuck_covers:
            adapt.cover_status = "generating"
            adapt.cover_retry_count = 0
            session.flush()

            from workers.ai_tasks import generate_adaptation_cover
            generate_adaptation_cover.delay(
                str(adapt.id), str(adapt.tenant_id)
            )

            reset_count += 1
            log.info(
                "autopilot.cover_reset_stuck",
                adaptation_id=str(adapt.id),
            )

        # Mark permanently failed ONLY items NOT in active queue
        permanently_failed = session.execute(
            select(ChannelAdaptation).where(
                ChannelAdaptation.cover_status == "error",
                ChannelAdaptation.cover_retry_count >= max_retries,
                ~ChannelAdaptation.id.in_(
                    select(AutopilotQueueItem.adaptation_id).where(
                        AutopilotQueueItem.status.in_(active_statuses)
                    )
                ),
            )
        ).scalars().all()

        for adapt in permanently_failed:
            adapt.cover_status = "permanently_failed"

        session.commit()
        log.info(
            "autopilot.cover_retry_done",
            retried=retried,
            generated=generated,
            reset_permanently_failed=reset_count,
            permanently_failed=len(permanently_failed),
        )
        return {
            "status": "ok",
            "retried": retried,
            "generated": generated,
            "reset_permanently_failed": reset_count,
            "permanently_failed": len(permanently_failed),
        }


@shared_task(
    bind=True,
    name="workers.autopilot_tasks.autopilot_expire_stale",
    max_retries=1,
    queue="ai_queue",
)
def autopilot_expire_stale(self):
    """Expire stale items from the autopilot queue.

    Items that have been queued/shadow for too long are marked as expired.
    """
    from app.models.autopilot_queue import AutopilotQueueItem

    # Items older than 48 hours that haven't been published
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)

    with get_sync_session() as session:
        stale = session.execute(
            select(AutopilotQueueItem).where(
                AutopilotQueueItem.status.in_(["queued", "shadow"]),
                AutopilotQueueItem.created_at < cutoff,
            )
        ).scalars().all()

        for item in stale:
            item.status = "expired"
            item.skip_reason = "ttl_exceeded_48h"

        session.commit()
        log.info("autopilot.expire_done", expired=len(stale))
        return {"status": "ok", "expired": len(stale)}
