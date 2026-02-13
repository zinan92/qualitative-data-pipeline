# qualitative-data-pipeline (park-intel)

## Project Overview
Qualitative data pipeline collecting articles from Twitter, Hacker News, Substack, YouTube into a structured API for trading analyst briefings.

## Tech Stack
- **Backend**: FastAPI, SQLAlchemy 2.0, Python 3.11+
- **Database**: SQLite at `data/park_intel.db`
- **Dependencies**: feedparser, requests, httpx

## Architecture
```
Collectors (fetch) → BaseCollector.save (dedup) → SQLite → FastAPI API → JSON
```

## Key Files
- `main.py` — FastAPI app entry (port 8001)
- `config.py` — Source configuration (Twitter accounts, HN keywords, Substack feeds, YouTube channels)
- `db/models.py` — Article model (source, title, content, url, tags, score, published_at)
- `api/routes.py` — 5 endpoints: health, latest, search, digest, sources
- `collectors/base.py` — BaseCollector abstract class
- `collectors/twitter.py` — Twitter collector (bird CLI, 41 KOL accounts)
- `collectors/hackernews.py` — HN Algolia API collector
- `collectors/substack.py` — Substack RSS collector (7 feeds)
- `collectors/youtube.py` — YouTube RSS collector (6 channels)
- `scripts/run_collectors.py` — Run all collectors

## API Endpoints
- `GET /api/health` — Healthcheck
- `GET /api/articles/latest?limit=20&source=twitter` — Recent articles
- `GET /api/articles/search?q=keyword` — Keyword search
- `GET /api/articles/digest` — Grouped by source with top tags
- `GET /api/articles/sources` — Source summary with counts

## Commands
```bash
# Run API server
python main.py  # port 8001

# Run all collectors
python scripts/run_collectors.py

# Run specific collector
python -c "from collectors.twitter import TwitterCollector; TwitterCollector().run()"
```

## Conventions
- All collectors inherit from `BaseCollector`
- Dedup via unique `source_id` per source
- Tags stored as JSON array in SQLite
- Content truncated to 500 chars in API responses

## Phase 1A TODO (Active)
1. Add `relevance_score` (1-5) and `narrative_tags` (JSON) to Article model
2. Auto-tag articles on ingest (AI/crypto/macro/geopolitics/sector-specific)
3. New `/api/articles/signals` endpoint — topic heat, sentiment, narrative momentum
4. Add Chinese source collectors (Xueqiu/Weibo finance)

## Related Project
- **quant-data-pipeline** (ashare) runs on port 8000, provides quantitative data
- Repo: https://github.com/zinan92/quant-data-pipeline
