"""Semantic deduplication service — Jaccard similarity on LLM-extracted entities.

Uses the 'semantic_fingerprint' field from material metadata
(populated by classifier during Phase 2) to detect near-duplicate content.

How it works:
    1. Classifier extracts 10-15 key factual entities (names, orgs, places, numbers)
    2. We compare entity sets using Jaccard similarity: |A ∩ B| / |A ∪ B|
    3. uniqueness_score = 10 × (1 - max_similarity)
    4. Score < 2.0 → considered a duplicate → auto-skipped by autopilot
"""

import uuid
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.material import RawMaterial

log = structlog.get_logger()

# Title-based dedup (complements Jaccard). Entity-overlap counting was tried and
# abandoned (06-04): news items about the same ongoing affair legitimately share
# 5+ named entities, so no entity threshold separates "same text re-published /
# cross-edition" from "different follow-up on the same story" — it kept killing
# real follow-ups and starving the feed. Titles do separate them: the same news
# item carries an (almost) identical headline across editions/re-scrapes, while
# a follow-up has a distinctly different one. We flag a duplicate when the
# normalized title is (near-)identical to a recent material's.
DUPLICATE_UNIQUENESS = 3.0      # forced score when the rule fires (< autopilot's 4.5 skip)
TITLE_DUP_JACCARD = 0.75        # word-level Jaccard on normalized titles ≥ this → same news


def _jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Compute Jaccard similarity between two sets.

    Returns 0.0 if both sets are empty, else |A ∩ B| / |A ∪ B|.
    """
    if not set_a and not set_b:
        return 0.0
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def _title_word_set(title: str) -> set[str]:
    """Normalize a headline to a set of significant lowercase word-tokens.

    Strips emoji/punctuation, lowercases, drops 1-2 char tokens. Used to detect
    the SAME news item across editions/re-scrapes (near-identical headline),
    independent of language script.
    """
    if not title:
        return set()
    import re

    tokens = re.findall(r"\w+", title.lower(), flags=re.UNICODE)
    return {t for t in tokens if len(t) > 2}


def _title_similarity(a: str, b: str) -> float:
    """Word-level Jaccard between two normalized titles (0.0–1.0)."""
    return _jaccard_similarity(_title_word_set(a), _title_word_set(b))


def compute_uniqueness_score(
    material_id: uuid.UUID,
    fingerprint: list[str],
    session: Session,
    tenant_id: uuid.UUID,
    lookback_hours: int = 48,
) -> float:
    """Compute uniqueness score for a material based on semantic fingerprint.

    Compares the material's key entities against all other materials
    from the last `lookback_hours` hours within the same tenant.

    Args:
        material_id: ID of the material being scored (excluded from comparison).
        fingerprint: List of key entity strings from classification.
        session: SQLAlchemy session.
        tenant_id: Tenant ID for scoping.
        lookback_hours: How far back to look for duplicates.

    Returns:
        Score 0.0-10.0 where 10 = completely unique, 0 = exact duplicate.
    """
    if not fingerprint:
        # No fingerprint available (old material) — assume unique
        return 10.0

    fp_set = {e.lower().strip() for e in fingerprint if e}
    if not fp_set:
        return 10.0

    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    # Title of the material being scored (for title-based dedup).
    self_title = session.execute(
        select(RawMaterial.title).where(RawMaterial.id == material_id)
    ).scalar()

    # Fetch semantic fingerprints + titles of recent materials (excluding self)
    recent = session.execute(
        select(
            RawMaterial.id,
            RawMaterial.metadata_["semantic_fingerprint"],
            RawMaterial.title,
        )
        .where(
            RawMaterial.tenant_id == tenant_id,
            RawMaterial.scraped_at >= cutoff,
            RawMaterial.id != material_id,
            # 'evaluated' is the dominant post-scoring status and MUST be in the
            # comparison pool — omitting it (the old bug) made dedup compare a
            # new candidate against only a small slice of recent materials and
            # let same-story dupes through.
            RawMaterial.status.in_(
                ["classified", "evaluated", "adapting", "adapted", "published"]
            ),
        )
        .limit(500)  # Safety cap
    ).all()

    if not recent:
        return 10.0

    max_sim = 0.0
    most_similar_id = None
    title_hit: tuple[uuid.UUID, float] | None = None  # (id, title_similarity)

    for row_id, other_fp_raw, other_title in recent:
        # Title-based dedup: the SAME news item keeps an (almost) identical
        # headline across editions/re-scrapes; a follow-up has a different one.
        if self_title and other_title:
            t_sim = _title_similarity(self_title, other_title)
            if t_sim >= TITLE_DUP_JACCARD and (title_hit is None or t_sim > title_hit[1]):
                title_hit = (row_id, t_sim)

        if not other_fp_raw or not isinstance(other_fp_raw, list):
            continue
        other_set = {e.lower().strip() for e in other_fp_raw if isinstance(e, str) and e}
        if not other_set:
            continue

        sim = _jaccard_similarity(fp_set, other_set)
        if sim > max_sim:
            max_sim = sim
            most_similar_id = row_id

    if max_sim > 0.5:
        log.info(
            "dedup.similar_found",
            material_id=str(material_id),
            similar_to=str(most_similar_id),
            similarity=round(max_sim, 3),
            entities_overlap=round(max_sim * len(fp_set)),
        )

    jaccard_score = round(10.0 * (1.0 - max_sim), 2)

    # Title near-match → same news item republished/cross-edition. Force a
    # duplicate-level score regardless of a deceptively-high entity Jaccard.
    if title_hit is not None:
        forced = min(jaccard_score, DUPLICATE_UNIQUENESS)
        log.info(
            "dedup.title_match",
            material_id=str(material_id),
            similar_to=str(title_hit[0]),
            title_similarity=round(title_hit[1], 3),
            jaccard_score=jaccard_score,
            forced_score=forced,
        )
        return max(0.0, min(10.0, forced))

    return max(0.0, min(10.0, jaccard_score))


def is_duplicate(
    material_id: uuid.UUID,
    fingerprint: list[str],
    session: Session,
    tenant_id: uuid.UUID,
    threshold: float = 0.85,
    lookback_hours: int = 48,
) -> bool:
    """Quick check: is this material a near-duplicate?

    Args:
        threshold: Jaccard similarity above this = duplicate. Default 0.85.

    Returns:
        True if a near-duplicate was found.
    """
    score = compute_uniqueness_score(
        material_id, fingerprint, session, tenant_id, lookback_hours
    )
    # uniqueness < 1.5 means similarity > 0.85
    return score < (10.0 * (1.0 - threshold))
