"""Scraping Celery tasks — orchestrate source parsing.

Task flow:
    scrape_source(source_id, tenant_id) → parse RSS → deduplicate → insert RawMaterials
    scrape_all_active_sources() → fan-out to scrape_source for each active source
"""

import asyncio
import hashlib
import io
import uuid
from datetime import datetime, timezone

import httpx
import structlog
from celery import shared_task
from sqlalchemy import func, select, text

from app.database import get_sync_session
from app.models.material import RawMaterial
from app.models.source import Source
from scraper.rss_parser import discover_feed_url, parse_rss_feed
from workers.image_dedup import normalize_image_url

logger = structlog.get_logger()

# Source-image rules
SOURCE_IMAGE_MIN_BYTES = 5_000          # < 5 KB → almost certainly an icon
SOURCE_IMAGE_MIN_DIMENSION = 400        # both width and height must clear this
SOURCE_IMAGE_MAX_BYTES = 8_000_000      # cap download size to 8 MB
SOURCE_IMAGE_TIMEOUT = 15.0
SOURCE_IMAGE_BAD_URL_TOKENS = (
    "logo", "default", "placeholder", "share", "social-card", "og-default",
)
# A genuine article hero photo is used exactly once. If a source-image's
# normalized URL is already attached to another material from the same source,
# it's a shared/section/wire photo — we must NOT reuse it as a cover (that's how
# one photo ended up on several unrelated posts). Enforced via
# _load_used_cover_urls + normalize_image_url (URL key survives CDN re-encoding).


def _fetch_source_image(
    url: str, used_urls: set[str]
) -> tuple[bytes, str, str] | None:
    """Download a candidate image URL and validate.

    Returns (data, content_type, sha256) on success, None on rejection.
    Rejection reasons: normalized URL already used as a cover for this source
    (the primary dedup key — survives CDN/resize byte changes), HTTP failure,
    too small, banned URL tokens, or dimension-check fail.
    """
    lower = url.lower()
    if any(tok in lower for tok in SOURCE_IMAGE_BAD_URL_TOKENS):
        return None

    # Primary dedup BEFORE downloading: if this image's normalized URL was
    # already used as a cover, skip it (saves the HTTP fetch). SHA-256 can't
    # catch these because the outlet re-encodes the bytes on every request.
    if normalize_image_url(url) in used_urls:
        logger.info("source_image.url_already_used_skip", url=url)
        return None

    try:
        with httpx.Client(timeout=SOURCE_IMAGE_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(url, headers={
                "User-Agent": "ContenZavod/1.0 (news aggregator; +https://contenzavod.io)",
            })
            resp.raise_for_status()
    except Exception as e:
        logger.warning("source_image.fetch_failed", url=url, error=str(e))
        return None

    data = resp.content
    if not data or len(data) < SOURCE_IMAGE_MIN_BYTES or len(data) > SOURCE_IMAGE_MAX_BYTES:
        return None

    content_type = resp.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if not content_type.startswith("image/"):
        return None

    sha = hashlib.sha256(data).hexdigest()

    # Dimension check via Pillow if available; if not installed, skip the
    # check (size-in-bytes filter above already removes most icons).
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(data))
        if min(img.size) < SOURCE_IMAGE_MIN_DIMENSION:
            return None
    except ImportError:
        pass
    except Exception as e:
        logger.debug("source_image.pillow_warning", error=str(e))
        # If Pillow can't decode, don't reject — let downstream handle it

    return data, content_type, sha


def _store_source_image(
    data: bytes, content_type: str, sha256_hex: str,
) -> str:
    """Upload image to MinIO under source-covers/{sha}.{ext}. Returns API path."""
    from app.services.storage import upload_bytes

    ext = ".jpg"
    if "png" in content_type:
        ext = ".png"
    elif "webp" in content_type:
        ext = ".webp"
    elif "gif" in content_type:
        ext = ".gif"

    object_name = f"source-covers/{sha256_hex}{ext}"
    # Idempotent: if the same content was already uploaded, MinIO accepts the
    # PUT and overwrites with identical bytes — cheap, no need to pre-check.
    upload_bytes(data, object_name, content_type)
    return f"/api/v1/files/{object_name}"


def _load_used_cover_urls(session, source_id: uuid.UUID) -> set[str]:
    """Normalized source URLs of all cover images already used in this source.

    Any image used once is off-limits for new covers: a real per-article photo
    never legitimately reappears, so a repeat URL is a shared/section/wire image.
    Keyed on the NORMALIZED source URL (not SHA) so it survives CDN re-encoding,
    which is what let one photo land on several unrelated posts. Guarantees an
    image is used on at most one post per source.
    """
    rows = session.execute(
        text(
            """
            SELECT DISTINCT metadata->'cover_image'->>'source_url' AS src
              FROM raw_materials
             WHERE source_id = :sid
               AND metadata->'cover_image'->>'source_url' IS NOT NULL
            """
        ),
        {"sid": str(source_id)},
    ).all()
    return {normalize_image_url(r[0]) for r in rows if r[0]}


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


