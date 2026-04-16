"""AI classification Celery tasks.

Task flow:
    classify_material(material_id, tenant_id) → call Claude → update status & metadata
    classify_new_materials(tenant_id) → find all "new" → fan-out to classify_material
"""

import asyncio
import uuid
from datetime import datetime, timezone

import structlog
from celery import shared_task
from sqlalchemy import select, update

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


@shared_task(bind=True, name="workers.ai_tasks.classify_material", max_retries=2)
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
            return {"status": "error", "reason": "empty_result"}

        # Update material with classification data
        meta = {**material.metadata_}
        meta["ai_classification"] = result
        meta["classified_at"] = datetime.now(timezone.utc).isoformat()
        meta["classified_by"] = "gemini-3-pro"

        material.metadata_ = meta
        material.status = "classified"
        session.commit()

        log.info(
            "ai.classify.done",
            category=result.get("category"),
            relevance=result.get("relevance_score"),
            sentiment=result.get("sentiment"),
        )
        
        # Route to evaluation for all active channels in the tenant
        evaluate_material_for_channels.delay(material_id, tenant_id)
        
        return {
            "status": "ok",
            "category": result.get("category"),
            "relevance_score": result.get("relevance_score"),
        }


@shared_task(name="workers.ai_tasks.classify_new_materials")
def classify_new_materials(tenant_id: str | None = None):
    """Find all materials with status 'new' and queue classification.

    If tenant_id is None, classifies for all tenants.
    """
    log = logger.bind(tenant_id=tenant_id)
    log.info("ai.classify_batch.start")

    with get_sync_session() as session:
        query = select(RawMaterial.id, RawMaterial.tenant_id).where(
            RawMaterial.status == "new"
        )
        if tenant_id:
            query = query.where(RawMaterial.tenant_id == uuid.UUID(tenant_id))

        # Limit batch to avoid overwhelming the API
        query = query.limit(50)
        materials = session.execute(query).all()

    queued = 0
    for mat_id, t_id in materials:
        classify_material.delay(str(mat_id), str(t_id))
        queued += 1

    log.info("ai.classify_batch.done", queued=queued)
    return {"queued": queued}


@shared_task(bind=True, name="workers.ai_tasks.evaluate_material_for_channels", max_retries=3)
def evaluate_material_for_channels(self, material_id: str, tenant_id: str):
    """Evaluate a classified material against all active channels for a tenant."""
    log = logger.bind(material_id=material_id, tenant_id=tenant_id)
    log.info("ai.evaluate_channels.start")

    from app.models.channel import Channel
    from app.models.channel_score import MaterialChannelScore

    with get_sync_session() as session:
        material = session.get(RawMaterial, uuid.UUID(material_id))
        if not material or material.status != "classified":
            log.error("ai.evaluate_channels.invalid_state")
            return {"status": "error", "reason": "invalid_state"}

        # Get all active channels for this tenant
        channels = session.execute(
            select(Channel).where(
                Channel.tenant_id == uuid.UUID(tenant_id),
                Channel.is_active == True,
                Channel.editorial_guidelines != "", 
                Channel.target_audience != ""
            )
        ).scalars().all()

        if not channels:
            log.info("ai.evaluate_channels.no_channels")
            return {"status": "ok", "evaluated": 0}

        from ai.editor import evaluate_material_for_channel, AIServiceTemporarilyUnavailable

        # Extract material data once
        material_data = {
            "original_title": material.title,
            "summary_ru": material.metadata_.get("ai_classification", {}).get("summary_ru"),
            "summary_en": material.metadata_.get("ai_classification", {}).get("summary_en"),
            "category": material.metadata_.get("ai_classification", {}).get("category"),
            "tags": material.metadata_.get("ai_classification", {}).get("tags", []),
            "sentiment": material.metadata_.get("ai_classification", {}).get("sentiment"),
            "relevance_score": material.metadata_.get("ai_classification", {}).get("relevance_score"),
        }

        evaluated = 0
        for channel in channels:
            # Check if score already exists (e.g. on retry)
            existing = session.execute(
                select(MaterialChannelScore).where(
                    MaterialChannelScore.material_id == material.id,
                    MaterialChannelScore.channel_id == channel.id
                )
            ).scalar_one_or_none()

            if existing:
                continue

            try:
                result = _run_async(evaluate_material_for_channel(
                    material_data=material_data,
                    channel_guidelines=channel.editorial_guidelines,
                    channel_audience=channel.target_audience
                ))
                
                if result:
                    score = MaterialChannelScore(
                        material_id=material.id,
                        channel_id=channel.id,
                        tenant_id=material.tenant_id,
                        relevance_score=result.get("relevance_score", 0),
                        hype_score=result.get("hype_score", 0),
                        is_recommended=result.get("is_recommended", False),
                        explanation=result.get("explanation", "")
                    )
                    session.add(score)
                    session.commit()
                    evaluated += 1
                    
            except AIServiceTemporarilyUnavailable as e:
                log.warning("ai.evaluate_channels.api_unavailable", error=str(e))
                session.commit()
                # Retry if we hit rate limits mid-loop
                raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
            except Exception as e:
                log.error("ai.evaluate_channels.eval_failed", channel_id=str(channel.id), error=str(e))
                continue

    log.info("ai.evaluate_channels.done", evaluated=evaluated)
    return {"status": "ok", "evaluated": evaluated}
