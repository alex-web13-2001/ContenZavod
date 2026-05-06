"""ReVid API client — video generation via revid.ai.

Handles the avatar-to-video workflow: submit render jobs,
poll for completion, and retrieve the final video URL.
"""

import httpx
import structlog

log = structlog.get_logger()

REVID_BASE = "https://www.revid.ai/api/public/v3"


class RevidClient:
    """Thin wrapper around the ReVid Public API v3."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "key": api_key,
            "Content-Type": "application/json",
        }

    # ── Render ──────────────────────────────────────────

    def render_avatar_video(
        self,
        script: str,
        avatar_url: str,
        voice_id: str,
        render_config: dict | None = None,
        webhook_url: str | None = None,
    ) -> dict:
        """Submit an avatar-to-video render job.

        render_config keys (camelCase, from frontend):
            avatarImageModel, removeBackground,
            voiceSpeed, voiceLanguage,
            mediaType, mediaDensity, mediaImageModel, videoModel, bRollType,
            placeAvatarInContext, captionsEnabled, captionsPreset, captionsPosition,
            musicEnabled, aspectRatio, disableAudio,
            providedMedia[{url, title, type}]

        Returns:
            {"success": 1, "pid": "p_xxx", ...} on success.
            {"success": 0, "error": "..."} on failure.
        """
        rc = render_config or {}

        provided_media = rc.get("providedMedia") or []

        # Normalize media type — map legacy/invalid values to valid ReVid API types
        MEDIA_TYPE_MAP = {
            "provided": "custom",
            "stock-image": "moving-image",
        }
        VALID_MEDIA_TYPES = {"stock-video", "video", "moving-image", "ai-image", "ai-video", "custom"}
        raw_media_type = rc.get("mediaType", "stock-video")
        media_type = MEDIA_TYPE_MAP.get(raw_media_type, raw_media_type)
        if media_type not in VALID_MEDIA_TYPES:
            media_type = "stock-video"

        payload: dict = {
            "workflow": "avatar-to-video",
            "source": {
                "text": script,
            },
            "media": {
                "type": media_type,
                "density": rc.get("mediaDensity", "medium"),
                "imageModel": rc.get("mediaImageModel", "good"),
                "videoModel": rc.get("videoModel", "base"),
                "bRollType": rc.get("bRollType", "fullscreen"),
                "placeAvatarInContext": rc.get("placeAvatarInContext", True),
            },
            "voice": {
                "enabled": True,
                "voiceId": voice_id,
                "speed": rc.get("voiceSpeed", 1),
                "useLegacyModel": False,
                "language": rc.get("voiceLanguage", "ru"),
            },
            "captions": {
                "enabled": rc.get("captionsEnabled", True),
                "preset": rc.get("captionsPreset", "Hormozi"),
                "position": rc.get("captionsPosition", "bottom"),
            },
            "music": {
                "enabled": rc.get("musicEnabled", False),
            },
            "avatar": {
                "enabled": True,
                "url": avatar_url,
                "mimeType": "image/png",
                "imageModel": rc.get("avatarImageModel", "good"),
                "removeBackground": rc.get("removeBackground", True),
            },
            "options": {
                "disableAudio": rc.get("disableAudio", True),
            },
            "metadata": None,
            "aspectRatio": rc.get("aspectRatio", "9 / 16"),
        }

        # Add user-provided media (custom backgrounds with titles for scene matching)
        if provided_media:
            payload["media"]["provided"] = provided_media

        if webhook_url:
            payload["webhookUrl"] = webhook_url

        log.info(
            "revid.render.submit",
            workflow="avatar-to-video",
            script_len=len(script),
            aspect_ratio=payload.get("aspectRatio"),
            media_type=payload["media"]["type"],
            provided_count=len(provided_media),
        )
        log.debug("revid.render.payload", payload=payload)

        resp = httpx.post(
            f"{REVID_BASE}/render",
            json=payload,
            headers=self.headers,
            timeout=30.0,
            follow_redirects=True,
        )

        data = resp.json()

        if resp.status_code >= 400:
            error_detail = data.get("error") or data.get("message") or resp.text
            log.error(
                "revid.render.http_error",
                status_code=resp.status_code,
                error=error_detail,
                response_body=data,
            )
            raise ValueError(f"ReVid {resp.status_code}: {error_detail}")

        if data.get("success") != 1:
            log.error("revid.render.failed", error=data.get("error"))
        else:
            log.info("revid.render.ok", pid=data.get("pid"))

        return data

    # ── Status ─────────────────────────────────────────

    def check_status(self, pid: str) -> dict:
        """Poll the status of a render job.

        Returns:
            {"status": "ready", "videoUrl": "https://...", ...}
            {"status": "rendering", "progress": 42, ...}
            {"status": "failed", "error": "..."}
        """
        resp = httpx.get(
            f"{REVID_BASE}/status",
            params={"pid": pid},
            headers=self.headers,
            timeout=15.0,
            follow_redirects=True,
        )
        resp.raise_for_status()
        data = resp.json()

        log.debug(
            "revid.status.polled",
            pid=pid,
            status=data.get("status"),
            progress=data.get("progress"),
        )
        return data

    # ── Credits ────────────────────────────────────────

    def estimate_credits(self, payload: dict) -> int | None:
        """Estimate credit cost without spending.

        Pass the same body you'd send to /render.
        """
        try:
            resp = httpx.post(
                f"{REVID_BASE}/calculate-credits",
                json=payload,
                headers=self.headers,
                timeout=10.0,
                follow_redirects=True,
            )
            resp.raise_for_status()
            return resp.json().get("credits")
        except Exception as e:
            log.warning("revid.credits.estimate_failed", error=str(e))
            return None
