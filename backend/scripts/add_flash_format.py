"""Data migration: Add 'flash' to content_formats for all Telegram channels.

Run once after deploying the multi-format autopilot update.
Usage: docker exec -it contenzavod-backend python scripts/add_flash_format.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, text
from app.database import get_sync_session
from app.models.channel import Channel


def main():
    with get_sync_session() as session:
        channels = session.execute(
            select(Channel).where(Channel.channel_type == "telegram")
        ).scalars().all()

        updated = 0
        for ch in channels:
            formats = ch.content_formats or ["short_post"]
            if "flash" not in formats:
                formats = ["flash"] + formats
                ch.content_formats = formats
                updated += 1
                print(f"  ✓ {ch.name}: {formats}")
            else:
                print(f"  · {ch.name}: already has flash")

        session.commit()
        print(f"\nDone. Updated {updated} channel(s).")


if __name__ == "__main__":
    main()
