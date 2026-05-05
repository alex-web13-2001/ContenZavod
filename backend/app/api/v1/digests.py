"""Video Digest API — create, manage, and generate AI news digest videos.

Endpoints:
    GET    /digests                      — list digests for project
    POST   /digests                      — create a new digest
    GET    /digests/{id}                 — get digest details
    POST   /digests/{id}/generate-script — generate AI script from materials
    PATCH  /digests/{id}/script          — manually edit script
    POST   /digests/{id}/render          — start video generation via ReVid
    GET    /digests/{id}/status          — poll render status
    DELETE /digests/{id}                 — delete a digest
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db, get_tenant_id
from app.models.video_digest import VideoDigest
from app.schemas.video_digest import (
    DigestCreate,
    DigestGenerateRequest,
    DigestListResponse,
    DigestListItem,
    DigestResponse,
    DigestScriptUpdate,
    DigestStatusResponse,
)

router = APIRouter(prefix="/digests", tags=["digests"])


# ── LIST ─────────────────────────────────────────────

@router.get("", response_model=DigestListResponse)
async def list_digests(
    project_id: uuid.UUID = Query(...),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """List all video digests for a project."""
    base_q = select(VideoDigest).where(
        VideoDigest.tenant_id == tenant_id,
        VideoDigest.project_id == project_id,
    )

    # Count
    count_q = select(func.count()).select_from(base_q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Fetch
    items_q = base_q.order_by(desc(VideoDigest.created_at)).offset(offset).limit(limit)
    result = await db.execute(items_q)
    digests = result.scalars().all()

    return DigestListResponse(
        items=[DigestListItem.model_validate(d) for d in digests],
        total=total,
    )


# ── CREATE ───────────────────────────────────────────

@router.post("", response_model=DigestResponse, status_code=status.HTTP_201_CREATED)
async def create_digest(
    body: DigestCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Create a new video digest (select materials, set title)."""
    digest = VideoDigest(
        tenant_id=tenant_id,
        project_id=body.project_id,
        title=body.title,
        language=body.language,
        material_ids=[str(m) for m in body.material_ids],
        revid_status="draft",
        config={},
    )
    db.add(digest)
    await db.commit()
    await db.refresh(digest)
    return DigestResponse.model_validate(digest)


# ── GET DETAIL ───────────────────────────────────────

@router.get("/{digest_id}", response_model=DigestResponse)
async def get_digest(
    digest_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Get full details of a digest.

    If the digest is currently rendering and has a ReVid PID,
    we check ReVid status and update the DB if the video is ready.
    """
    digest = await _get_digest_or_404(db, digest_id, tenant_id)

    # Auto-check ReVid status when rendering
    if digest.revid_status == "rendering" and digest.revid_pid:
        try:
            from integrations.revid import RevidClient
            from app.core.config import settings
            client = RevidClient(api_key=settings.revid_api_key)
            revid_data = client.check_status(digest.revid_pid)

            revid_status = revid_data.get("status", "")
            if revid_status == "ready" and revid_data.get("videoUrl"):
                digest.revid_status = "ready"
                digest.video_url = revid_data["videoUrl"]
                digest.credits_used = revid_data.get("creditsConsumed")
                await db.commit()
                await db.refresh(digest)
            elif revid_status == "failed":
                digest.revid_status = "failed"
                digest.error_message = revid_data.get("error", "ReVid render failed")
                await db.commit()
                await db.refresh(digest)
        except Exception:
            pass  # Don't break the GET if ReVid check fails

    return DigestResponse.model_validate(digest)


# ── GENERATE SCRIPT ──────────────────────────────────

@router.post("/{digest_id}/generate-script", response_model=DigestResponse)
async def generate_script(
    digest_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Trigger AI script generation from the selected materials.

    Sets status to 'script_generating' and queues a Celery task.
    """
    digest = await _get_digest_or_404(db, digest_id, tenant_id)

    if digest.revid_status not in ("draft", "script_ready", "failed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot generate script in status '{digest.revid_status}'",
        )

    digest.revid_status = "script_generating"
    await db.commit()
    await db.refresh(digest)

    # Queue async generation
    from workers.digest_tasks import generate_digest_script_task
    generate_digest_script_task.delay(str(digest_id))

    return DigestResponse.model_validate(digest)


# ── EDIT SCRIPT ──────────────────────────────────────

@router.patch("/{digest_id}/script", response_model=DigestResponse)
async def update_script(
    digest_id: uuid.UUID,
    body: DigestScriptUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Manually edit the digest script."""
    digest = await _get_digest_or_404(db, digest_id, tenant_id)

    if digest.revid_status == "rendering":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot edit script while rendering",
        )

    digest.script_text = body.script_text
    digest.revid_status = "script_ready"
    digest.error_message = None
    await db.commit()
    await db.refresh(digest)

    return DigestResponse.model_validate(digest)


# ── RENDER VIDEO ─────────────────────────────────────

@router.post("/{digest_id}/render", response_model=DigestResponse)
async def render_video(
    digest_id: uuid.UUID,
    body: DigestGenerateRequest | None = None,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Submit the script to ReVid API for video generation.

    Optionally override avatar, voice, aspect ratio, or quality.
    """
    digest = await _get_digest_or_404(db, digest_id, tenant_id)

    if not digest.script_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No script text. Generate or write a script first.",
        )

    if digest.revid_status == "rendering":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video is already being rendered",
        )

    # Apply overrides to config
    if body:
        config = digest.config or {}
        if body.render_config:
            # New unified config from frontend — store the whole thing
            config["render_config"] = body.render_config
        # Legacy field overrides (backward compat)
        if body.avatar_url:
            config["avatar_url"] = body.avatar_url
        if body.voice_id:
            config["voice_id"] = body.voice_id
        if body.aspect_ratio:
            config["aspect_ratio"] = body.aspect_ratio
        if body.quality:
            config["quality"] = body.quality
        digest.config = config

    digest.revid_status = "rendering"
    digest.error_message = None
    await db.commit()
    await db.refresh(digest)

    # Queue rendering
    from workers.digest_tasks import render_digest_video_task
    render_digest_video_task.delay(str(digest_id))

    return DigestResponse.model_validate(digest)


# ── STATUS ───────────────────────────────────────────

@router.get("/{digest_id}/status", response_model=DigestStatusResponse)
async def get_status(
    digest_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Poll the current status of video generation."""
    digest = await _get_digest_or_404(db, digest_id, tenant_id)
    return DigestStatusResponse(
        id=digest.id,
        revid_status=digest.revid_status,
        revid_pid=digest.revid_pid,
        video_url=digest.video_url,
        error_message=digest.error_message,
    )


# ── DELETE ───────────────────────────────────────────

@router.delete("/{digest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_digest(
    digest_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Delete a video digest."""
    digest = await _get_digest_or_404(db, digest_id, tenant_id)
    await db.delete(digest)
    await db.commit()


# ── Helpers ──────────────────────────────────────────

async def _get_digest_or_404(
    db: AsyncSession,
    digest_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> VideoDigest:
    """Fetch a digest by ID, scoped to tenant, or raise 404."""
    stmt = select(VideoDigest).where(
        VideoDigest.id == digest_id,
        VideoDigest.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    digest = result.scalar_one_or_none()
    if not digest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Digest not found",
        )
    return digest
