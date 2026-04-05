# buyanopenpilotcar.today

Find openpilot-compatible vehicles for sale on CarMax.

## How it works

```
pipeline/data/ref/CARS.md (opendbc) + pipeline/package_keywords.json
        │
        ▼ pipeline/matcher.py
pipeline/data/openpilot_cars.json
        │
        ▼ imported at build time
frontend/ (Vite + SolidJS)
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

# Build reference data from pipeline/data/ref/CARS.md
uv run python markdown_to_json.py

# Scrape CarMax (requires cookies — see pipeline/README.md)
uv run python scraper.py

# Merge + match
uv run python merge_inventory.py
uv run python matcher.py
# output: pipeline/data/openpilot_cars.json
```

See [`pipeline/README.md`](pipeline/README.md) for full setup, cookie config, and CI runbook.

## Running the frontend

Requires [Bun](https://bun.sh/).

```bash
cd frontend
bun install
bun run dev
```

## CI

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| `pipeline-scrape` | daily 8am UTC | scrape → match → PR with updated data |
| `pipeline-update-ref-data` | daily 10am UTC | sync `pipeline/data/ref/CARS.md` from opendbc, rebuild ref data → PR |
| `pipeline-validate-reference-data` | PR touching `pipeline/data/ref/CARS.md` or `package_keywords.json` | validate reference data schema |
| `pipeline-check-store-coordinates` | push / PR to main | typecheck + build frontend, validate store coords |
