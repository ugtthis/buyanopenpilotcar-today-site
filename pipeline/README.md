# Pipeline

Scrapes CarMax inventory, matches listings to openpilot-compatible vehicles, and produces `data/openpilot_cars.json`.

## Setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Running locally

```bash
uv run python markdown_to_json.py   # build ref data from data/ref/CARS.md
uv run python enricher.py           # enrich with support specs from opendbc-site
uv run python scraper.py            # scrape CarMax listings
uv run python merge_inventory.py    # merge per-make scrapes into JSONL
uv run python matcher.py            # match inventory → data/openpilot_cars.json
```

### Cookies

The scraper needs browser cookies for full inventory access.

- **CI**: `ABCK_COOKIE` and `KMXVISITOR_COOKIE` GitHub Actions secrets
- **Local**: create `cookies.json`:

```json
{ "_abck": "...", "KmxVisitor": "..." }
```

### Config

Scraper behavior is tuned via `config.json`:

```json
{
  "delay_seconds": 1.5,
  "delay_jitter": 0.8,
  "max_retries": 3,
  "max_concurrent_makes": 2
}
```

Makes are loaded from `data/ref/opendbc_ref.json` automatically.
