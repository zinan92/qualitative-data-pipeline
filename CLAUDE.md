# qualitative-data-pipeline (park-intel)

## Project Overview
Qualitative data pipeline collecting articles from Twitter, Hacker News, Substack, YouTube, Xueqiu into a structured API for trading analyst briefings. Features keyword + LLM tagging for relevance scoring and narrative extraction.

## Tech Stack
- **Backend**: FastAPI, SQLAlchemy 2.0, Python 3.11+
- **Database**: SQLite at `data/park_intel.db`
- **Dependencies**: feedparser, requests, anthropic, python-dotenv

## Architecture
```
Collectors (fetch) → BaseCollector.save (dedup + keyword tagging) → SQLite
                                                                      ↓
LLM Tagger (async backfill) → relevance_score + narrative_tags → SQLite
                                                                      ↓
                                                    FastAPI API → JSON
```

## Key Files
- `main.py` — FastAPI app entry (port 8001)
- `config.py` — Source configuration + env loading
- `db/models.py` — Article model (source, title, content, url, tags, score, relevance_score, narrative_tags)
- `db/migrations.py` — Idempotent schema migrations
- `api/routes.py` — 6 endpoints: health, latest, search, digest, signals, sources
- `collectors/base.py` — BaseCollector abstract class (with auto keyword tagging)
- `collectors/twitter.py` — Twitter collector (bird CLI, timeline + 41 KOL accounts)
- `collectors/hackernews.py` — HN Algolia API collector
- `collectors/substack.py` — Substack RSS collector (7 feeds)
- `collectors/youtube.py` — YouTube RSS collector (6 channels)
- `collectors/xueqiu.py` — Xueqiu collector (hot timeline + KOL feeds)
- `tagging/keywords.py` — Regex-based keyword tagger (13 tag categories)
- `tagging/llm.py` — Claude Sonnet LLM tagger for relevance + narratives
- `scripts/run_collectors.py` — Run all collectors
- `scripts/backfill_tags.py` — Backfill keyword tags on existing articles
- `scripts/run_llm_tagger.py` — Run LLM tagger on unscored articles

## API Endpoints
- `GET /api/health` — Healthcheck
- `GET /api/articles/latest?limit=20&source=twitter&min_relevance=4` — Recent articles
- `GET /api/articles/search?q=keyword` — Keyword search
- `GET /api/articles/digest` — Grouped by source with top tags
- `GET /api/articles/signals?hours=24&compare_hours=24` — Topic heat, narrative momentum, relevance distribution
- `GET /api/articles/sources` — Source summary with counts

## Commands
```bash
# Run API server
python main.py  # port 8001

# Run all collectors
python scripts/run_collectors.py

# Run specific collector
python scripts/run_collectors.py --source xueqiu

# Backfill keyword tags
python scripts/backfill_tags.py

# Run LLM tagger (requires ANTHROPIC_API_KEY in .env)
python scripts/run_llm_tagger.py --limit 10
python scripts/run_llm_tagger.py --backfill

# Run tests
pytest tests/
```

## Environment Variables (.env)
- `ANTHROPIC_API_KEY` — Required for LLM tagging
- `XUEQIU_COOKIE` — Optional, for authenticated Xueqiu access

## Conventions
- All collectors inherit from `BaseCollector`
- Dedup via unique `source_id` per source
- Tags stored as JSON array in SQLite
- Keyword tags auto-applied on ingest via BaseCollector.save()
- Content truncated to 500 chars in API responses

## Tag Categories (13)
ai, crypto, macro, geopolitics, china-market, us-market, sector/tech, sector/finance, sector/energy, trading, regulation, earnings, commodities

## Phase 1A — COMPLETE
- Article model: relevance_score (1-5) + narrative_tags (JSON)
- Keyword tagger (13 categories, bilingual CN/EN)
- LLM tagger (Claude Sonnet, batch processing)
- Xueqiu collector (Chinese source)
- /api/articles/signals endpoint (topic heat + narrative momentum)
- 31 tests passing

## Phase 1B TODO (Next)
- Bridge park-intel signals to quant-data-pipeline (ashare)
- ashare proxies /api/articles/signals from park-intel

## Related Project
- **quant-data-pipeline** (ashare) runs on port 8000, provides quantitative data
- Repo: https://github.com/zinan92/quant-data-pipeline
