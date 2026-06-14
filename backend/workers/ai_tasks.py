"""AI classification and editorial Celery tasks.

Task flow:
    classify_material(material_id, tenant_id) → call Gemini → update status & metadata
    classify_new_materials(tenant_id) → find all "new" → fan-out to classify_material
    evaluate_material_for_projects(material_id, tenant_id) → score for all projects
    adapt_material_for_channels(material_id, project_id, tenant_id) → generate content
"""

import asyncio
import uuid
from datetime import datetime, timezone

import structlog
from celery import shared_task
from sqlalchemy import select

from app.database import get_sync_session
from app.models.material import RawMaterial

logger = structlog.get_logger()


def _run_async(coro):
    """Run async code from sync Celery context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
    except RuntimeError:
        pass
    return asyncio.run(coro)


@shared_task(bind=True, name="workers.ai_tasks.classify_material", max_retries=5)
def classify_material(self, material_id: str, tenant_id: str):
    """Classify a single material using Claude Haiku 4.5."""
    log = logger.bind(material_id=material_id, tenant_id=tenant_id)
    log.info("ai.classify.start")

    with get_sync_session() as session:
        material = session.get(RawMaterial, uuid.UUID(material_id))
        if not material:
            log.error("ai.classify.material_not_found")
            return {"status": "error", "reason": "not_found"}

        if str(material.tenant_id) != tenant_id:
            log.error("ai.classify.tenant_mismatch")
            return {"status": "error", "reason": "tenant_mismatch"}

        # Mark as classifying
        material.status = "classifying"
        session.flush()

        # Run classification
        from ai.classifier import classify_article, AIServiceTemporarilyUnavailable

        try:
            result = _run_async(classify_article(
                title=material.title,
                content=material.content_text,
                url=material.original_url,
            ))
        except AIServiceTemporarilyUnavailable as e:
            log.warning("ai.classify.api_unavailable", error=str(e))
            material.status = "new"  # Reset for retry later
            session.commit()
            raise self.retry(exc=e, countdown=120 * (self.request.retries + 1))
        except Exception as e:
            log.error("ai.classify.failed", error=str(e))
            material.status = "new"  # Reset
            material.metadata_ = {**material.metadata_, "classify_error": str(e)}
            session.commit()
            raise self.retry(exc=e, countdown=30 * (self.request.retries + 1))

        if not result:
            log.warning("ai.classify.empty_result")
            material.status = "new"  # Reset for retry
            session.commit()
            raise self.retry(
                exc=Exception("Empty classification result"),
                countdown=60 * (self.request.retries + 1),
            )

        # Update material with classification data
        meta = {**material.metadata_}

        # Normalize tags — AI sometimes returns them as a JSON string
        if isinstance(result.get("tags"), str):
            import json as _json
            try:
                result["tags"] = _json.loads(result["tags"])
            except (ValueError, _json.JSONDecodeError):
                result["tags"] = []
        if not isinstance(result.get("tags"), list):
            result["tags"] = []

        meta["ai_classification"] = result
        meta["classified_at"] = datetime.now(timezone.utc).isoformat()
        meta["classified_by"] = "gemini-3-pro"

        # Save semantic fingerprint for deduplication (Phase 2)
        key_entities = result.get("key_entities", [])
        if key_entities:
            meta["semantic_fingerprint"] = [e.lower().strip() for e in key_entities if e]

        # Canonical cross-language event key for semantic dedup (top-level for
        # cheap querying). Same real-world event in EN/GR/RU → same/overlapping key.
        event_key = result.get("event_key")
        if event_key:
            meta["event_key"] = event_key.lower().strip()

        material.metadata_ = meta
        material.status = "classified"
        session.commit()

        log.info(
            "ai.classify.done",
            category=result.get("category"),
            relevance=result.get("relevance_score"),
            sentiment=result.get("sentiment"),
        )

        # Auto-route to project scoring
        evaluate_material_for_projects.delay(material_id, tenant_id)

        return {
            "status": "ok",
            "category": result.get("category"),
            "relevance_score": result.get("relevance_score"),
        }


@shared_task(name="workers.ai_tasks.classify_new_materials")
def classify_new_materials(tenant_id: str | None = None):
    """Find all materials with status 'new' and queue classification."""
    log = logger.bind(tenant_id=tenant_id)
    log.info("ai.classify_batch.start")

    with get_sync_session() as session:
        query = select(RawMaterial.id, RawMaterial.tenant_id).where(
            RawMaterial.status == "new"
        )
        if tenant_id:
            query = query.where(RawMaterial.tenant_id == uuid.UUID(tenant_id))

        query = query.limit(50)
        materials = session.execute(query).all()

    queued = 0
    for mat_id, t_id in materials:
        classify_material.delay(str(mat_id), str(t_id))
        queued += 1

    log.info("ai.classify_batch.done", queued=queued)
    return {"queued": queued}


@shared_task(name="workers.ai_tasks.evaluate_classified_materials")
def evaluate_classified_materials(tenant_id: str | None = None):
    """Find classified materials without project scores and queue evaluation."""
    log = logger.bind(tenant_id=tenant_id)
    log.info("ai.evaluate_batch.start")

    from app.models.project_score import MaterialProjectScore

    with get_sync_session() as session:
        # Find classified materials that have NO project scores yet
        scored_ids = select(MaterialProjectScore.material_id).distinct()
        query = select(RawMaterial.id, RawMaterial.tenant_id).where(
            RawMaterial.status == "classified",
            ~RawMaterial.id.in_(scored_ids),
        )
        if tenant_id:
            query = query.where(RawMaterial.tenant_id == uuid.UUID(tenant_id))

        query = query.limit(30)  # Process in batches of 30
        materials = session.execute(query).all()

    queued = 0
    for mat_id, t_id in materials:
        evaluate_material_for_projects.delay(str(mat_id), str(t_id))
        queued += 1

    log.info("ai.evaluate_batch.done", queued=queued)
    return {"queued": queued}


@shared_task(bind=True, name="workers.ai_tasks.evaluate_material_for_projects", max_retries=5)
def evaluate_material_for_projects(self, material_id: str, tenant_id: str):
    """Evaluate a classified material against all active projects for a tenant.

    For each project with topic_guidelines set:
    - Call AI to score relevance + hype
    - Store result in MaterialProjectScore
    - If recommended → trigger adapt_material_for_channels
    """
    log = logger.bind(material_id=material_id, tenant_id=tenant_id)
    log.info("ai.evaluate_projects.start")

    from app.models.project import Project
    from app.models.project_score import MaterialProjectScore

    with get_sync_session() as session:
        material = session.get(RawMaterial, uuid.UUID(material_id))
        if not material or material.status != "classified":
            log.error("ai.evaluate_projects.invalid_state", status=material.status if material else None)
            return {"status": "error", "reason": "invalid_state"}

        # Get all active projects for this tenant that have guidelines set
        projects = session.execute(
            select(Project).where(
                Project.tenant_id == uuid.UUID(tenant_id),
                Project.is_active == True,
                Project.topic_guidelines != "",
            )
        ).scalars().all()

        if not projects:
            log.info("ai.evaluate_projects.no_projects")
            return {"status": "ok", "evaluated": 0}

        from ai.editor import evaluate_material_for_project, AIServiceTemporarilyUnavailable

        # Extract material data once
        ai_data = material.metadata_.get("ai_classification", {})
        material_data = {
            "original_title": material.title,
            "summary_ru": ai_data.get("summary_ru"),
            "summary_en": ai_data.get("summary_en"),
            "category": ai_data.get("category"),
            "tags": ai_data.get("tags", []),
            "sentiment": ai_data.get("sentiment"),
            "relevance_score": ai_data.get("relevance_score"),
        }

        evaluated = 0
        for project in projects:
            # Check if score already exists (idempotency)
            existing = session.execute(
                select(MaterialProjectScore).where(
                    MaterialProjectScore.material_id == material.id,
                    MaterialProjectScore.project_id == project.id,
                )
            ).scalar_one_or_none()

            if existing:
                continue

            try:
                result = _run_async(evaluate_material_for_project(
                    material_data=material_data,
                    topic_guidelines=project.topic_guidelines,
                    target_audience=project.target_audience,
                ))

                if result:
                    score = MaterialProjectScore(
                        material_id=material.id,
                        project_id=project.id,
                        tenant_id=material.tenant_id,
                        relevance_score=result.get("relevance_score", 0),
                        hype_score=result.get("hype_score", 0),
                        is_recommended=result.get("is_recommended", False),
                        explanation=result.get("explanation", ""),
                    )
                    session.add(score)
                    session.commit()
                    evaluated += 1

                    log.info(
                        "ai.evaluate_projects.scored",
                        project=project.name,
                        relevance=result.get("relevance_score"),
                        hype=result.get("hype_score"),
                        recommended=result.get("is_recommended"),
                    )

                    # Adaptation is triggered lazily by autopilot_rank_and_queue
                    # for only the top candidates. No eager adapt here.

            except AIServiceTemporarilyUnavailable as e:
                log.warning("ai.evaluate_projects.api_unavailable", error=str(e))
                session.commit()
                raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
            except Exception as e:
                log.error("ai.evaluate_projects.eval_failed", project_id=str(project.id), error=str(e))
                continue

        # Update material status to 'evaluated' after scoring
        material.status = "evaluated"
        session.commit()

    log.info("ai.evaluate_projects.done", evaluated=evaluated)
    return {"status": "ok", "evaluated": evaluated}


@shared_task(bind=True, name="workers.ai_tasks.adapt_material_for_channels", max_retries=5)
def adapt_material_for_channels(self, material_id: str, project_id: str, tenant_id: str):
    """Generate adapted content for the PRIMARY format of each channel.

    Only the first format in channel.content_formats is generated automatically.
    Additional formats can be generated on-demand via the /adaptations/generate API.

    For each active channel:
      For the PRIMARY content_format (first in list):
        For each language:
          → Call AI adapter → Store ChannelAdaptation
    """
    log = logger.bind(material_id=material_id, project_id=project_id)
    log.info("ai.adapt_channels.start")

    from app.models.channel import Channel
    from app.models.channel_adaptation import ChannelAdaptation

    with get_sync_session() as session:
        material = session.get(RawMaterial, uuid.UUID(material_id))
        if not material:
            log.error("ai.adapt_channels.material_not_found")
            return {"status": "error", "reason": "not_found"}

        # Get all active channels for this project
        channels = session.execute(
            select(Channel).where(
                Channel.project_id == uuid.UUID(project_id),
                Channel.is_active == True,
            )
        ).scalars().all()

        if not channels:
            log.info("ai.adapt_channels.no_channels")
            return {"status": "ok", "adapted": 0}

        from ai.adapter import adapt_material_for_channel, AIServiceTemporarilyUnavailable

        # Prepare material data
        ai_data = material.metadata_.get("ai_classification", {})
        material_data = {
            "original_title": material.title,
            "summary_ru": ai_data.get("summary_ru"),
            "summary_en": ai_data.get("summary_en"),
            "content_text": material.content_text,
            "original_url": material.original_url,
        }

        adapted = 0
        # Default primary formats per platform
        _platform_defaults = {
            "telegram": "short_post",
            "website": "longread",
            "youtube": "video_script",
        }

        # Use AI-suggested format when available (multi-format support)
        suggested_format = ai_data.get("suggested_format")

        for channel in channels:
            # Determine content format for this channel:
            # 1. Use AI-suggested format if it's in the channel's allowed formats
            # 2. Fall back to platform default
            # 3. Fall back to first allowed format
            channel_formats = channel.content_formats or ["short_post"]
            if suggested_format and suggested_format in channel_formats:
                primary_format = suggested_format
            else:
                default = _platform_defaults.get(channel.channel_type, "short_post")
                if default in channel_formats:
                    primary_format = default
                else:
                    primary_format = channel_formats[0]
            for language in channel.languages:
                # Check if adaptation already exists (idempotency)
                existing = session.execute(
                    select(ChannelAdaptation).where(
                        ChannelAdaptation.material_id == material.id,
                        ChannelAdaptation.channel_id == channel.id,
                        ChannelAdaptation.language == language,
                        ChannelAdaptation.content_format == primary_format,
                    )
                ).scalar_one_or_none()

                if existing:
                    continue

                try:
                    result = _run_async(adapt_material_for_channel(
                        material_data=material_data,
                        channel_name=channel.name,
                        channel_type=channel.channel_type,
                        content_format=primary_format,
                        tone_of_voice=channel.tone_of_voice,
                        language=language,
                        formatting_rules=channel.formatting_rules,
                        editorial_rules=channel.editorial_rules,
                    ))

                    if result:
                        adaptation = ChannelAdaptation(
                            material_id=material.id,
                            channel_id=channel.id,
                            tenant_id=material.tenant_id,
                            language=language,
                            content_format=primary_format,
                            headline=result.get("headline", ""),
                            body=result.get("body", ""),
                            priority=result.get("priority", "normal"),
                            status="draft",
                        )
                        session.add(adaptation)
                        session.commit()
                        adapted += 1

                        log.info(
                            "ai.adapt_channels.created",
                            channel=channel.name,
                            format=primary_format,
                            language=language,
                            priority=result.get("priority"),
                        )

                except AIServiceTemporarilyUnavailable as e:
                    log.warning("ai.adapt_channels.api_unavailable", error=str(e))
                    session.commit()
                    raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
                except Exception as e:
                    log.error(
                        "ai.adapt_channels.adapt_failed",
                        channel=channel.name, language=language,
                        error=str(e),
                    )
                    continue

    if adapted == 0:
        log.warning("ai.adapt_channels.all_failed", material_id=material_id)

    # Update material status to 'adapted' if any adaptations were created
    if adapted > 0:
        with get_sync_session() as session:
            material = session.get(RawMaterial, uuid.UUID(material_id))
            if material:
                material.status = "adapted"
                session.commit()

    log.info("ai.adapt_channels.done", adapted=adapted)
    return {"status": "ok", "adapted": adapted}


@shared_task(bind=True, name="workers.ai_tasks.adapt_single_format", max_retries=3)
def adapt_single_format(
    self, material_id: str, channel_id: str, content_format: str, language: str, tenant_id: str
):
    """Generate adaptation for a SINGLE material × channel × format × language.

    Called on-demand from the editorial UI when the editor clicks
    "Generate as Longread" / "Generate as Video Script" etc.
    """
    log = logger.bind(
        material_id=material_id, channel_id=channel_id,
        content_format=content_format, language=language,
    )
    log.info("ai.adapt_single.start")

    from app.models.channel import Channel
    from app.models.channel_adaptation import ChannelAdaptation

    with get_sync_session() as session:
        material = session.get(RawMaterial, uuid.UUID(material_id))
        if not material:
            log.error("ai.adapt_single.material_not_found")
            return {"status": "error", "reason": "not_found"}

        channel = session.get(Channel, uuid.UUID(channel_id))
        if not channel:
            log.error("ai.adapt_single.channel_not_found")
            return {"status": "error", "reason": "channel_not_found"}

        # Idempotency check
        existing = session.execute(
            select(ChannelAdaptation).where(
                ChannelAdaptation.material_id == material.id,
                ChannelAdaptation.channel_id == channel.id,
                ChannelAdaptation.language == language,
                ChannelAdaptation.content_format == content_format,
            )
        ).scalar_one_or_none()

        if existing:
            log.info("ai.adapt_single.already_exists")
            return {"status": "ok", "adaptation_id": str(existing.id), "already_existed": True}

        from ai.adapter import adapt_material_for_channel, AIServiceTemporarilyUnavailable

        ai_data = material.metadata_.get("ai_classification", {})
        material_data = {
            "original_title": material.title,
            "summary_ru": ai_data.get("summary_ru"),
            "summary_en": ai_data.get("summary_en"),
            "content_text": material.content_text,
            "original_url": material.original_url,
        }

        try:
            result = _run_async(adapt_material_for_channel(
                material_data=material_data,
                channel_name=channel.name,
                channel_type=channel.channel_type,
                content_format=content_format,
                tone_of_voice=channel.tone_of_voice,
                language=language,
                formatting_rules=channel.formatting_rules,
                editorial_rules=channel.editorial_rules,
            ))

            if result:
                adaptation = ChannelAdaptation(
                    material_id=material.id,
                    channel_id=channel.id,
                    tenant_id=material.tenant_id,
                    language=language,
                    content_format=content_format,
                    headline=result.get("headline", ""),
                    body=result.get("body", ""),
                    priority=result.get("priority", "normal"),
                    status="draft",
                )
                session.add(adaptation)
                session.commit()
                log.info("ai.adapt_single.created", adaptation_id=str(adaptation.id))
                return {"status": "ok", "adaptation_id": str(adaptation.id)}

        except AIServiceTemporarilyUnavailable as e:
            log.warning("ai.adapt_single.api_unavailable", error=str(e))
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        except Exception as e:
            log.error("ai.adapt_single.failed", error=str(e))
            raise self.retry(exc=e, countdown=30 * (self.request.retries + 1))

    return {"status": "error", "reason": "empty_result"}


@shared_task(
    bind=True,
    name="workers.ai_tasks.adapt_and_enqueue_autopilot",
    max_retries=3,
)
def adapt_and_enqueue_autopilot(
    self,
    material_id: str,
    channel_id: str,
    content_format: str,
    language: str,
    tenant_id: str,
    project_id: str,
):
    """Manual enqueue from Recommendations: adapt if needed, then queue.

    Used when an editor clicks "Send to autopilot" on a recommendation card.
    Bypasses the rank_and_queue ratio balancing — the user explicitly chose
    this material/channel/format combination.
    """
    from datetime import datetime as _dt, timedelta as _td, timezone as _tz
    from app.models.autopilot_queue import AutopilotQueueItem
    from app.models.channel import Channel
    from app.models.channel_adaptation import ChannelAdaptation

    log = logger.bind(
        material_id=material_id, channel_id=channel_id,
        content_format=content_format, language=language,
    )
    log.info("autopilot.manual_enqueue.start")

    with get_sync_session() as session:
        # Find or create adaptation
        adaptation = session.execute(
            select(ChannelAdaptation).where(
                ChannelAdaptation.material_id == uuid.UUID(material_id),
                ChannelAdaptation.channel_id == uuid.UUID(channel_id),
                ChannelAdaptation.language == language,
                ChannelAdaptation.content_format == content_format,
            )
        ).scalar_one_or_none()

        if not adaptation:
            # Synchronously generate the adaptation via existing helper
            log.info("autopilot.manual_enqueue.generating_adaptation")
            from ai.adapter import adapt_material_for_channel, AIServiceTemporarilyUnavailable

            material = session.get(RawMaterial, uuid.UUID(material_id))
            channel = session.get(Channel, uuid.UUID(channel_id))
            if not material or not channel:
                log.error("autopilot.manual_enqueue.missing_entity")
                return {"status": "error", "reason": "not_found"}

            ai_data = material.metadata_.get("ai_classification", {})
            material_data = {
                "original_title": material.title,
                "summary_ru": ai_data.get("summary_ru"),
                "summary_en": ai_data.get("summary_en"),
                "content_text": material.content_text,
                "original_url": material.original_url,
            }
            try:
                result = _run_async(adapt_material_for_channel(
                    material_data=material_data,
                    channel_name=channel.name,
                    channel_type=channel.channel_type,
                    content_format=content_format,
                    tone_of_voice=channel.tone_of_voice,
                    language=language,
                    formatting_rules=channel.formatting_rules,
                    editorial_rules=channel.editorial_rules,
                ))
            except AIServiceTemporarilyUnavailable as e:
                raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

            if not result:
                log.error("autopilot.manual_enqueue.adapt_empty")
                return {"status": "error", "reason": "adapt_failed"}

            adaptation = ChannelAdaptation(
                material_id=material.id,
                channel_id=channel.id,
                tenant_id=material.tenant_id,
                language=language,
                content_format=content_format,
                headline=result.get("headline", ""),
                body=result.get("body", ""),
                priority=result.get("priority", "normal"),
                status="draft",
            )
            session.add(adaptation)
            session.flush()
            log.info("autopilot.manual_enqueue.adaptation_created", adaptation_id=str(adaptation.id))

        # Prevent duplicate active queue items for this adaptation+channel
        existing_queue = session.execute(
            select(AutopilotQueueItem).where(
                AutopilotQueueItem.adaptation_id == adaptation.id,
                AutopilotQueueItem.channel_id == uuid.UUID(channel_id),
                AutopilotQueueItem.status.in_(["queued", "shadow", "approved", "publishing"]),
            )
        ).scalar_one_or_none()
        if existing_queue:
            log.info("autopilot.manual_enqueue.already_queued", queue_item_id=str(existing_queue.id))
            return {"status": "ok", "queue_item_id": str(existing_queue.id), "already_existed": True}

        # Create queue item, bypassing ratio balancing
        queue_item = AutopilotQueueItem(
            tenant_id=uuid.UUID(tenant_id),
            channel_id=uuid.UUID(channel_id),
            adaptation_id=adaptation.id,
            project_id=uuid.UUID(project_id),
            final_score=8.0,  # Manual nominal score
            freshness_score=10.0,
            uniqueness_score=10.0,
            engagement_predict=5.0,
            strategy="express",  # Express skips shadow + cover wait
            scheduled_at=_dt.now(_tz.utc) + _td(minutes=2),
            status="queued",
        )
        session.add(queue_item)
        session.commit()

        # Cover policy (same as autopilot_rank_and_queue):
        #   * Any format with a source image → attach it.
        #   * Non-flash without source image → AI gen.
        #   * Flash without source image → no cover.
        if not adaptation.cover_status:
            material_for_cover = session.get(RawMaterial, uuid.UUID(material_id))
            mat_meta = (material_for_cover.metadata_ or {}) if material_for_cover else {}
            src_cover = (
                mat_meta.get("cover_image")
                if mat_meta.get("cover_status") == "ready"
                else None
            )
            if src_cover and src_cover.get("url"):
                adaptation.cover_image_url = src_cover["url"]
                adaptation.cover_status = "ready"
                session.commit()
                log.info(
                    "autopilot.manual_enqueue.cover_from_source",
                    format=content_format,
                    sha=(src_cover.get("sha256") or "")[:12],
                )
            elif content_format != "flash":
                adaptation.cover_status = "generating"
                adaptation.cover_retry_count = 0
                session.commit()
                generate_adaptation_cover.delay(str(adaptation.id), tenant_id)

        log.info("autopilot.manual_enqueue.queued", queue_item_id=str(queue_item.id))
        return {"status": "ok", "queue_item_id": str(queue_item.id), "adaptation_id": str(adaptation.id)}


@shared_task(
    bind=True,
    name="workers.ai_tasks.generate_cover_image",
    max_retries=2,
    queue="media_queue",
)
def generate_cover_image(self, material_id: str, tenant_id: str, language: str = "ru"):
    """Generate an AI cover image for a material.

    Flow:
        1. Gemini generates an optimal prompt from news context
        2. GPT Image-2 generates a photorealistic 16:9 image
        3. Image is downloaded and saved to MinIO
        4. Material metadata is updated with the cover URL
    """
    log = logger.bind(material_id=material_id, language=language)
    log.info("image.generate.start")

    with get_sync_session() as session:
        material = session.get(RawMaterial, uuid.UUID(material_id))
        if not material:
            log.error("image.generate.material_not_found")
            return {"status": "error", "reason": "not_found"}

        if str(material.tenant_id) != tenant_id:
            log.error("image.generate.tenant_mismatch")
            return {"status": "error", "reason": "tenant_mismatch"}

        # Mark as generating in metadata
        meta = {**material.metadata_}
        meta["cover_status"] = "generating"
        material.metadata_ = meta
        session.commit()

        # Prepare context
        ai_data = meta.get("ai_classification", {})
        headline = ai_data.get("summary_ru") or material.title or ""
        summary = ai_data.get("summary_en") or ai_data.get("summary_ru") or ""

        from ai.image_generator import generate_cover_image as gen_image, ImageGenerationError

        try:
            result = _run_async(gen_image(
                headline=headline,
                summary=summary,
                language=language,
                content_text=material.content_text or "",
            ))
        except ImageGenerationError as e:
            from ai.provider_health import is_hard_failure
            meta = {**material.metadata_}
            if is_hard_failure(str(e)):
                # Provider systemically down — don't retry (circuit breaker).
                log.warning("image.generate.provider_down_no_retry", error=str(e)[:120])
                meta["cover_status"] = "permanently_failed"
                meta["cover_error"] = str(e)[:300]
                material.metadata_ = meta
                session.commit()
                return {"status": "error", "reason": "provider_down"}
            log.error("image.generate.failed", error=str(e))
            meta["cover_status"] = "error"
            meta["cover_error"] = str(e)
            material.metadata_ = meta
            session.commit()
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

        if not result or not result.get("image_url"):
            log.error("image.generate.no_url")
            meta = {**material.metadata_}
            meta["cover_status"] = "error"
            material.metadata_ = meta
            session.commit()
            return {"status": "error", "reason": "no_image_url"}

        # Download image and save to MinIO
        from app.services.storage import download_and_upload

        object_name = f"covers/{material_id}.png"
        try:
            _run_async(download_and_upload(
                url=result["image_url"],
                object_name=object_name,
            ))
        except Exception as e:
            log.error("image.generate.upload_failed", error=str(e))
            meta = {**material.metadata_}
            meta["cover_status"] = "error"
            meta["cover_error"] = f"Upload failed: {e}"
            material.metadata_ = meta
            session.commit()
            raise self.retry(exc=e, countdown=30 * (self.request.retries + 1))

        # Update material metadata with cover info
        meta = {**material.metadata_}
        meta["cover_image"] = {
            "url": f"/api/v1/files/{object_name}",
            "prompt": result.get("prompt", ""),
            "overlay_text": result.get("overlay_text", ""),
            "task_id": result.get("task_id", ""),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "language": language,
        }
        meta["cover_status"] = "ready"
        if "cover_error" in meta:
            del meta["cover_error"]
        material.metadata_ = meta
        session.commit()

        log.info(
            "image.generate.done",
            object_name=object_name,
            overlay=result.get("overlay_text", "")[:50],
        )
        return {
            "status": "ok",
            "cover_url": f"/api/v1/files/{object_name}",
        }


@shared_task(
    bind=True,
    name="workers.ai_tasks.generate_adaptation_cover",
    max_retries=5,
    queue="media_queue",
)
def generate_adaptation_cover(self, adaptation_id: str, tenant_id: str, with_overlay: bool | None = None):
    """Generate an AI cover image for a specific adaptation.

    with_overlay=True  → photo with a short headline baked in (poster style).
    with_overlay=False → clean photorealistic photo, no text.
    with_overlay=None  → derive from the material's suggested_cover_style
                         (photo_text → overlay, otherwise clean). This keeps
                         retries/manual paths consistent with the chosen style.
    """
    from app.models.channel_adaptation import ChannelAdaptation

    log = logger.bind(adaptation_id=adaptation_id)
    log.info("image.adaptation.start")

    with get_sync_session() as session:
        adaptation = session.get(ChannelAdaptation, uuid.UUID(adaptation_id))
        if not adaptation:
            log.error("image.adaptation.not_found")
            return {"status": "error", "reason": "not_found"}

        if str(adaptation.tenant_id) != tenant_id:
            log.error("image.adaptation.tenant_mismatch")
            return {"status": "error", "reason": "tenant_mismatch"}

        # Get material for context
        material = session.get(RawMaterial, adaptation.material_id)
        if not material:
            log.error("image.adaptation.material_not_found")
            adaptation.cover_status = "error"
            session.commit()
            return {"status": "error", "reason": "material_not_found"}

        language = adaptation.language
        log = log.bind(language=language)

        # Prepare context from adaptation + material
        headline = adaptation.headline or ""
        ai_data = (material.metadata_ or {}).get("ai_classification", {})
        summary = ai_data.get("summary_en") or ai_data.get("summary_ru") or ""

        # Resolve overlay mode: explicit arg wins; otherwise derive from the
        # AI-suggested cover style so retries/manual paths stay consistent.
        if with_overlay is None:
            cover_style = ai_data.get("suggested_cover_style", "photo_clean")
            overlay_mode = cover_style == "photo_text"
        else:
            overlay_mode = with_overlay
        log = log.bind(with_overlay=overlay_mode)

        from ai.image_generator import generate_cover_image as gen_image, ImageGenerationError
        from ai.provider_health import is_hard_failure

        try:
            result = _run_async(gen_image(
                headline=headline,
                summary=summary,
                language=language,
                content_text=material.content_text or "",
                with_overlay=overlay_mode,
            ))
        except ImageGenerationError as e:
            # Circuit breaker: on a systemic failure (credits/network/cooldown)
            # do NOT retry — that's what burned all credits overnight (21 covers
            # → ~2500 attempts). Mark permanently_failed so the periodic
            # retry_covers sweep also leaves it alone until the breaker clears.
            if is_hard_failure(str(e)):
                log.warning("image.adaptation.provider_down_no_retry", error=str(e)[:120])
                adaptation.cover_status = "permanently_failed"
                adaptation.cover_last_error = str(e)[:300]
                session.commit()
                return {"status": "error", "reason": "provider_down"}
            log.error("image.adaptation.failed", error=str(e))
            adaptation.cover_status = "error"
            adaptation.cover_last_error = str(e)
            session.commit()
            raise self.retry(exc=e, countdown=180 * (self.request.retries + 1))

        if not result or not result.get("image_url"):
            log.error("image.adaptation.no_url")
            adaptation.cover_status = "error"
            adaptation.cover_last_error = "no_image_url"
            session.commit()
            return {"status": "error", "reason": "no_image_url"}

        # Download image and save to MinIO
        from app.services.storage import download_and_upload

        object_name = f"covers/{adaptation_id}_{language}.png"
        try:
            _run_async(download_and_upload(
                url=result["image_url"],
                object_name=object_name,
            ))
        except Exception as e:
            log.error("image.adaptation.upload_failed", error=str(e))
            adaptation.cover_status = "error"
            session.commit()
            raise self.retry(exc=e, countdown=30 * (self.request.retries + 1))

        # Update adaptation with cover info
        adaptation.cover_image_url = f"/api/v1/files/{object_name}"
        adaptation.cover_status = "ready"
        session.commit()

        log.info(
            "image.adaptation.done",
            object_name=object_name,
            overlay=result.get("overlay_text", "")[:50],
        )
        return {
            "status": "ok",
            "adaptation_id": adaptation_id,
            "cover_url": f"/api/v1/files/{object_name}",
        }
