# CarMax API Scraper

A simple, performant, and maintainable web scraper for CarMax car listings. Uses `curl-cffi` for browser impersonation to bypass bot detection.

## Features

- **Browser Impersonation**: Uses curl-cffi to mimic Chrome's TLS fingerprint
- **Automatic Pagination**: Handles the 100 results/page API limit automatically
- **Configurable**: Easy-to-edit JSON config for makes and settings
- **Rate Limiting**: Built-in delays to avoid detection
- **Error Handling**: Automatic retries with exponential backoff
- **Self-Documenting**: Type hints, docstrings, and clear variable names

## Installation

```bash
# Install uv (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

Requires Python 3.11+

## Configuration

Edit `config.json` to customize:

```json
{
  "makes": ["ford", "toyota", "honda"],
  "delay_seconds": 1.5,
  "max_retries": 3
}
```

| Field | Description | Default |
|-------|-------------|---------|
| `makes` | List of car makes to scrape | `["ford", "toyota", "honda"]` |
| `delay_seconds` | Delay between API requests (seconds) | `1.5` |
| `max_retries` | Number of retry attempts on failure | `3` |

## Usage

### Basic Usage

```bash
uv run python scraper.py
```

This will scrape all makes listed in `config.json`.

### Override Makes via CLI

```bash
uv run python scraper.py --makes ford,toyota,honda
```

### Run Tests

```bash
uv run pytest
```

### Build Reference Data (`markdown_to_json.py`)

Use this CLI to convert `CARS.md` + `package_keywords.json` into `data/opendbc_ref.json`.

```bash
python3 markdown_to_json.py
```

Useful flags:

```bash
python3 markdown_to_json.py --input CARS.md --output data/opendbc_ref.json
```

Validate table compatibility only (no output file written):

```bash
python3 markdown_to_json.py --input CARS.md --validate-only
```

Only the first markdown table is parsed. Any later reference tables are ignored.

Validation is strict. Every car row must include:
- `make`
- `model`
- `package_requirements`

Example error output:

```text
❌ Error: Every car must include make, model, and package_requirements.
  - row 3 missing: model. row=['Acura', '', 'Technology Plus Package', '[Upstream](#upstream)']
```

On validation failure, the command exits with code `1` and writes no output JSON.

`--validate-only` behavior:
- checks required row fields and missing package definitions
- ignores unused package-key warnings (useful for CI/contributor checks)
- prints a success checkmark:

```text
✓ Validation passed: CARS.md (387 vehicles)
```

## Output

Results are saved to the `output/` directory:

```
output/
├── ford.json
├── toyota.json
└── honda.json
```

Each JSON file contains:

```json
{
  "make": "ford",
  "total_count": 1523,
  "scraped_count": 1523,
  "scraped_at": "2026-01-28T10:30:00Z",
  "listings": [
    {
      "stockNumber": "12345678",
      "year": 2022,
      "make": "Ford",
      "model": "F-150",
      "trim": "XLT",
      "price": 42999,
      "mileage": 15234,
      ...
    }
  ]
}
```

## How It Works

### Data Pipeline

1. **Load Config**: Read makes list from `config.json`
2. **For Each Make**: Process sequentially to avoid rate limiting
3. **Fetch First Page**: Get first 100 results + total count
4. **Calculate Pages**: `total_pages = ceil(total_count / 100)`
5. **Fetch Remaining**: Paginate through skip=100, 200, 300...
6. **Merge Results**: Combine all pages into single list
7. **Save Raw JSON**: Write `output/{make}.json` as per-make scrape output
8. **Merge Inventory**: Build `data/*_full.jsonl` as the canonical matcher input
9. **Match Inventory**: Build `data/openpilot_cars.json` as the canonical product output

### API Endpoint

The scraper uses CarMax's public search API:

```
https://www.carmax.com/cars/api/search/run?uri=%2Fcars%2F{make}&skip={offset}&take=100&shipping=-1&sort=price-desc
```

| Parameter | Description |
|-----------|-------------|
| `uri` | `/cars/{make}` (URL encoded) |
| `skip` | Pagination offset (0, 100, 200...) |
| `take` | Results per page (max 100) |
| `shipping` | -1 for all |
| `sort` | price-desc or price-asc |

### Browser Impersonation

The scraper uses `curl-cffi` with `impersonate="chrome120"` to:
- Match Chrome's TLS/JA3 fingerprint
- Use HTTP/2 like modern browsers
- Send realistic headers (Accept, Referer, Origin, etc.)

This helps bypass bot detection systems that check browser signatures.

## Code Structure

All logic is contained in a single file (`scraper.py`) for easy maintenance:

- **Type Hints**: All functions have type annotations
- **Docstrings**: Clear documentation for every function
- **Named Constants**: `MAX_RESULTS_PER_PAGE = 100` (no magic numbers)
- **Dataclasses**: Structured config with `@dataclass`
- **Error Handling**: Try/except blocks with retries

## Troubleshooting

### Import Error: No module named 'curl_cffi'

```bash
uv sync
```

### 403 Forbidden or Access Denied

The scraper uses browser impersonation, but CarMax may still detect automated requests if:
- Delay is too short (increase `delay_seconds`)
- Too many concurrent requests
- IP-based rate limiting

Try increasing the delay or using a VPN.

### Empty Results

Check that:
- The make name is correct (lowercase, e.g., "ford" not "Ford")
- Your internet connection is working
- CarMax's API is accessible

## License

MIT

## Documentation

For current architecture, runbooks, and quirks:

- `md/DATA_PIPELINE.md` - canonical pipeline design, data model, matcher semantics
- `md/OPERATIONS.md` - CI flow, cookies, diagnostics, common failures
- `md/REFACTOR_PLAN.md` - pipeline PR roadmap, design decisions, open decisions
- `md/SCRAPER_ANALYSIS.md` - deep scraper analysis, bugs, performance, design issues
- `md/FUTURE.md` - deferred improvements and reasoning behind past decisions
- `md/TODO.md` - code hygiene items and technical debt

## GitHub Actions Automation

Workflow file: `.github/workflows/scrape.yml`

Current scheduled pipeline:

1. `scraper.py`
2. `merge_inventory.py`
3. `matcher.py`
4. `scripts/generate_pr_summary.py`
5. Auto-create PR

Runs daily at `08:00 UTC` and can also be triggered manually.

Workflow contract:

- `output/*.json` is raw scrape output
- `data/*_full.jsonl` is the canonical matcher input
- `data/openpilot_cars.json` is the canonical product output
- healthy runs are eligible for normal automation
- degraded runs are surfaced in the PR summary and title for manual review

## Disclaimer

This scraper is for educational purposes. Respect CarMax's terms of service and robots.txt. Use responsibly and avoid overloading their servers.
