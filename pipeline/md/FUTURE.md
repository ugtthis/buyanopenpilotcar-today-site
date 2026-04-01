# Future Work

Deferred improvements — not blocking current ship. Revisit when a concrete need arises.

---

## Decisions made (and why)

Documenting choices so future-us remembers the reasoning, not just the outcome.

### Untracked `output/*.json` from git (Mar 2026)

**What:** Ran `git rm --cached output/` and added `output/` to `.gitignore`. Per-make scrape files are no longer committed.

**Why:** Every PR had ~4.5M lines of JSON diff across 30 output files. The actual meaningful changes (scraper code, product artifact, workflow) were buried. These files are ephemeral scrape snapshots — their listings get merged into `data/*_full.jsonl` (uploaded as a 30-day GitHub Actions artifact) and the product artifact is `data/openpilot_cars.json`. Nothing downstream needs them in git history.

**What almost broke:** `generate_pr_summary.py` read previous run counts from git (`git show origin/main:output/Toyota.json`) to build the run-over-run comparison table. Fix: introduced `data/scrape_counts.json` (~1KB, `{make: count}` pairs) committed instead. Same comparison table, zero bloat.

**What we preserved:** The comparison table still shows "Toyota: 11,279 → 11,342 (+63)". The scraper still writes `output/*.json` to disk (needed by `merge_inventory.py`). The JSONL artifact is still uploaded to GitHub Actions.

### HTML count check moved inline into scraper (Mar 2026)

**What:** Added `check_make_exists()` to `scraper.py`. Deleted `scripts/verify_counts.py` and removed its CI step. Count mismatches now go into `scrape_result.json` alongside `failed_makes`.

**Why:** The old flow was: scrape → verify counts (separate script, separate HTTP request, different time window). The new flow fetches the HTML page and the API data in the same session, seconds apart. Tighter time window = more accurate mismatch detection. Also eliminates a redundant network call and a whole script.

**What this enables:** `generate_pr_summary.py` reads mismatches from one file (`scrape_result.json`) instead of two (`scrape_result.json` + `count_check.json`). The workflow is one step simpler.

### Count mismatch threshold is 3 cars absolute, not a percentage (Mar 2026)

**What:** `COUNT_MISMATCH_THRESHOLD = 3` — if HTML count and API count differ by more than 3, flag it.

**Why considered percentage:** Large makes (Toyota, 11K cars) could have proportionally larger churn. But the mismatch isn't caused by inventory size — it's caused by the time gap between the HTML fetch and the API call (seconds). Cars sold in those seconds are the noise. 3 cars is generous enough for normal churn and tight enough to catch real problems (stale cookies, API throttling). A percentage threshold would be too loose on large makes and too tight on small ones.

### Mismatch logs as warn, not error (Mar 2026)

**What:** Count mismatch logs `⚠️` (warn) not `❌` (error).

**Why:** The scraper continues scraping after a mismatch — it's informational, not fatal. Using error-level suggested the scrape failed when it didn't. The mismatch still gets recorded in `scrape_result.json` and surfaced in the PR summary. It still contributes to degraded workflow state.

### `["-"]` placeholder stays in `package_keywords.json` (Mar 2026)

**What:** Some entries in `package_keywords.json` have `keywords: ["-"]` instead of real keywords or `null`.

**Why not change it:** `["-"]` means "we know the package requirement but haven't written keyword matching rules yet — match anyway for now." Replacing with `null` would break validation in `markdown_to_json.py` — `null` keywords are only valid for `extra_high` and `non_us` confidence levels. Changing this requires rethinking the entire confidence/keyword validation contract. Not worth it until there's a concrete matching accuracy problem.

### Scraper globals (`browser_cookies`, `start_time`) stay for now (Mar 2026)

**What:** These are module-level globals mutated at runtime.

