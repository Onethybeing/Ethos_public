"""Backfill AI slop fields for already-ingested articles.

Examples:
    uv run python scripts/backfill_ai_slop.py
    uv run python scripts/backfill_ai_slop.py --all --use-l2 --update-qdrant
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from backend.config import get_settings
from backend.core.db.postgres import init_db
from backend.core.logging_config import setup_logging
from backend.services.slop_detector.slop_backfill import backfill_ai_slop_scores


def parse_args() -> argparse.Namespace:
    """Parse command-line args for slop backfill."""
    parser = argparse.ArgumentParser(
        description="Backfill ai_slop_score and ai_slop_label for existing Postgres articles."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process at most N articles.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all rows, not only records with missing slop fields.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="How many articles to process per DB transaction.",
    )
    parser.add_argument(
        "--use-l2",
        action="store_true",
        help="Enable LLM layer-2 for uncertain layer-1 outputs.",
    )
    parser.add_argument(
        "--update-qdrant",
        action="store_true",
        help="Also patch ai_slop payload fields in Qdrant.",
    )
    return parser.parse_args()


async def _main() -> None:
    args = parse_args()

    settings = get_settings()
    setup_logging(settings.log_level)

    await init_db()

    stats = await backfill_ai_slop_scores(
        limit=args.limit,
        only_missing=not args.all,
        batch_size=args.batch_size,
        use_l2=args.use_l2,
        update_qdrant=args.update_qdrant,
    )

    print("AI slop backfill completed")
    print(f"targeted={stats.targeted}")
    print(f"processed={stats.processed}")
    print(f"updated={stats.updated}")
    print(f"skipped={stats.skipped}")
    print(f"errors={stats.errors}")
    print(f"qdrant_updated={stats.qdrant_updated}")
    print(f"qdrant_errors={stats.qdrant_errors}")


if __name__ == "__main__":
    asyncio.run(_main())