@shared_task(bind=True, name="workers.scrape_tasks.scrape_source", max_retries=3)
def scrape_source(self, source_id: str, tenant_id: str):
    """Scrape a single source by ID."""
    log = logger.bind(source_id=source_id, tenant_id=tenant_id)
    log.info("scrape.start")

    with get_sync_session() as session:
        source = session.get(Source, uuid.UUID(source_id))
        if not source:
            log.error("scrape.source_not_found")
            return {"status": "error", "reason": "source_not_found"}

        if str(source.tenant_id) != tenant_id:
            log.error("scrape.tenant_mismatch")
            return {"status": "error", "reason": "tenant_mismatch"}

        feed_url = source.url
        source_type = source.source_type

        # Auto-discover RSS feed if source type is 'website'
        if source_type == "website":
            discovered = _run_async(discover_feed_url(feed_url))
            if discovered:
                feed_url = discovered
                log.info("scrape.discovered_feed", feed_url=feed_url)
            else:
                log.warning("scrape.no_feed_found", url=feed_url)
                source.error_count += 1
                session.commit()
                return {"status": "error", "reason": "no_feed_found"}

        # Parse the feed
        try:
            materials = _run_async(parse_rss_feed(feed_url))
        except Exception as e:
            log.error("scrape.parse_error", error=str(e))
            source.error_count += 1
            session.commit()
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

        # Deduplicate: get existing hashes for this tenant
        existing_hashes = set(
            row[0] for row in session.execute(
                select(RawMaterial.content_hash).where(
                    RawMaterial.tenant_id == uuid.UUID(tenant_id)
                )
            ).all()
        )

        # Normalized source URLs of all cover images already used by this source.
        # An image used once must never become another post's cover (the "same
        # photo on many news items" bug). Keyed on normalized URL, not SHA, so it
        # survives CDN re-encoding. Seeded from the DB, then updated in-loop so
        # repeats within this same scrape batch are blocked too.
        used_cover_urls = _load_used_cover_urls(session, source.id)

        new_count = 0
        new_image_count = 0
        for mat_data in materials:
            if mat_data["content_hash"] in existing_hashes:
                continue

            meta = mat_data.get("metadata_", {}) or {}

            # Try to attach a source image (one HTTP per new material, capped).
            # _fetch_source_image rejects any URL already in used_cover_urls,
            # so each distinct image lands on at most one material.
            image_url = mat_data.get("image_url")
            if image_url:
                fetched = _fetch_source_image(image_url, used_cover_urls)
                if fetched:
                    img_bytes, ct, sha = fetched
                    try:
                        stored_path = _store_source_image(img_bytes, ct, sha)
                        meta["cover_image"] = {
                            "url": stored_path,           # served by /api/v1/files/...
                            "source_url": image_url,      # original where we got it
                            "sha256": sha,
                            "size_bytes": len(img_bytes),
                            "origin": "source_feed",
                        }
                        meta["cover_status"] = "ready"
                        new_image_count += 1
                        # block reuse later in this batch (normalized URL key)
                        used_cover_urls.add(normalize_image_url(image_url))
                    except Exception as e:
                        log.warning(
                            "source_image.upload_failed",
                            url=image_url, error=str(e),
                        )

            material = RawMaterial(
                source_id=source.id,
                tenant_id=uuid.UUID(tenant_id),
                original_url=mat_data["original_url"],
                title=mat_data["title"],
                content_text=mat_data["content_text"],
                content_html=mat_data.get("content_html"),
                content_hash=mat_data["content_hash"],
                metadata_=meta,
                word_count=mat_data.get("word_count"),
                published_at=mat_data.get("published_at"),
                scraped_at=datetime.now(timezone.utc),
                status="new",
            )
            session.add(material)
            existing_hashes.add(mat_data["content_hash"])
            new_count += 1

        # Update source
        source.last_scraped_at = datetime.now(timezone.utc)
        source.last_success_at = datetime.now(timezone.utc)
        source.error_count = 0
        session.commit()

        log.info(
            "scrape.done",
            new=new_count, total=len(materials), with_images=new_image_count,
        )
        return {
            "status": "ok",
            "new": new_count,
            "total": len(materials),
            "with_images": new_image_count,
        }


@shared_task(name="workers.scrape_tasks.scrape_all_active_sources")
def scrape_all_active_sources():
    """Fan-out: queue scrape_source for every active source."""
    logger.info("scrape.fan_out.start")

    with get_sync_session() as session:
        sources = session.execute(
            select(Source.id, Source.tenant_id).where(Source.is_active.is_(True))
        ).all()

    for source_id, tenant_id in sources:
        scrape_source.delay(str(source_id), str(tenant_id))

    logger.info("scrape.fan_out.done", count=len(sources))
    return {"queued": len(sources)}
