"""Data fix: backfill empty semantic_fingerprint on recently-scraped materials.

Between 2026-05-25 and the tool_choice fix, the KIE models answered in prose
instead of calling classify_article, so many materials were stored with an
empty `key_entities` → empty `semantic_fingerprint`. An empty fingerprint makes
compute_uniqueness_score return 10.0 (fully unique), which silently disables
dedup for that material — letting duplicate stories publish.

This script re-runs the (now tool_choice-forced) classifier on affected
materials and repopulates metadata.semantic_fingerprint + ai_classification.

Scope: only materials scraped within the dedup lookback window (default 48h),
since older ones no longer affect future dedup comparisons.

Usage (inside the backend/worker container, AFTER deploying the classifier fix):
    docker exec -it contenzavod-backend python scripts/backfill_fingerprints.py
    docker exec -it contenzavod-backend python scripts/backfill_fingerprints.py --hours 72
    docker exec -it contenzavod-backend python scripts/backfill_fingerprints.py --dry-run
"""

import argparse
import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from ai.classifier import AIServiceTemporarilyUnavailable, classify_article
from app.database import get_sync_session
from app.models.material import RawMaterial


def _has_fingerprint(material: RawMaterial) -> bool:
    fp = (material.metadata_ or {}).get("semantic_fingerprint")
    return isinstance(fp, list) and len(fp) > 0


async def _reclassify_all(
    targets: list[tuple[str, str, str, str]], max_concurrent: int = 3
) -> dict[str, dict]:
    """Classify targets concurrently. Returns {material_id: classification}."""
    semaphore = asyncio.Semaphore(max_concurrent)
    results: dict[str, dict] = {}

    async def _one(mat_id: str, title: str, content: str, url: str) -> None:
        async with semaphore:
            try:
                res = await classify_article(title, content, url)
            except AIServiceTemporarilyUnavailable:
                print(f"  · {mat_id[:8]} skipped — AI temporarily unavailable")
                return
            except Exception as e:  # noqa: BLE001 — never let one item kill the batch
                print(f"  · {mat_id[:8]} error: {str(e)[:80]}")
                return
            if res and res.get("key_entities"):
                results[mat_id] = res
            else:
                print(f"  · {mat_id[:8]} no usable result")

    await asyncio.gather(*(_one(*t) for t in targets))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill empty semantic fingerprints.")
    parser.add_argument("--hours", type=int, default=48, help="Lookback window (default 48).")
    parser.add_argument("--limit", type=int, default=500, help="Max materials to process.")
    parser.add_argument("--dry-run", action="store_true", help="Only report, do not write.")
    args = parser.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(hours=args.hours)

    # 1. Load candidates (sync), filter to those missing a fingerprint.
    with get_sync_session() as session:
        rows = (
            session.execute(
                select(RawMaterial)
                .where(RawMaterial.scraped_at >= cutoff)
                .order_by(RawMaterial.scraped_at.desc())
                .limit(args.limit)
            )
            .scalars()
            .all()
        )
        targets = [
            (str(m.id), m.title or "", m.content_text or "", m.original_url or "")
            for m in rows
            if not _has_fingerprint(m)
        ]

    print(
        f"Scanned {len(rows)} materials scraped in last {args.hours}h — "
        f"{len(targets)} missing a fingerprint."
    )
    if not targets:
        print("Nothing to backfill.")
        return
    if args.dry_run:
        print("[dry-run] would re-classify the above; no changes written.")
        return

    # 2. Re-classify concurrently (async).
    classified = asyncio.run(_reclassify_all(targets))
    print(f"Re-classified {len(classified)}/{len(targets)} successfully.")

    # 3. Write results back (sync).
    updated = 0
    with get_sync_session() as session:
        for mat_id, result in classified.items():
            material = session.get(RawMaterial, uuid.UUID(mat_id))
            if not material:
                continue
            meta = dict(material.metadata_ or {})
            meta["ai_classification"] = result
            meta["semantic_fingerprint"] = [
                e.lower().strip() for e in result.get("key_entities", []) if e
            ]
            meta["fingerprint_backfilled_at"] = datetime.now(timezone.utc).isoformat()
            material.metadata_ = meta  # reassign so SQLAlchemy detects the change
            updated += 1
        session.commit()

    print(f"Done. Updated {updated} material(s).")


if __name__ == "__main__":
    main()
