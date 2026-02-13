#!/usr/bin/env python3
"""Backfill keyword tags for all existing articles."""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import get_session, init_db
from db.models import Article
from tagging import tag_article

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    init_db()
    session = get_session()
    try:
        articles = session.query(Article).all()
        logger.info("Backfilling tags for %d articles", len(articles))

        updated = 0
        for article in articles:
            # Parse existing tags
            existing_tags: list[str] = []
            if article.tags:
                try:
                    existing_tags = json.loads(article.tags)
                except (json.JSONDecodeError, TypeError):
                    existing_tags = []

            # Generate keyword tags
            keyword_tags = tag_article(article.title, article.content)

            # Merge (dedup, preserve order)
            merged = list(dict.fromkeys(existing_tags + keyword_tags))
            new_tags_json = json.dumps(merged)

            if new_tags_json != article.tags:
                article.tags = new_tags_json
                updated += 1

        session.commit()
        logger.info("Updated %d articles (of %d total)", updated, len(articles))

        # Verify
        empty_count = session.query(Article).filter(Article.tags == "[]").count()
        logger.info("Articles with empty tags: %d", empty_count)
    finally:
        session.close()


if __name__ == "__main__":
    main()
