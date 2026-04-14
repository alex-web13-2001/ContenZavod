"""Scraping Celery tasks — orchestrate source parsing.

Task flow:
    scrape_source(source_id, tenant_id) → parse RSS → deduplicate → insert RawMaterials
    scrape_all_active_sources() → fan-out to scrape_source for each active source
"""

import asyncio
import uuid
from datetime import datetime, timezone

import structlog
from celery import shared_task
from sqlalchemy import select, text

from app.database import get_sync_session
from app.models.material import RawMaterial
from app.models.source import Source
from scraper.rss_parser import discover_feed_url, parse_rss_feed

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

        new_count = 0
        for mat_data in materials:
            if mat_data["content_hash"] in existing_hashes:
                continue

            material = RawMaterial(
                source_id=source.id,
                tenant_id=uuid.UUID(tenant_id),
                original_url=mat_data["original_url"],
                title=mat_data["title"],
                content_text=mat_data["content_text"],
                content_html=mat_data.get("content_html"),
                content_hash=mat_data["content_hash"],
                metadata_=mat_data.get("metadata_", {}),
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

        log.info("scrape.done", new=new_count, total=len(materials))
        return {"status": "ok", "new": new_count, "total": len(materials)}


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
