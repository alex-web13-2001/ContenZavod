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
# These are generous defaults; override per-channel via autopilot_config.ttl_hours
DEFAULT_TTL = {
    "politics": 48,
    "economy": 72,
    "society": 72,
    "sport": 24,
    "culture": 168,
    "tech": 168,
    "lifestyle": 168,
    "crime": 48,
    "health": 72,
    "environment": 168,
    "world": 48,
    "opinion": 168,
    "default": 72,
}


# Default format ratio distribution for multi-format feeds
DEFAULT_FORMAT_RATIOS = {
    "flash": 0.40,
    "short_post": 0.40,
    "longread": 0.20,
}

# Telegram-compatible formats (the formats autopilot uses for TG channels)
TELEGRAM_FORMATS = ["flash", "short_post", "longread"]


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
        "language_settings": {},
        "format_ratios": DEFAULT_FORMAT_RATIOS,
        "longread_max_per_day": 2,
        # Hard cutoff: materials older than this never enter the queue.
        # Protects against publishing stale news when fresh content is scarce.
        "max_material_age_hours": 24,
    }
    cfg = channel.autopilot_config or {}
    return {**defaults, **cfg}


def _get_language_config(config: dict, language: str) -> dict:
    """Get per-language settings, falling back to channel-level defaults.

    Supports per-language overrides for:
    - max_posts_per_day
    - min_interval_minutes
    - min_score_threshold

    Example config:
        {
            "max_posts_per_day": 10,           # channel default
            "min_interval_minutes": 45,        # channel default
            "language_settings": {
                "ru": {"max_posts_per_day": 12, "min_interval_minutes": 30},
                "en": {"max_posts_per_day": 8},
                "el": {}                        # uses channel defaults
            }
        }
    """
    lang_overrides = config.get("language_settings", {}).get(language, {})
    return {
        "max_posts_per_day": lang_overrides.get(
            "max_posts_per_day", config.get("max_posts_per_day", 10)
        ),
        "min_interval_minutes": lang_overrides.get(
            "min_interval_minutes", config.get("min_interval_minutes", 45)
        ),
        "min_score_threshold": lang_overrides.get(
            "min_score_threshold", config.get("min_score_threshold", 7.0)
        ),
    }



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

            # Auto-promote shadow → queued when shadow_mode is disabled
            if not shadow:
                shadow_items = session.execute(
                    select(AutopilotQueueItem).where(
                        AutopilotQueueItem.channel_id == channel.id,
                        AutopilotQueueItem.status == "shadow",
                    )
                ).scalars().all()

                for si in shadow_items:
                    si.status = "queued"
                    si.updated_at = datetime.now(timezone.utc)
                    log.info(
                        "autopilot.shadow_promoted",
                        adaptation_id=str(si.adaptation_id),
                        channel=channel.name,
                    )

                if shadow_items:
                    session.flush()

            # Count how many already queued/published today PER LANGUAGE
            today_start = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )

            # Get per-language counts for today
            lang_counts_rows = session.execute(
                select(
                    ChannelAdaptation.language,
                    func.count(AutopilotQueueItem.id),
                )
                .join(
                    ChannelAdaptation,
                    AutopilotQueueItem.adaptation_id == ChannelAdaptation.id,
                )
                .where(
                    AutopilotQueueItem.channel_id == channel.id,
                    AutopilotQueueItem.created_at >= today_start,
                    AutopilotQueueItem.status.in_(
                        ["queued", "shadow", "approved", "publishing", "published"]
                    ),
                )
                .group_by(ChannelAdaptation.language)
            ).all()
            today_counts_by_lang: dict[str, int] = {}
            for lang, cnt in lang_counts_rows:
                today_counts_by_lang[lang] = cnt

            # Compute remaining slots per language
            remaining_by_lang: dict[str, int] = {}
            all_full = True
            for lang in (channel.languages or ["ru"]):
                lang_cfg = _get_language_config(config, lang)
                lang_max = lang_cfg["max_posts_per_day"]
                lang_today = today_counts_by_lang.get(lang, 0)
                rem = lang_max - lang_today
                remaining_by_lang[lang] = max(0, rem)
                if rem > 0:
                    all_full = False

            if all_full:
                log.debug(
                    "autopilot.all_languages_full",
                    channel=channel.name,
                    counts=today_counts_by_lang,
                )
                continue

            # Track how many we queue per language in this cycle
            queued_by_lang: dict[str, int] = {}



            # Determine allowed formats for this channel type
            if channel.channel_type == "telegram":
                allowed_formats = [f for f in TELEGRAM_FORMATS
                                   if f in (channel.content_formats or ["short_post"])]
                if not allowed_formats:
                    allowed_formats = ["short_post"]
            else:
                _platform_primary = {
                    "website": "longread",
                    "youtube": "video_script",
                }
                allowed_formats = [_platform_primary.get(channel.channel_type, "short_post")]

            # Format balance: count today's items by format
            format_ratios = config.get("format_ratios", DEFAULT_FORMAT_RATIOS)
            longread_max = config.get("longread_max_per_day", 2)

            format_counts_today: dict[str, int] = {}
            fmt_rows = session.execute(
                select(
                    ChannelAdaptation.content_format,
                    func.count(AutopilotQueueItem.id),
                )
                .join(
                    ChannelAdaptation,
                    AutopilotQueueItem.adaptation_id == ChannelAdaptation.id,
                )
                .where(
                    AutopilotQueueItem.channel_id == channel.id,
                    AutopilotQueueItem.created_at >= today_start,
                    AutopilotQueueItem.status.in_(
                        ["queued", "shadow", "approved", "publishing", "published"]
                    ),
                )
                .group_by(ChannelAdaptation.content_format)
            ).all()
            for fmt_name, cnt in fmt_rows:
                if fmt_name:
                    format_counts_today[fmt_name] = cnt

            total_today = sum(format_counts_today.values())

            # Find materials already in queue or published for this channel
            # This prevents the same article from being published twice
            # (e.g. via short_post AND longread adaptations)
            already_queued_material_ids = session.execute(
                select(ChannelAdaptation.material_id).distinct()
                .join(
                    AutopilotQueueItem,
                    AutopilotQueueItem.adaptation_id == ChannelAdaptation.id,
                )
                .where(
                    AutopilotQueueItem.channel_id == channel.id,
                    AutopilotQueueItem.status.in_(
                        ["queued", "shadow", "approved", "publishing", "published"]
                    ),
                )
            ).scalars().all()
            already_published_materials = set(already_queued_material_ids)

            # Hard freshness cutoff: never enqueue materials older than this.
            # Configurable per-channel via autopilot_config.max_material_age_hours.
            # Default 24h, see ADR-007.
            max_age_hours = int(config.get("max_material_age_hours", 24))
            age_cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

            # Get draft adaptations for ALL allowed formats for this channel
            # WHERE the underlying material is still within the freshness window.
            adaptations = session.execute(
                select(ChannelAdaptation)
                .join(RawMaterial, ChannelAdaptation.material_id == RawMaterial.id)
                .where(
                    ChannelAdaptation.channel_id == channel.id,
                    ChannelAdaptation.status == "draft",
                    ChannelAdaptation.content_format.in_(allowed_formats),
                    RawMaterial.scraped_at >= age_cutoff,
                )
            ).scalars().all()

            # --- Lazy adapt: trigger adaptation for top scored materials ---
            # Only adapt materials that will actually be needed (remaining slots + buffer)
            total_remaining = sum(remaining_by_lang.values())

            # Skip lazy-adapt if we already have enough draft candidates
            if len(adaptations) >= total_remaining * 2:
                log.debug(
                    "autopilot.lazy_adapt_skip_enough_drafts",
                    drafts=len(adaptations),
                    remaining=total_remaining,
                )
            else:
                adapt_budget = total_remaining + 3  # tight budget

                # Materials that already have ANY adaptation for this channel
                # (any status — draft, published, approved, etc.)
                all_adapted_ids = session.execute(
                    select(ChannelAdaptation.material_id).distinct().where(
                        ChannelAdaptation.channel_id == channel.id,
                    )
                ).scalars().all()
                skip_material_ids = set(all_adapted_ids)
                skip_material_ids.update(already_published_materials)

                # Find top-scored recommended materials WITHOUT any adaptations,
                # restricted to the freshness window (ADR-007).
                from app.models.project_score import MaterialProjectScore as MPS_lazy

                lazy_query = (
                    select(MPS_lazy.material_id, MPS_lazy.project_id, RawMaterial.tenant_id)
                    .join(RawMaterial, MPS_lazy.material_id == RawMaterial.id)
                    .where(
                        MPS_lazy.project_id == channel.project_id,
                        MPS_lazy.is_recommended == True,
                        RawMaterial.scraped_at >= age_cutoff,
                    )
                    .order_by((MPS_lazy.relevance_score + MPS_lazy.hype_score).desc())
                    .limit(adapt_budget)
                )
                if skip_material_ids:
                    lazy_query = lazy_query.where(
                        ~MPS_lazy.material_id.in_(skip_material_ids)
                    )
                unadapted = session.execute(lazy_query).all()

                if unadapted:
                    from workers.ai_tasks import adapt_material_for_channels
                    for mat_id, proj_id, t_id in unadapted:
                        adapt_material_for_channels.delay(
                            str(mat_id), str(proj_id), str(t_id)
                        )
                    log.info(
                        "autopilot.lazy_adapt_triggered",
                        channel=channel.name,
                        count=len(unadapted),
                        budget=adapt_budget,
                    )

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
                # Skip if this material is already queued or published
                if adapt.material_id in already_published_materials:
                    continue

                # Per-language: skip if this language's slots are already full
                adapt_lang = adapt.language or "ru"
                lang_remaining = remaining_by_lang.get(adapt_lang, 0)
                lang_already_queued = queued_by_lang.get(adapt_lang, 0)
                if lang_remaining - lang_already_queued <= 0:
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
                # No artificial floor: materials past their category TTL get
                # freshness = 0 and naturally fall below the score threshold.
                # The hard max_material_age_hours filter above is what protects
                # the queue from emptying — see ADR-007.

                # Phase 2: Compute real uniqueness score via semantic fingerprint
                fingerprint = (material.metadata_ or {}).get("semantic_fingerprint", [])
                uniqueness = compute_uniqueness_score(
                    material.id, fingerprint, session, adapt.tenant_id
                )

                # Skip near-duplicates: uniqueness < 4.0 ≈ similarity > 0.6.
                # Looser than the original 2.0 threshold so two retellings of
                # the same story (different sources, ≥60% overlap) get caught.
                # See ADR-007.
                if uniqueness < 4.0:
                    log.info(
                        "autopilot.skip_duplicate",
                        material_id=str(material.id),
                        uniqueness=uniqueness,
                        title=material.title[:60],
                    )
                    continue

                # Per-language threshold from language_settings
                lang_cfg = _get_language_config(config, adapt_lang)
                lang_threshold = lang_cfg.get("min_score_threshold", threshold)

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

                if not is_express and final < lang_threshold:
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
                    "language": adapt_lang,
                    "content_format": adapt.content_format,
                })

            # Sort by final score descending
            scored_items.sort(key=lambda x: x["final"], reverse=True)

            # Take items respecting per-language limits AND format balance
            queued_formats: dict[str, int] = dict(format_counts_today)  # copy
            for item in scored_items:
                lang = item["language"]
                lang_rem = remaining_by_lang.get(lang, 0)
                lang_q = queued_by_lang.get(lang, 0)
                if lang_q >= lang_rem:
                    continue  # This language is full

                fmt = item["content_format"]
                adapt = item["adaptation"]

                # Format balance check: skip if this format is over its ratio
                if total_today > 0 and fmt in format_ratios:
                    current_ratio = queued_formats.get(fmt, 0) / max(total_today, 1)
                    target_ratio = format_ratios.get(fmt, 0.5)
                    # Allow 1.5x overshoot before blocking
                    if current_ratio > target_ratio * 1.5 and item["strategy"] != "express":
                        log.debug(
                            "autopilot.skip_format_balance",
                            format=fmt,
                            current=current_ratio,
                            target=target_ratio,
                        )
                        continue

                # Longread daily limit check
                if fmt == "longread":
                    lr_today = queued_formats.get("longread", 0)
                    if lr_today >= longread_max and item["strategy"] != "express":
                        log.debug(
                            "autopilot.skip_longread_limit",
                            count=lr_today,
                            limit=longread_max,
                        )
                        continue

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
                total_today += 1
                queued_by_lang[lang] = queued_by_lang.get(lang, 0) + 1
                queued_formats[fmt] = queued_formats.get(fmt, 0) + 1

                # Cover generation: flash NEVER gets covers, others follow policy
                needs_cover = True
                if fmt == "flash":
                    needs_cover = False
                elif config.get("cover_policy") == "never":
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
                    format=fmt,
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

            # Load the adaptation to get its language for per-language checks
            adaptation = session.get(ChannelAdaptation, item.adaptation_id)
            if not adaptation:
                item.status = "skipped"
                item.skip_reason = "adaptation_not_found"
                continue

            adapt_lang = adaptation.language or "ru"
            lang_cfg = _get_language_config(config, adapt_lang)

            # Anti-spam: check min interval PER LANGUAGE
            min_interval = lang_cfg["min_interval_minutes"]
            last_published = session.execute(
                select(AutopilotQueueItem.published_at)
                .join(
                    ChannelAdaptation,
                    AutopilotQueueItem.adaptation_id == ChannelAdaptation.id,
                )
                .where(
                    AutopilotQueueItem.channel_id == channel.id,
                    AutopilotQueueItem.status == "published",
                    ChannelAdaptation.language == adapt_lang,
                )
                .order_by(AutopilotQueueItem.published_at.desc())
                .limit(1)
            ).scalar()

            if last_published and (now - last_published).total_seconds() < min_interval * 60:
                # Too soon for this language — reschedule
                item.scheduled_at = last_published + timedelta(minutes=min_interval)
                log.debug(
                    "autopilot.rescheduled",
                    adaptation_id=str(item.adaptation_id),
                    language=adapt_lang,
                    next_at=item.scheduled_at.isoformat(),
                )
                continue

            # Daily limit check PER LANGUAGE
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            lang_max_per_day = lang_cfg["max_posts_per_day"]
            today_published = session.execute(
                select(func.count(AutopilotQueueItem.id))
                .join(
                    ChannelAdaptation,
                    AutopilotQueueItem.adaptation_id == ChannelAdaptation.id,
                )
                .where(
                    AutopilotQueueItem.channel_id == channel.id,
                    AutopilotQueueItem.status == "published",
                    AutopilotQueueItem.published_at >= today_start,
                    ChannelAdaptation.language == adapt_lang,
                )
            ).scalar() or 0

            if today_published >= lang_max_per_day:
                item.status = "skipped"
                item.skip_reason = f"daily_limit_{adapt_lang} ({today_published}/{lang_max_per_day})"
                continue

            # Cover readiness check (adaptation already loaded above)
            cover_policy = config.get("cover_policy", "short_post_optional")

            # Always wait for a cover that's still being generated —
            # "optional" means we can skip if cover is absent or permanently
            # failed, NOT that we should publish while it's still creating.
            if adaptation.cover_status == "generating":
                log.debug(
                    "autopilot.waiting_cover_generating",
                    adaptation_id=str(adaptation.id),
                )
                continue

            # For formats/strategies where cover IS required, also wait
            # for error/retry states (they might still resolve)
            needs_cover = True
            if cover_policy == "short_post_optional" and adaptation.content_format == "short_post":
                needs_cover = False
            if cover_policy == "never":
                needs_cover = False
            if item.strategy == "express":
                needs_cover = False

            if needs_cover and adaptation.cover_status != "ready":
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

            # Material-level dedup: skip if same material+language was
            # already published or is being published for this channel
            already_published_material = session.execute(
                select(AutopilotQueueItem.id)
                .join(
                    ChannelAdaptation,
                    AutopilotQueueItem.adaptation_id == ChannelAdaptation.id,
                )
                .where(
                    AutopilotQueueItem.channel_id == channel.id,
                    AutopilotQueueItem.id != item.id,
                    AutopilotQueueItem.status.in_(["publishing", "published"]),
                    ChannelAdaptation.material_id == adaptation.material_id,
                    ChannelAdaptation.language == adapt_lang,
                )
                .limit(1)
            ).scalar_one_or_none()

            if already_published_material:
                item.status = "skipped"
                item.skip_reason = f"material_already_published_{adapt_lang}"
                log.info(
                    "autopilot.skip_material_dup",
                    adaptation_id=str(item.adaptation_id),
                    language=adapt_lang,
                    material_id=str(adaptation.material_id),
                )
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


@shared_task(
    bind=True,
    name="workers.autopilot_tasks.autopilot_archive_stale_drafts",
    max_retries=1,
    queue="ai_queue",
)
def autopilot_archive_stale_drafts(self):
    """Archive draft adaptations whose source material is past the freshness window.

    Runs hourly. Without this, the system accumulates draft adaptations forever,
    bloating the rank_and_queue candidate pool and burning the lazy-adapt budget
    on materials that will never publish anyway. See ADR-007.

    Threshold: 48 hours after scrape time (twice the default queue cutoff of 24h,
    giving slack for materials briefly under the threshold to make it through).
    """
    from app.models.channel_adaptation import ChannelAdaptation
    from app.models.material import RawMaterial

    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)

    with get_sync_session() as session:
        stale = session.execute(
            select(ChannelAdaptation)
            .join(RawMaterial, ChannelAdaptation.material_id == RawMaterial.id)
            .where(
                ChannelAdaptation.status == "draft",
                RawMaterial.scraped_at < cutoff,
            )
        ).scalars().all()

        for adapt in stale:
            adapt.status = "archived"

        session.commit()
        log.info("autopilot.archive_stale_drafts.done", archived=len(stale))
        return {"status": "ok", "archived": len(stale)}
