# buyanopenpilotcar.today

Find openpilot-compatible vehicles for sale on CarMax.

## Running the frontend

Requires [Bun](https://bun.sh/).

```bash
cd frontend
bun install
bun run dev
```

## How it works

```
pipeline/data/ref/CARS.md (opendbc) + pipeline/package_keywords.json
        │
        ▼ pipeline/markdown_to_json.py
pipeline/data/ref/opendbc_ref.json
        │
        ▼ pipeline/enricher.py
pipeline/data/ref/opendbc_enriched_ref.json
        │
scraper.py → merge_inventory.py → matcher.py
        │
        ▼
pipeline/data/openpilot_cars.json
        │
        ▼ imported at build time
frontend/
```

The pipeline produces `pipeline/data/openpilot_cars.json`

## Project structure

```
pipeline/   Python data pipeline (uv)
frontend/   Vite + SolidJS web app
.github/    CI workflows for both
```

## Running the pipeline

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
cd pipeline
uv sync

# Build raw reference data from pipeline/data/ref/CARS.md
uv run python markdown_to_json.py

# Enrich into pipeline/data/ref/opendbc_enriched_ref.json
uv run python enricher.py

# Scrape CarMax (requires cookies — see pipeline/README.md)
uv run python scraper.py

# Merge + match
uv run python merge_inventory.py
uv run python matcher.py
# output: pipeline/data/openpilot_cars.json
```

See [`pipeline/README.md`](pipeline/README.md) for full setup, cookie config, and CI runbook.
