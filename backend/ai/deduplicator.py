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

    max_sim = 0.0
    most_similar_id = None

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

    if max_sim > 0.5:
        log.info(
            "dedup.similar_found",
            material_id=str(material_id),
            similar_to=str(most_similar_id),
            similarity=round(max_sim, 3),
            entities_overlap=round(max_sim * len(fp_set)),
        )

    score = round(10.0 * (1.0 - max_sim), 2)
    return max(0.0, min(10.0, score))


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
