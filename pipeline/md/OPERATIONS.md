# Operations Runbook

Operational guide for running and monitoring the pipeline.

## Daily CI Flow

Workflow: `.github/workflows/scrape.yml`

Current step order:
1. `uv run python scraper.py`
2. `uv run python merge_inventory.py`
3. `uv run python matcher.py`
4. `uv run python scripts/generate_pr_summary.py`
5. create PR (`peter-evans/create-pull-request`)

PR body comes from `.github/pr-summary.md` and includes:
- workflow state (`healthy` or `degraded`)
- canonical artifact status
- per-make scrape counts
- matcher `pipeline_metrics` block

Workflow state contract:
- `healthy` means the raw scrape outputs exist, `data/*_full.jsonl` exists, and `data/openpilot_cars.json` exists.
- `degraded` means at least one canonical artifact is missing, so the PR title is marked for manual review.

Artifact roles:
- `output/*.json` = raw per-make scrape output
- `data/*_full.jsonl` = canonical matcher input
- `data/openpilot_cars.json` = canonical product output

## Local Full Run

```bash
python3 markdown_to_json.py
python3 scraper.py
python3 merge_inventory.py
python3 matcher.py
python3 scripts/generate_pr_summary.py
```

## Cookies (Critical)

Preferred in CI:
- `ABCK_COOKIE`
- `KMXVISITOR_COOKIE`

Local fallback:
- `cookies.json`

Behavior without valid cookies:
- scraper may return partial inventory
- pipeline still completes, but match coverage may drop

Required cookie roles:
- `_abck`: Akamai bot-management cookie; required for full inventory behavior.
- `KmxVisitor_0`: visitor preference cookie; should include `ShowReservedCars=true&ComingSoon=true`.

Typical setup:
1. Open `carmax.com` in a browser.
2. Copy `_abck` value from browser cookies.
3. Set GitHub Actions secrets:
   - `ABCK_COOKIE=<copied_abck>`
   - `KMXVISITOR_COOKIE=ShowReservedCars=true&ComingSoon=true`

Operational note:
- `_abck` is long-lived (repo comments indicate expiration around Jan 2027), but should still be treated as rotatable.
- If counts drop unexpectedly, refresh cookies first.

## API Quirks (Important)

- Endpoint: `https://www.carmax.com/cars/api/search/run`
- Pagination limit: `take=100` max per request.
- Without valid cookies, API may return significantly reduced inventory.
- API can return cars not matching requested make if filtering is weak; scraper guards against this by re-filtering make in code.
- `totalCount` and `items` can diverge from expected if cookies are stale; track `scraped_count` per make and investigate large gaps.
- `total_count: 0` can be valid for unsupported/unavailable brands and should not be treated as failure.

## Investigation Findings To Keep In Mind

- Full-inventory behavior depends on both cookie validity and browser-like request profile.
- Rate-limit and bot-detection risk is controlled by:
  - conservative concurrency (`max_concurrent_makes`)
  - request delays + jitter
  - retry with backoff
- CI uses fresh runner IPs, which helps long-term stability but does not eliminate cookie drift risk.

## Fast Health Checks

After `matcher.py`:

```bash
python3 -c "import json; d=json.load(open('data/openpilot_cars.json')); print(d['pipeline_metrics'])"
```

Check these first:
- `json_parse_errors` should usually be `0`
- `match_rate` should stay in expected range for your current scrape
- `no_match_breakdown.keyword_mismatch` spikes can signal feature text drift
- `no_match_breakdown.year_mismatch` spikes can signal year parsing/reference issues
- `no_match_breakdown.unsupported_models` spikes can signal normalization or market mix shifts

## Known Quirks

- `total_count: 0` for a make is valid data, not a failure.
- `keywords: null` and `keywords: ["-"]` both bypass feature keyword matching in matcher.
- A keyword mismatch produces no match — confidence is never downgraded; the car is simply skipped. This means `no_match_breakdown.keyword_mismatch` counts cars where year matched but at least one keyword was absent.
- `non_us` entries in `opendbc_ref.json` are excluded from the match index — they appear in `openpilot_cars.json` as entries but `available_years` is always empty and all years land in `unavailable_years`.
- Duplicate VIN warnings can be valid when one listing satisfies multiple reference variants.
- `openpilot_cars.json` is overwritten on each matcher run.

## Common Failures and First Fix

### Scraper returns unexpectedly low totals
- Re-check cookie validity first.
- Re-run scraper for confirmation.

### Matcher match rate drops sharply
- Inspect `pipeline_metrics.no_match_breakdown`.
- If `keyword_mismatch` rose: inspect feature text and keyword aliases.
- If `year_mismatch` rose: inspect `years` in `opendbc_ref.json`.

### No input JSONL found for matcher
- Run `python3 merge_inventory.py` first, or pass `--input`.

### PR summary missing matcher metrics
- Confirm `matcher.py` ran before summary generation.
- Confirm `data/openpilot_cars.json` contains `pipeline_metrics`.

## Source Of Truth Docs

- Technical data model and boundaries: `md/DATA_PIPELINE.md`
- This file: operational execution and diagnostics
