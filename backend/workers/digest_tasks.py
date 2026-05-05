"""Celery tasks for Video Digest generation.

Handles:
- AI script generation from selected materials
- ReVid API render submission
- Status polling with exponential backoff
"""

import uuid

import structlog
from celery import shared_task
from sqlalchemy import select

from app.config import get_settings
from app.database import get_sync_session
from app.models.material import RawMaterial
from app.models.video_digest import VideoDigest
from integrations.revid import RevidClient

log = structlog.get_logger()


@shared_task(name="digest.generate_script", bind=True, max_retries=2)
def generate_digest_script_task(self, digest_id: str) -> dict:
    """Generate the AI script for a digest.

    Loads the selected materials, calls AI to produce a script,
    and stores it in the digest record.
    """
    log.info("digest.script.task_start", digest_id=digest_id)

    with get_sync_session() as session:
        digest = session.get(VideoDigest, uuid.UUID(digest_id))
        if not digest:
            log.error("digest.script.not_found", digest_id=digest_id)
            return {"status": "error", "error": "digest not found"}

        # Load source materials
        mat_uuids = [uuid.UUID(m) if isinstance(m, str) else m for m in digest.material_ids]
        stmt = select(RawMaterial).where(RawMaterial.id.in_(mat_uuids))
        materials = session.execute(stmt).scalars().all()

        if not materials:
            digest.revid_status = "failed"
            digest.error_message = "No materials found for digest"
            session.commit()
            return {"status": "error", "error": "no materials"}

        # Generate script via AI
        from ai.digest_script import generate_digest_script

        script = generate_digest_script(
            materials=list(materials),
            title=digest.title,
        )

        if not script:
            digest.revid_status = "failed"
            digest.error_message = "AI script generation returned empty result"
            session.commit()
            return {"status": "error", "error": "empty script"}

        digest.script_text = script
        digest.revid_status = "script_ready"
        session.commit()

        log.info(
            "digest.script.done",
            digest_id=digest_id,
            word_count=len(script.split()),
        )

        return {"status": "ok", "word_count": len(script.split())}


@shared_task(name="digest.render_video", bind=True, max_retries=2)
def render_digest_video_task(self, digest_id: str) -> dict:
    """Submit the digest script to ReVid API for video rendering.

    Requires the digest to have a script_text and be in 'script_ready' status.
    """
    settings = get_settings()
    if not settings.revid_api_key:
        log.error("digest.render.no_api_key")
        return {"status": "error", "error": "REVID_API_KEY not configured"}

    log.info("digest.render.task_start", digest_id=digest_id)

    with get_sync_session() as session:
        digest = session.get(VideoDigest, uuid.UUID(digest_id))
        if not digest:
            return {"status": "error", "error": "digest not found"}

        if not digest.script_text:
            digest.revid_status = "failed"
            digest.error_message = "No script text to render"
            session.commit()
            return {"status": "error", "error": "no script"}

        config = digest.config or {}
        rc = config.get("render_config")
        
        # Legacy fallback: build render_config from old individual fields
        if not rc:
            rc = {}
            if config.get("provided_media"):
                rc["providedMedia"] = config["provided_media"]
            if config.get("use_only_provided"):
                rc["mediaType"] = "provided"
            if "cutout_avatar" in config:
                rc["removeBackground"] = config["cutout_avatar"]
            if config.get("avatar_image_model"):
                rc["avatarImageModel"] = config["avatar_image_model"]
            if config.get("media_image_model"):
                rc["mediaImageModel"] = config["media_image_model"]
            if config.get("video_model"):
                rc["videoModel"] = config["video_model"]
            if config.get("b_roll_type"):
                rc["bRollType"] = config["b_roll_type"]
        
        # Avatar URL: from render_config > legacy config > env default
        avatar_url = rc.get("avatarUrl") or config.get("avatar_url") or settings.revid_avatar_url
        voice_id = rc.get("voiceId") or config.get("voice_id") or settings.revid_voice_id

        if not avatar_url:
            digest.revid_status = "failed"
            digest.error_message = "Avatar URL not configured"
            session.commit()
            return {"status": "error", "error": "no avatar_url"}

        client = RevidClient(api_key=settings.revid_api_key)

        try:
            result = client.render_avatar_video(
                script=digest.script_text,
                avatar_url=avatar_url,
                voice_id=voice_id,
                render_config=rc,
            )
        except Exception as e:
            digest.revid_status = "failed"
            digest.error_message = f"ReVid API error: {str(e)}"
            session.commit()
            log.error("digest.render.api_error", error=str(e))
            return {"status": "error", "error": str(e)}

        if result.get("success") != 1:
            error_msg = result.get("error", "Unknown ReVid error")
            digest.revid_status = "failed"
            digest.error_message = error_msg
            session.commit()
            return {"status": "error", "error": error_msg}

        pid = result["pid"]
        digest.revid_pid = pid
        digest.revid_status = "rendering"
        session.commit()

        log.info("digest.render.submitted", digest_id=digest_id, pid=pid)

        # Start polling
        poll_digest_status_task.apply_async(
            args=[digest_id],
            countdown=10,  # First poll in 10 seconds
        )

        return {"status": "ok", "pid": pid}


@shared_task(
    name="digest.poll_status",
    bind=True,
    max_retries=120,  # ~10 min with 5s intervals
    default_retry_delay=5,
)
def poll_digest_status_task(self, digest_id: str) -> dict:
    """Poll ReVid API for render status.

    Retries every 5-8 seconds until the video is ready or fails.
    """
    settings = get_settings()
    if not settings.revid_api_key:
        return {"status": "error", "error": "no api key"}

    with get_sync_session() as session:
        digest = session.get(VideoDigest, uuid.UUID(digest_id))
        if not digest or not digest.revid_pid:
            return {"status": "error", "error": "digest or pid not found"}

        if digest.revid_status in ("ready", "failed"):
            return {"status": digest.revid_status}

        client = RevidClient(api_key=settings.revid_api_key)

        try:
            result = client.check_status(digest.revid_pid)
        except Exception as e:
            log.warning("digest.poll.error", error=str(e))
            raise self.retry(countdown=8)

        status = result.get("status", "unknown")

        if status == "ready":
            digest.revid_status = "ready"
            digest.video_url = result.get("videoUrl")
            digest.thumbnail_url = result.get("thumbnailUrl")
            digest.duration_seconds = result.get("durationSeconds")
            session.commit()

            log.info(
                "digest.poll.ready",
                digest_id=digest_id,
                video_url=digest.video_url,
            )
            return {"status": "ready", "video_url": digest.video_url}

        elif status == "failed":
            error_msg = result.get("error", "Render failed")
            digest.revid_status = "failed"
            digest.error_message = error_msg
            session.commit()

            log.error("digest.poll.failed", digest_id=digest_id, error=error_msg)
            return {"status": "failed", "error": error_msg}

        else:
            # Still rendering — retry with backoff
            progress = result.get("progress", 0)
            retry_delay = 8 if progress and progress > 30 else 5

            log.debug(
                "digest.poll.rendering",
                digest_id=digest_id,
                progress=progress,
                retry_in=retry_delay,
            )
            raise self.retry(countdown=retry_delay)
