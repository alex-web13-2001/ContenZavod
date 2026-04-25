"""Projects CRUD endpoints."""

import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db, get_tenant_id
from app.schemas.project import ProjectCreate, ProjectListResponse, ProjectResponse, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=dict)
async def list_projects(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    """List all projects for the current tenant."""
    from app.services.project_service import ProjectService

    service = ProjectService(db, tenant_id)
    items, total = await service.list(page, per_page)
    return {
        "items": [ProjectListResponse.model_validate(p) for p in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": math.ceil(total / per_page) if total > 0 else 0,
    }


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    from app.services.project_service import ProjectService

    service = ProjectService(db, tenant_id)
    project = await service.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse.model_validate(project)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    from app.services.project_service import ProjectService

    service = ProjectService(db, tenant_id)
    project = await service.create(data)
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    from app.services.project_service import ProjectService

    service = ProjectService(db, tenant_id)
    project = await service.update(project_id, data)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    from app.services.project_service import ProjectService

    service = ProjectService(db, tenant_id)
    deleted = await service.delete(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")


@router.get("/{project_id}/recommendations")
async def list_project_recommendations(
    project_id: str,
    recommended_only: bool = Query(True),
    pipeline_status: str = Query("inbox", pattern=r"^(inbox|in_progress|published|rejected)$"),
    category: str | None = Query(None),
    date_from: str | None = Query(None, description="ISO date, e.g. 2026-04-20"),
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    """List materials scored for this project, filtered by pipeline stage."""
    import uuid as _uuid
    from datetime import datetime
    from sqlalchemy import select, func, case
    from app.models.project_score import MaterialProjectScore
    from app.models.material import RawMaterial
    from app.models.publish_job import PublishJob
    from app.models.channel_adaptation import ChannelAdaptation

    tid = _uuid.UUID(tenant_id)
    pid = _uuid.UUID(project_id)

    # --- Pipeline counts (always return all counts) ---
    count_query = (
        select(
            MaterialProjectScore.editorial_status,
            func.count().label("cnt"),
        )
        .where(
            MaterialProjectScore.project_id == pid,
            MaterialProjectScore.tenant_id == tid,
        )
    )
    if recommended_only:
        count_query = count_query.where(MaterialProjectScore.is_recommended == True)
    count_query = count_query.group_by(MaterialProjectScore.editorial_status)

    count_rows = (await db.execute(count_query)).all()
    pipeline_counts = {"inbox": 0, "in_progress": 0, "published": 0, "rejected": 0}
    for row_status, cnt in count_rows:
        if row_status in pipeline_counts:
            pipeline_counts[row_status] = cnt

    # --- Main query ---
    query = (
        select(MaterialProjectScore)
        .where(
            MaterialProjectScore.project_id == pid,
            MaterialProjectScore.tenant_id == tid,
            MaterialProjectScore.editorial_status == pipeline_status,
        )
    )

    if recommended_only:
        query = query.where(MaterialProjectScore.is_recommended == True)

    # Date filter — different date field per pipeline stage
    _joined_raw = False
    if date_from:
        try:
            dt = datetime.fromisoformat(date_from)
            if pipeline_status == "published":
                # Filter by actual publication date via PublishJob
                from app.models.publish_job import PublishJob
                pub_filter_subq = (
                    select(ChannelAdaptation.material_id)
                    .join(PublishJob, PublishJob.content_id == ChannelAdaptation.id)
                    .where(
                        PublishJob.status == "published",
                        PublishJob.published_at >= dt,
                    )
                    .distinct()
                    .subquery()
                )
                query = query.where(
                    MaterialProjectScore.material_id.in_(select(pub_filter_subq.c.material_id))
                )
            elif pipeline_status == "in_progress":
                # Filter by when the material was moved to in_progress (updated_at on score)
                query = query.where(MaterialProjectScore.updated_at >= dt)
            else:
                # inbox / rejected — filter by material creation date
                query = query.join(
                    RawMaterial, MaterialProjectScore.material_id == RawMaterial.id
                ).where(RawMaterial.created_at >= dt)
                _joined_raw = True
        except ValueError:
            pass

    # Category filter
    if category:
        if _joined_raw:
            # Already joined RawMaterial
            query = query.where(
                RawMaterial.metadata_["ai_classification"]["category"].astext == category
            )
        else:
            query = query.join(
                RawMaterial, MaterialProjectScore.material_id == RawMaterial.id
            ).where(
                RawMaterial.metadata_["ai_classification"]["category"].astext == category
            )

    # Order: published by publish date, others by score created_at desc
    if pipeline_status == "published":
        # Join to PublishJob to sort by actual publish date
        pub_date_subq = (
            select(
                ChannelAdaptation.material_id,
                func.max(PublishJob.published_at).label("latest_pub"),
            )
            .join(PublishJob, PublishJob.content_id == ChannelAdaptation.id)
            .where(PublishJob.status == "published")
            .group_by(ChannelAdaptation.material_id)
            .subquery()
        )
        query = query.outerjoin(
            pub_date_subq, MaterialProjectScore.material_id == pub_date_subq.c.material_id
        ).order_by(pub_date_subq.c.latest_pub.desc().nullslast(), MaterialProjectScore.created_at.desc())
    else:
        query = query.order_by(MaterialProjectScore.created_at.desc())

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    offset = (page - 1) * per_page
    result = await db.execute(query.offset(offset).limit(per_page))
    scores = result.scalars().all()

    # Enrich with material data
    items = []
    for s in scores:
        material = await db.get(RawMaterial, s.material_id)
        ai_data = (material.metadata_.get("ai_classification", {}) if material else {})

        # Find Russian adaptation headline (for display)
        ru_adapt = None
        if material:
            ru_adapt = (await db.execute(
                select(ChannelAdaptation).where(
                    ChannelAdaptation.material_id == material.id,
                    ChannelAdaptation.language == "ru",
                ).order_by(ChannelAdaptation.created_at.desc()).limit(1)
            )).scalar_one_or_none()

        item = {
            "id": str(s.id),
            "material_id": str(s.material_id),
            "project_id": str(s.project_id),
            "relevance_score": s.relevance_score,
            "hype_score": s.hype_score,
            "is_recommended": s.is_recommended,
            "explanation": s.explanation,
            "editorial_status": s.editorial_status,
            "created_at": s.created_at.isoformat(),
            "material_title": material.title if material else None,
            "headline_ru": ru_adapt.headline if ru_adapt else None,
            "material_url": material.original_url if material else None,
            "material_status": material.status if material else None,
            "category": ai_data.get("category"),
            "summary_ru": ai_data.get("summary_ru"),
            "tags": ai_data.get("tags", []),
            "is_breaking": ai_data.get("is_breaking", False),
            "cover_image_url": meta.get("cover_image", {}).get("url") if (meta := (material.metadata_ or {})) else None,
            "cover_status": (material.metadata_ or {}).get("cover_status"),
        }

        # For published items — enrich with publish data + ALL published adaptations
        if pipeline_status == "published" and material:
            from app.models.channel import Channel

            # Get ALL published jobs for this material
            pub_jobs = (await db.execute(
                select(PublishJob, ChannelAdaptation)
                .join(ChannelAdaptation, PublishJob.content_id == ChannelAdaptation.id)
                .where(
                    ChannelAdaptation.material_id == material.id,
                    PublishJob.status == "published",
                )
                .order_by(PublishJob.published_at.desc())
            )).all()

            published_posts = []
            latest_pub = None

            for job, adapt in pub_jobs:
                ch = await db.get(Channel, adapt.channel_id)
                published_posts.append({
                    "adaptation_id": str(adapt.id),
                    "lang": adapt.language,
                    "format": adapt.content_format,
                    "headline": adapt.headline,
                    "body": adapt.body,
                    "channel_name": ch.name if ch else "",
                    "channel_type": ch.channel_type if ch else "telegram",
                    "published_at": job.published_at.isoformat() if job.published_at else None,
                    "platform_post_id": job.platform_post_id,
                    "cover_image_url": adapt.cover_image_url,
                    "cover_status": adapt.cover_status,
                    # Telegram stats from publish job
                    "views": job.views or 0,
                    "reactions": job.reactions or 0,
                    "forwards": job.forwards or 0,
                    "comments": job.comments or 0,
                })
                if not latest_pub or (job.published_at and (not latest_pub.published_at or job.published_at > latest_pub.published_at)):
                    latest_pub = job

            item["published_posts"] = published_posts
            item["published_at"] = latest_pub.published_at.isoformat() if latest_pub and latest_pub.published_at else s.created_at.isoformat()
            item["platform_post_id"] = latest_pub.platform_post_id if latest_pub else None

        items.append(item)

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pipeline_counts": pipeline_counts,
    }


@router.patch("/{project_id}/recommendations/{score_id}/status")
async def update_recommendation_status(
    project_id: str,
    score_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    """Change editorial pipeline status of a material in this project.

    Valid transitions:
      inbox → in_progress  (take into work — triggers adaptation generation)
      inbox → rejected     (reject material)
      in_progress → published (via publish flow, not usually called directly)
      * → rejected         (reject from any stage)
      rejected → inbox     (restore)
    """
    import uuid as _uuid
    from sqlalchemy import select, update
    from app.models.project_score import MaterialProjectScore
    from app.models.channel_adaptation import ChannelAdaptation

    tid = _uuid.UUID(tenant_id)
    pid = _uuid.UUID(project_id)
    sid = _uuid.UUID(score_id)

    new_status = data.get("status")
    if new_status not in ("inbox", "in_progress", "rejected"):
        raise HTTPException(status_code=400, detail="Invalid status. Use: inbox, in_progress, rejected")

    score = (await db.execute(
        select(MaterialProjectScore).where(
            MaterialProjectScore.id == sid,
            MaterialProjectScore.project_id == pid,
            MaterialProjectScore.tenant_id == tid,
        )
    )).scalar_one_or_none()

    if not score:
        raise HTTPException(status_code=404, detail="Score not found")

    old_status = score.editorial_status
    score.editorial_status = new_status

    # On rejection: mark all adaptations as rejected
    if new_status == "rejected":
        await db.execute(
            update(ChannelAdaptation)
            .where(ChannelAdaptation.material_id == score.material_id)
            .values(status="rejected")
        )

    await db.commit()

    # On inbox → in_progress: trigger adaptation generation
    if old_status == "inbox" and new_status == "in_progress":
        from workers.ai_tasks import adapt_material_for_channels
        from app.models.channel import Channel

        # Find project channels
        channels = (await db.execute(
            select(Channel.id).where(
                Channel.project_id == pid,
                Channel.is_active == True,
            )
        )).scalars().all()

        if channels:
            adapt_material_for_channels.delay(
                str(score.material_id), str(pid), str(tid)
            )

    return {
        "id": str(score.id),
        "editorial_status": score.editorial_status,
        "previous_status": old_status,
    }


@router.get("/{project_id}/categories")
async def list_project_categories(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    """Return distinct categories for materials recommended to this project."""
    import uuid as _uuid
    from sqlalchemy import select, func
    from app.models.project_score import MaterialProjectScore
    from app.models.material import RawMaterial

    tid = _uuid.UUID(tenant_id)
    pid = _uuid.UUID(project_id)

    cat_col = RawMaterial.metadata_["ai_classification"]["category"].astext

    query = (
        select(cat_col, func.count().label("cnt"))
        .join(MaterialProjectScore, MaterialProjectScore.material_id == RawMaterial.id)
        .where(
            MaterialProjectScore.project_id == pid,
            MaterialProjectScore.tenant_id == tid,
            MaterialProjectScore.is_recommended == True,
            cat_col.isnot(None),
        )
        .group_by(cat_col)
        .order_by(func.count().desc())
    )

    rows = (await db.execute(query)).all()
    return [{"category": r[0], "count": r[1]} for r in rows]


@router.post("/{project_id}/recommendations/{score_id}/publish-batch")
async def batch_publish_adaptations(
    project_id: str,
    score_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    """Publish selected adaptations and move material to 'published' stage.

    Body: { "adaptation_ids": ["uuid1", "uuid2", ...] }

    This is the main publish action:
    1. Approves selected adaptations and creates PublishJobs
    2. Moves the MaterialProjectScore to editorial_status='published'
    3. Queues Celery tasks for actual sending
    """
    import uuid as _uuid
    from sqlalchemy import select, update
    from app.models.project_score import MaterialProjectScore
    from app.models.channel_adaptation import ChannelAdaptation
    from app.models.channel import Channel
    from app.models.publish_job import PublishJob

    tid = _uuid.UUID(tenant_id)
    pid = _uuid.UUID(project_id)
    sid = _uuid.UUID(score_id)

    adaptation_ids = data.get("adaptation_ids", [])
    if not adaptation_ids:
        raise HTTPException(status_code=400, detail="No adaptation_ids provided")

    # Verify score exists
    score = (await db.execute(
        select(MaterialProjectScore).where(
            MaterialProjectScore.id == sid,
            MaterialProjectScore.project_id == pid,
            MaterialProjectScore.tenant_id == tid,
        )
    )).scalar_one_or_none()
    if not score:
        raise HTTPException(status_code=404, detail="Score not found")

    # Process each adaptation
    publish_job_ids = []
    published_details = []
    for aid_str in adaptation_ids:
        aid = _uuid.UUID(aid_str)
        adaptation = await db.get(ChannelAdaptation, aid)
        if not adaptation or str(adaptation.tenant_id) != tenant_id:
            continue

        # Mark as approved (triggers publish flow)
        adaptation.status = "approved"

        # Get channel for publish config
        channel = await db.get(Channel, adaptation.channel_id)
        config = (channel.config or {}) if channel else {}

        if config.get("bot_token") and config.get("chat_id"):
            idempotency_key = f"{adaptation.id}:{adaptation.channel_id}:{adaptation.content_format}"
            existing = (await db.execute(
                select(PublishJob).where(PublishJob.idempotency_key == idempotency_key)
            )).scalar_one_or_none()

            if not existing:
                job = PublishJob(
                    content_id=adaptation.id,
                    channel_id=adaptation.channel_id,
                    tenant_id=tid,
                    status="queued",
                    idempotency_key=idempotency_key,
                )
                db.add(job)
                await db.flush()
                publish_job_ids.append(str(job.id))

        published_details.append({
            "id": str(adaptation.id),
            "language": adaptation.language,
            "content_format": adaptation.content_format,
            "channel_name": channel.name if channel else "—",
        })

    # Move material to published
    score.editorial_status = "published"
    await db.commit()

    # Queue Celery tasks after commit
    if publish_job_ids:
        from workers.publish_tasks import publish_to_telegram
        for job_id in publish_job_ids:
            publish_to_telegram.delay(job_id)

    return {
        "id": str(score.id),
        "editorial_status": "published",
        "published_count": len(publish_job_ids),
        "details": published_details,
    }


@router.post("/{project_id}/materials/{material_id}/generate-cover", status_code=202)
async def generate_material_cover(
    project_id: str,
    material_id: str,
    language: str = Query("ru", description="Language for text overlay"),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    """Generate an AI cover image for a material.

    Uses Gemini to create an optimal prompt, then GPT Image-2 to generate
    a photorealistic 16:9 image matching the news topic.
    """
    import uuid as _uuid
    from sqlalchemy import select
    from app.models.project_score import MaterialProjectScore

    tid = _uuid.UUID(tenant_id)

    # Verify material exists and belongs to this project
    score = (await db.execute(
        select(MaterialProjectScore).where(
            MaterialProjectScore.project_id == _uuid.UUID(project_id),
            MaterialProjectScore.material_id == _uuid.UUID(material_id),
            MaterialProjectScore.tenant_id == tid,
        )
    )).scalar_one_or_none()

    if not score:
        raise HTTPException(status_code=404, detail="Материал не найден в проекте")

    # Launch Celery task
    from workers.ai_tasks import generate_cover_image

    task = generate_cover_image.delay(
        material_id=material_id,
        tenant_id=tenant_id,
        language=language,
    )

    return {
        "status": "generating",
        "task_id": task.id,
        "material_id": material_id,
    }


@router.post("/{project_id}/adaptations/{adaptation_id}/generate-cover", status_code=202)
async def generate_adaptation_cover(
    project_id: str,
    adaptation_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    """Generate an AI cover image for a specific channel adaptation.

    Creates a cover with text overlay in the adaptation's language,
    matching the adaptation's headline and content.
    """
    import uuid as _uuid
    from sqlalchemy import select
    from app.models.channel_adaptation import ChannelAdaptation

    tid = _uuid.UUID(tenant_id)

    adaptation = (await db.execute(
        select(ChannelAdaptation).where(
            ChannelAdaptation.id == _uuid.UUID(adaptation_id),
            ChannelAdaptation.tenant_id == tid,
        )
    )).scalar_one_or_none()

    if not adaptation:
        raise HTTPException(status_code=404, detail="Адаптация не найдена")

    # Mark as generating
    adaptation.cover_status = "generating"
    await db.commit()

    # Launch Celery task
    from workers.ai_tasks import generate_adaptation_cover as gen_task

    task = gen_task.delay(
        adaptation_id=adaptation_id,
        tenant_id=tenant_id,
    )

    return {
        "status": "generating",
        "task_id": task.id,
        "adaptation_id": adaptation_id,
        "language": adaptation.language,
    }
