#!/usr/bin/env python3
"""Run LLM tagger on articles that haven't been scored yet."""

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import get_session, init_db
from db.models import Article
from tagging.llm import LLMTagger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run LLM tagger on unscored articles")
    parser.add_argument("--backfill", action="store_true", help="Process all unscored articles")
    parser.add_argument("--limit", type=int, default=0, help="Process N most recent unscored articles")
    parser.add_argument("--batch-size", type=int, default=10, help="Articles per LLM call")
    parser.add_argument("--budget", type=float, default=5.0, help="Max spend per session ($)")
    args = parser.parse_args()

    if not args.backfill and args.limit <= 0:
        parser.error("Specify --backfill or --limit N")

    init_db()
    session = get_session()
    tagger = LLMTagger(batch_size=args.batch_size, daily_budget=args.budget)

    try:
        query = session.query(Article).filter(Article.relevance_score.is_(None))

        if args.backfill:
            articles = query.order_by(Article.collected_at.desc()).all()
        else:
            articles = query.order_by(Article.collected_at.desc()).limit(args.limit).all()

        logger.info("Found %d unscored articles to process", len(articles))

        if not articles:
            return

        # Process in batches
        scored = 0
        for i in range(0, len(articles), args.batch_size):
            batch = articles[i : i + args.batch_size]
            batch_dicts = [
                {"id": a.id, "title": a.title, "content": a.content, "source": a.source}
                for a in batch
            ]

            results = tagger.tag_batch(batch_dicts)
            if not results:
                logger.warning("Empty results for batch %d, stopping", i // args.batch_size + 1)
                break

            # Map results back by id
            result_map = {r["id"]: r for r in results}
            for a in batch:
                if a.id in result_map:
                    r = result_map[a.id]
                    a.relevance_score = r["relevance_score"]
                    a.narrative_tags = json.dumps(r["narrative_tags"])
                    scored += 1

            session.commit()
            logger.info(
                "Batch %d: scored %d/%d articles (session cost: $%.4f)",
                i // args.batch_size + 1,
                len(results),
                len(batch),
                tagger.session_cost,
            )

        logger.info("Done. Total scored: %d. Session cost: $%.4f", scored, tagger.session_cost)

        # Distribution check
        rows = session.execute(
            session.query(Article.relevance_score, func.count(Article.id))
            .group_by(Article.relevance_score)
            .statement
        ).all()
        for score, count in sorted(rows, key=lambda x: (x[0] is None, x[0])):
            label = str(score) if score is not None else "unscored"
            logger.info("  relevance_score=%s: %d articles", label, count)

    finally:
        session.close()


if __name__ == "__main__":
    from sqlalchemy import func
    main()