**Why not refactor:** The scraper works as a standalone script called from CI. Nobody imports it as a library. The globals make unit testing harder (requires monkeypatching), but the existing tests work fine with `patch()`. The refactor (move cookies into `ScraperConfig`, pass `start_time` as a parameter) is medium effort with no behavior change. Ship the correctness fixes first; revisit when a concrete testing need arises.

---

## Scraper performance

- **Share one `AsyncSession` across makes** — currently 29 TLS handshakes (one per make). A shared session reuses the connection after the first make. Estimated ~4 min savings on an 80-min run. Risk: a session-level error affects all makes; create a fresh session for the retry pass if this happens.

- **Sort makes by expected size descending** — Toyota and Honda are the two largest makes but start in alphabetical order (H and T), so they rarely overlap. Starting large makes first fills both worker slots immediately and reduces the long tail. Estimated ~10-15 min savings. Requires reading counts from the previous run's output.

- **Drop `indent=2` on output JSON** — `save_results()` writes with `indent=2`, tripling file size. These files are machine-consumed intermediates; no human reads them raw. One-line fix. Now lower priority since `output/` is gitignored.

---

## Scraper correctness

- **Track failed pages in output metadata** — when `fetch_page()` fails mid-scrape, those cars are silently dropped. The current 95% completeness check only fires if >5% of inventory is lost (one dropped page is ~1.7% for Ford). Add a `failed_pages` list to the output JSON so downstream stages and the PR summary can surface it.

- **Detect deterministic vs transient failures before retrying** — retrying a make that failed due to an encoding error or 404 is wasteful. Check the error type before queuing the retry pass; only retry on transient errors (timeouts, 5xx).

- **Add API response schema validation** — `response.json()` is trusted completely. If CarMax renames `items` to `results` or `totalCount` to `total`, the scraper silently produces empty output. A simple guard (`if "items" not in data: raise`) fails fast instead of silently producing bad data.

- **Fix `ScraperConfig.load()` missing-file handling** — currently throws a raw `FileNotFoundError`. Should give a friendly message like `load_makes()` does, or fall back gracefully to defaults.

---

## Scraper design

- **Move cookies and `start_time` off module globals** — `browser_cookies` and `start_time` are module-level globals mutated at runtime. This makes unit-testing `get_headers()` and `log()` require monkeypatching module state. Move cookies into `ScraperConfig`; pass `start_time` as a parameter to `log()`. Medium effort, no behavior change.

- **Enrich `scrape_result.json` with per-make success data** — the file currently records only failures and count mismatches. Adding per-make scraped counts, timestamps, and durations would give downstream stages a single source of truth and eliminate `generate_pr_summary.py` re-reading every output file.

---

## Pipeline decisions (needs explicit answer before acting)

- **`["-"]` placeholder in `package_keywords.json`** — means "we know the package requirement but haven't written keyword rules yet." Semantically obscure. Any redesign requires rethinking the confidence/keyword validation contract (which confidence levels can have null vs placeholder vs real keywords). Leave it until there's a concrete reason to change.

- **Degraded run behavior for product artifact** — should a degraded run (one or more failed makes) produce a debug-only partial `openpilot_cars.json`, or skip it entirely? Currently skipped. The tradeoff: partial output is worse than no output for the web experience, but useful for debugging.

- **Long-term run history** — `output/*.json` are now gitignored; the only history is the GitHub Actions artifact uploads. If run-over-run trend analysis becomes useful (count drift, new makes, support changes), a lightweight append-only log in `data/` would serve that without a database.

---

## Code hygiene (trivial, low risk)

These are from `TODO.md` and are not worth a standalone PR — fold into the next time those files are touched:

- Remove dead `"save": "💾"` entry from the `log()` symbols dict (never referenced)
- Remove default value on `max_retries` param in `fetch_page()` (all call sites pass `config.max_retries` explicitly)
- Simplify cookie string build to a one-liner: `"; ".join(f"{k}={v}" for k, v in cookies.items())`
- Remove `load_cookies()` return value or remove the global — currently the return value is discarded at the call site; the real mechanism is the global side effect
