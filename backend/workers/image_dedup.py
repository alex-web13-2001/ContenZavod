"""Image URL canonicalization for cover-image deduplication.

The stable identifier of a cover image is its NORMALIZED source URL, not the
image bytes: outlets (Philenews, Cyprus Mail) serve one logical photo under many
byte-variants — WordPress "-WxH"/"-scaled" suffixes, "/image/sNNNx/" CDN
segments, and re-encoded bytes on every fetch (so SHA-256 changes each time).
Normalizing the URL collapses all those variants to one key, which is what lets
dedup recognise "the same photo" and stop it landing on several unrelated posts.

Kept in its own tiny module so both the scraper (workers.scrape_tasks) and the
autopilot publisher (workers.autopilot_tasks) can import it without pulling in
each other's Celery task definitions.
"""

import re
from urllib.parse import urlparse

_WP_SIZE_SUFFIX = re.compile(r"-\d{2,4}x\d{2,4}(?=\.[a-z]{3,4}$)", re.I)
_WP_SCALED_SUFFIX = re.compile(r"-scaled(?=\.[a-z]{3,4}$)", re.I)
_CDN_SIZE_SEGMENT = re.compile(r"/image/s\d+x\d*/", re.I)


def normalize_image_url(url: str) -> str:
    """Canonicalize an image URL so resize/CDN variants collapse to one key.

    - lowercases host, drops scheme and query/fragment (cache-busters)
    - removes WordPress "-WxH" and "-scaled" size suffixes
    - removes "/image/sNNNx/" CDN resize segments
    Returns a stable key identifying the underlying image across variants.
    """
    if not url:
        return ""
    try:
        p = urlparse(url.strip())
    except Exception:
        return url.strip().lower()
    host = (p.netloc or "").lower()
    path = p.path or ""
    path = _CDN_SIZE_SEGMENT.sub("/", path)
    path = _WP_SCALED_SUFFIX.sub("", path)
    path = _WP_SIZE_SUFFIX.sub("", path)
    return f"{host}{path}"
