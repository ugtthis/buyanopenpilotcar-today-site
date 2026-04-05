# Scraper


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

Use this CLI to convert `data/ref/CARS.md` + `package_keywords.json` into `data/ref/opendbc_ref.json`.

```bash
python3 markdown_to_json.py
```

Useful flags:

```bash
python3 markdown_to_json.py --input data/ref/CARS.md --output data/ref/opendbc_ref.json
```

Validate table compatibility only (no output file written):

```bash
python3 markdown_to_json.py --input data/ref/CARS.md --validate-only
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


Workflow contract:

- `output/*.json` is raw scrape output
- `data/*_full.jsonl` is the canonical matcher input
- `data/openpilot_cars.json` is the canonical product output
- healthy runs are eligible for normal automation
- degraded runs are surfaced in the PR summary and title for manual review

## Disclaimer

This scraper is for educational purposes
