#!/usr/bin/env python3
"""CLI to run park-intel collectors."""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from collectors.hackernews import HackerNewsCollector
from collectors.substack import SubstackCollector
from collectors.twitter import TwitterCollector
from collectors.xueqiu import XueqiuCollector
from collectors.youtube import YouTubeCollector

COLLECTORS: dict[str, type] = {
    "twitter": TwitterCollector,
    "hackernews": HackerNewsCollector,
    "substack": SubstackCollector,
    "youtube": YouTubeCollector,
    "xueqiu": XueqiuCollector,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run park-intel collectors")
    parser.add_argument(
        "--source",
        choices=list(COLLECTORS.keys()),
        help="Run a specific collector (default: all)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    sources = [args.source] if args.source else list(COLLECTORS.keys())

    total_saved = 0
    for source in sources:
        collector_cls = COLLECTORS[source]
        logging.info("Running collector: %s", source)
        try:
            collector = collector_cls()
            saved = collector.run()
            total_saved += saved
        except Exception:
            logging.exception("Collector %s failed", source)

    logging.info("Done. Total new articles saved: %d", total_saved)


if __name__ == "__main__":
    main()
