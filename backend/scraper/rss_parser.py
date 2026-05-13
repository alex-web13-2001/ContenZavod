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


def _extract_image_from_entry(entry: dict[str, Any]) -> str | None:
    """Extract image URL from a feedparser entry.

    Checks (in order):
      1. media_content (Yahoo Media RSS — most reliable)
      2. media_thumbnail
      3. enclosures (standard RSS with type="image/*")
      4. <img> tag inside content/summary HTML
    Returns None if no usable image found.
    """
    # 1. media:content
    media = entry.get("media_content") or []
    for m in media:
        url = m.get("url", "")
        mtype = m.get("medium") or m.get("type") or ""
        if url and (mtype.startswith("image") or not mtype):
            return url

    # 2. media:thumbnail
    thumbs = entry.get("media_thumbnail") or []
    for t in thumbs:
        if t.get("url"):
            return t["url"]

    # 3. enclosures
    encs = entry.get("enclosures") or []
    for enc in encs:
        url = enc.get("href") or enc.get("url", "")
        if url and (enc.get("type", "").startswith("image") or url.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))):
            return url

    # 4. <img> in content/summary
    html_blob = ""
    if entry.get("content"):
        try:
            html_blob = entry.content[0].get("value", "")
        except Exception:
            pass
    if not html_blob:
        html_blob = entry.get("summary", "")
    if html_blob:
        m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html_blob, re.I)
        if m:
            return m.group(1)

    return None


async def fetch_article_meta(
    url: str,
    timeout: int = 15,
    want_text: bool = True,
    want_image: bool = True,
) -> dict[str, str | None]:
    """Fetch the article page; extract full text and/or og:image.

    Single HTTP request — both extractions from the same response.
    Returns dict with optional 'text' and 'image_url' keys (None on failure).
    """
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers={
                "User-Agent": "ContenZavod/1.0 (news aggregator; +https://contenzavod.io)",
            })
            resp.raise_for_status()
    except Exception as e:
        logger.warning("scraper.fetch_failed", url=url, error=str(e))
        return {"text": None, "image_url": None}

    soup = BeautifulSoup(resp.text, "html.parser")
    result: dict[str, str | None] = {"text": None, "image_url": None}

    # ── Text: try common article selectors ──
    if want_text:
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
                for junk in el.select("script, style, nav, aside, [class*='ad-'], [class*='sidebar']"):
                    junk.decompose()
                text = el.get_text(separator=" ", strip=True)
                if len(text) > 200:
                    result["text"] = text
                    break

    # ── Image: og:image / twitter:image ──
    if want_image:
        for prop in ["og:image", "og:image:url", "twitter:image", "twitter:image:src"]:
            tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
            if tag and tag.get("content"):
                result["image_url"] = tag["content"]
                break
        # Fallback: first significant <img> in article body
        if not result["image_url"]:
            for el_sel in ["article img", '[class*="article"] img', "main img"]:
                img = soup.select_one(el_sel)
                if img and img.get("src"):
                    src = img["src"]
                    if "logo" in src.lower() or "icon" in src.lower() or "placeholder" in src.lower():
                        continue
                    result["image_url"] = src
                    break

    return result


# Backwards-compat wrapper used in older code paths
async def fetch_full_article(url: str, timeout: int = 15) -> str | None:
    """Legacy alias — returns only the article text."""
    meta = await fetch_article_meta(url, timeout=timeout, want_text=True, want_image=False)
    return meta.get("text")


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

        # Try cheap image extraction from RSS entry first (no extra HTTP)
        image_url = _extract_image_from_entry(entry)

        # If we need text OR image, hit the article page once and grab both
        need_text = fetch_full_text and len(content_text) < 500
        need_image = not image_url
        if need_text or need_image:
            article = await fetch_article_meta(
                link, want_text=need_text, want_image=need_image,
            )
            if need_text and article.get("text") and len(article["text"]) > len(content_text):
                content_text = article["text"]
            if need_image and article.get("image_url"):
                image_url = article["image_url"]

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
            "image_url": image_url,  # candidate source image; downloaded by worker
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
