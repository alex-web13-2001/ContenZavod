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

# Ubiquitous entities that carry almost no story-identifying signal — they appear
# in a huge share of Cyprus articles, so they must NOT count toward "same story".
STOPWORD_ENTITIES: frozenset[str] = frozenset({
    "cyprus", "republic of cyprus", "kypros", "nicosia", "lefkosia", "limassol",
    "larnaca", "paphos", "famagusta", "kyrenia", "european union", "eu", "euro",
    "cyprus mail", "philenews", "in-cyprus", "cna", "politis", "police", "government",
})

# Cross-source dedup rule (complements Jaccard). The same event reported by two
# outlets shares the same concrete named entities even when each adds its own
# extras — so Jaccard stays low (~0.25) while the count of shared SPECIFIC
# entities is high. If that count clears the bar AND covers a real fraction of
# the smaller fingerprint, treat it as a duplicate regardless of Jaccard.
SPECIFIC_OVERLAP_MIN = 3        # ≥ this many shared non-stopword entities
SPECIFIC_OVERLAP_FRACTION = 0.30  # AND ≥ this fraction of the smaller specific set
DUPLICATE_UNIQUENESS = 3.0      # forced score when the rule fires (< autopilot's 4.5 skip)


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

    # Fetch semantic fingerprints of recent materials (excluding self)
    # Using raw SQL for JSONB extraction since metadata_ is JSONB
    recent = session.execute(
        select(
            RawMaterial.id,
            RawMaterial.metadata_["semantic_fingerprint"],
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

    # Specific (non-stopword) entities of the candidate — used for the
    # cross-source overlap rule that Jaccard alone misses.
    fp_specific = fp_set - STOPWORD_ENTITIES

    max_sim = 0.0
    most_similar_id = None
    overlap_hit: tuple[uuid.UUID, int, int] | None = None  # (id, shared, smaller_set)

    for row_id, other_fp_raw in recent:
        if not other_fp_raw or not isinstance(other_fp_raw, list):
            continue

        other_set = {e.lower().strip() for e in other_fp_raw if isinstance(e, str) and e}
        if not other_set:
            continue

        sim = _jaccard_similarity(fp_set, other_set)
        if sim > max_sim:
            max_sim = sim
            most_similar_id = row_id

        # Cross-source overlap check on SPECIFIC entities only.
        other_specific = other_set - STOPWORD_ENTITIES
        shared = len(fp_specific & other_specific)
        smaller = min(len(fp_specific), len(other_specific))
        if (
            smaller > 0
            and shared >= SPECIFIC_OVERLAP_MIN
            and shared / smaller >= SPECIFIC_OVERLAP_FRACTION
        ):
            # Keep the strongest overlap (most shared specific entities)
            if overlap_hit is None or shared > overlap_hit[1]:
                overlap_hit = (row_id, shared, smaller)

    if max_sim > 0.5:
        log.info(
            "dedup.similar_found",
            material_id=str(material_id),
            similar_to=str(most_similar_id),
            similarity=round(max_sim, 3),
            entities_overlap=round(max_sim * len(fp_set)),
        )

    jaccard_score = round(10.0 * (1.0 - max_sim), 2)

    # If the cross-source rule fired, force a duplicate-level score (overriding a
    # deceptively-high Jaccard score). This catches the same story told by two
    # outlets in different words/languages, where Jaccard stays ~0.25.
    if overlap_hit is not None:
        forced = min(jaccard_score, DUPLICATE_UNIQUENESS)
        log.info(
            "dedup.cross_source_overlap",
            material_id=str(material_id),
            similar_to=str(overlap_hit[0]),
            shared_specific=overlap_hit[1],
            smaller_specific_set=overlap_hit[2],
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
