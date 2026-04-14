"""RSS feed parser — fetches and parses RSS/Atom feeds into RawMaterial records.

Supports:
- Standard RSS 2.0 and Atom feeds
- Auto-detection of feed URL from site homepage
- Content deduplication via SHA-256 hash
- Full-text extraction from article pages via httpx + BeautifulSoup
"""

import hashlib
import re
from datetime import datetime, timezone
from typing import Any

import feedparser
import httpx
import structlog
from bs4 import BeautifulSoup

logger = structlog.get_logger()


def _clean_html(html: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def _content_hash(text: str) -> str:
    """SHA-256 hash of content for dedup."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _word_count(text: str) -> int:
    return len(text.split())


def _parse_date(entry: dict[str, Any]) -> datetime | None:
    """Extract publication date from feed entry."""
    for field in ("published_parsed", "updated_parsed"):
        ts = entry.get(field)
        if ts:
            try:
                from time import mktime
                return datetime.fromtimestamp(mktime(ts), tz=timezone.utc)
            except Exception:
                continue
    return None


async def fetch_full_article(url: str, timeout: int = 15) -> str | None:
    """Fetch the full article text from a URL."""
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers={
                "User-Agent": "ContenZavod/1.0 (news aggregator; +https://contenzavod.io)",
            })
            resp.raise_for_status()
    except Exception as e:
        logger.warning("scraper.fetch_failed", url=url, error=str(e))
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Try common article selectors
    for selector in [
        "article",
        '[class*="article-body"]',
        '[class*="entry-content"]',
        '[class*="post-content"]',
        '[class*="story-body"]',
        "main",
    ]:
        el = soup.select_one(selector)
        if el:
            # Remove scripts, styles, nav, ads
            for junk in el.select("script, style, nav, aside, [class*='ad-'], [class*='sidebar']"):
                junk.decompose()
            text = el.get_text(separator=" ", strip=True)
            if len(text) > 200:
                return text

    return None


async def parse_rss_feed(
    feed_url: str,
    fetch_full_text: bool = True,
    max_items: int = 50,
) -> list[dict[str, Any]]:
    """Parse an RSS feed and return a list of material dicts.

    Returns list of dicts ready to create RawMaterial records:
        title, original_url, content_text, content_html, content_hash,
        word_count, published_at, metadata_
    """
    logger.info("scraper.rss.start", url=feed_url)

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        resp = await client.get(feed_url, headers={
            "User-Agent": "ContenZavod/1.0 (news aggregator; +https://contenzavod.io)",
        })
        resp.raise_for_status()

    feed = feedparser.parse(resp.text)
    if feed.bozo and not feed.entries:
        logger.error("scraper.rss.parse_error", url=feed_url, error=str(feed.bozo_exception))
        return []

    logger.info("scraper.rss.entries", url=feed_url, count=len(feed.entries))
    results = []

    for entry in feed.entries[:max_items]:
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        if not title or not link:
            continue

        # Get content from feed (summary or content)
        raw_content = ""
        if entry.get("content"):
            raw_content = entry.content[0].get("value", "")
        elif entry.get("summary"):
            raw_content = entry.summary

        content_text = _clean_html(raw_content) if raw_content else ""

        # Optionally fetch full article
        if fetch_full_text and len(content_text) < 500:
            full = await fetch_full_article(link)
            if full and len(full) > len(content_text):
                content_text = full

        if not content_text:
            content_text = title  # fallback

        cHash = _content_hash(content_text)
        pub_date = _parse_date(entry)

        # Metadata
        meta: dict[str, Any] = {}
        if entry.get("author"):
            meta["author"] = entry.author
        if entry.get("tags"):
            meta["tags"] = [t.get("term", "") for t in entry.tags if t.get("term")]
        if feed.feed.get("title"):
            meta["feed_title"] = feed.feed.title

        results.append({
            "title": title[:500],
            "original_url": link,
            "content_text": content_text,
            "content_html": raw_content or None,
            "content_hash": cHash,
            "word_count": _word_count(content_text),
            "published_at": pub_date,
            "metadata_": meta,
        })

    logger.info("scraper.rss.done", url=feed_url, materials=len(results))
    return results


async def discover_feed_url(site_url: str) -> str | None:
    """Try to discover RSS feed URL from a website homepage."""
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(site_url, headers={
                "User-Agent": "ContenZavod/1.0",
            })
            resp.raise_for_status()
    except Exception:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    for link in soup.find_all("link", type=re.compile(r"(rss|atom)\+xml", re.I)):
        href = link.get("href")
        if href:
            if href.startswith("/"):
                from urllib.parse import urljoin
                href = urljoin(site_url, href)
            return href

    # Common paths
    for path in ["/feed/", "/rss/", "/feed", "/rss", "/atom.xml"]:
        try:
            async with httpx.AsyncClient(timeout=5, follow_redirects=True) as client:
                resp = await client.head(site_url.rstrip("/") + path)
                if resp.status_code == 200:
                    return site_url.rstrip("/") + path
        except Exception:
            continue

    return None
