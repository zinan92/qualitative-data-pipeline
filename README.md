# park-intel

Qualitative data pipeline — collects articles from Twitter, Hacker News, and Substack into a local SQLite database with a FastAPI query layer.

## Quick Start

```bash
pip install -r requirements.txt

# Run collectors
python scripts/run_collectors.py                    # all collectors
python scripts/run_collectors.py --source hackernews  # specific source

# Start API server
python main.py
# → http://127.0.0.1:8001/docs
```

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/health` | Healthcheck |
| `GET /api/articles/latest?limit=20&source=twitter` | Latest articles |
| `GET /api/articles/search?q=bitcoin&days=7` | Search by keyword |
| `GET /api/articles/sources` | Source summary with counts |

## Collectors

- **Twitter** — via `bird` CLI (@xiaomucrypto, @coolish, @ohxiyu, @billtheinvestor)
- **Hacker News** — Algolia API, score >= 50
- **Substack** — RSS feeds (Pomp, Doomberg, Ethan Mollick, SemiAnalysis, etc.)

## Data

SQLite DB at `data/park_intel.db` (gitignored).
