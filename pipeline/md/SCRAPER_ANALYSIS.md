# Scraper Analysis

A deep analysis of `scraper.py` — what it does well, where it breaks, and what paths exist to make it the simplest robust scraper it can be.

This analysis is grounded in the full pipeline context: how the scraper feeds `merge_inventory.py`, how the matcher consumes the merged output, how the GitHub Actions workflow gates healthy vs degraded runs, and what the REFACTOR_PLAN already decided to preserve vs change.

---

## How the scraper fits in the pipeline

```
CARS.md (from opendbc)
        │
        ▼
markdown_to_json.py ──► data/opendbc_ref.json (reference: makes, models, years, packages)
                                │
                                │ load_makes() reads make list from here
                                ▼
                          scraper.py ──► output/<Make>.json (one per make)
                                │
                                ▼
                        merge_inventory.py ──► data/YYYY-MM-DD_full.jsonl
                                │
                                ▼
                          matcher.py ──► data/openpilot_cars.json (product artifact)
                                │
                                ▼
                        verify_counts.py ──► data/count_check.json
                        generate_pr_summary.py ──► .github/pr-summary.md
                                │
                                ▼
                          GitHub PR (auto-merge if healthy)
```

The scraper is the most fragile and expensive stage. It makes hundreds of HTTP requests against a real website over 80 minutes. Everything downstream either validates the scraper's output or transforms it. If the scraper produces bad data, every downstream stage inherits that badness.

---

## Bugs

### 1. Škoda permanently fails — Referer header encoding

**The bug:** `get_headers()` puts the raw make name into the `Referer` header (line 105). When `make` contains non-ASCII characters like `Š` (U+0160), `curl_cffi` tries to encode the header as `latin-1` and throws. The `uri` param on line 123 correctly uses `quote(make)`, but the Referer does not.

**Why it matters:** This is a deterministic failure. Škoda fails on every attempt, survives the retry pass, and is permanently recorded as a failed make. The entire pipeline is marked degraded and auto-merge is blocked — all because of a missing `quote()` call.

**Fix:** One line.

```python
"Referer": f"https://www.carmax.com/cars/{quote(make)}",
```

**Broader concern:** This reveals that there are no tests for non-ASCII makes. Any future make with diacritics or non-Latin characters would hit the same crash.

### 2. Failed pages silently drop cars

**The bug:** In `scrape_make()`, when a mid-scrape page fails after retries, the code logs a warning (line 201) and continues to the next page. The gap in inventory is never recorded.

**What happens:** If page 7 of 60 fails for Ford, the output contains pages 1-6 and 8-60 but is missing ~100 cars from page 7. The 95% threshold check on line 204 only fires if the total loss exceeds 5% of the expected count. For a 6000-car make, a single dropped page is 1.7% — well under the threshold.

**Why it matters downstream:** `merge_inventory.py` blindly flattens whatever listings exist. `matcher.py` then finds the cheapest car per variant-year. If the actual cheapest car was on the dropped page, the product artifact silently shows the second-cheapest. The user never knows.

**Paths:**

- **Minimal:** Track which pages failed and include that metadata in the output JSON. At least `verify_counts.py` and the PR summary can surface it.
- **Better:** Treat any page failure as a make-level failure. The make goes into the retry queue and gets a full fresh scrape. This aligns with the REFACTOR_PLAN's principle that partial curated output is worse than delayed output.

### 3. `totalCount`-based pagination on a filtered result set

**The bug:** `total_pages` is computed from `totalCount` (the API's unfiltered count). But the scraper filters items to only those matching the requested make (lines 174, 195). When the API redirects an unknown make to "all cars," `totalCount` could be 50,000+.

**Current protection:** Line 177 catches the case where zero items match on the first page and returns early. But if even one item matched by coincidence (e.g., a make called "Ram" matching a random listing), the scraper would paginate through all 500 pages of the entire CarMax inventory.

**Likelihood:** Low. The filter on line 174 makes it unlikely for a legitimate make. But for edge-case makes where the API might return a mixed result set (like partial matches), this is a latent time bomb.

**Fix:** Add a second guard — if `len(items) / total_count < some_threshold` after the first few pages, bail early.

---

## Performance

### 4. One AsyncSession per make — 29 TLS handshakes

**What happens:** `scrape_make()` creates a new `AsyncSession` on every invocation (line 163). With 29 makes, that is 29 separate TLS handshakes and 29 connection pools, all to the same host (`www.carmax.com`).

**Why it matters:** Each TLS handshake to CarMax takes several seconds (visible in the logs — the gap between "Starting..." and "Found X cars" is consistently ~10s). A shared session would reuse the connection and skip the handshake after the first make.

**Estimated savings:** ~9 seconds per make after the first. With 29 makes, that is ~4 minutes of pure handshake overhead on an 80-minute run. Not transformative but meaningful, and it is also the more correct pattern for `curl_cffi`.

**Why it is not a trivial change:** The semaphore controls concurrency at the make level, but a shared session means concurrent makes share a connection pool. `curl_cffi`'s `AsyncSession` is safe for concurrent use, so this should work. But it changes the isolation model — a session-level failure (e.g., a broken connection) would affect all makes sharing it, not just one.

**Path:** Create the `AsyncSession` once in `main()` and pass it to `scrape_make()`. The semaphore already limits concurrent usage. If session-level errors occur, catch them and create a fresh session for the retry pass.

### 5. `indent=2` on large output files

**What happens:** `save_results()` writes each make's JSON with `indent=2` (line 223). The Acura output file is 139,552 lines. Toyota at 11,278 cars is likely 1.4 million+ lines.

**Why it matters:** Indentation roughly triples file size. These files are machine-consumed intermediates — `merge_inventory.py` reads them, extracts the listings, and writes them as JSONL. No human reads the raw `output/<Make>.json` files. The indentation costs disk I/O during the write, disk I/O during the merge read, and git storage if these files are committed (which they currently are).

**The git cost:** The workflow commits `output/*.json` on every run. At ~3x size with indentation, that is ~3x the diff size in every PR. The REFACTOR_PLAN's Open Decision #5 already questions whether committing these files is worth the storage cost.

**Fix:** `json.dump(data, f)` — just drop the `indent` parameter. If human inspection is needed, pipe through `python -m json.tool`.

### 6. Delay is applied unconditionally before every page

**What happens:** Lines 187-189 compute a jittered delay and sleep before every single page fetch. The delay range is 0.7s to 2.3s (1.5 ± 0.8, floored at 0.3).

**Why it is mostly fine:** The delay exists to avoid hammering CarMax. With 2 concurrent workers, each making requests with ~1.5s gaps, the effective rate is ~1.3 requests/second. This is responsible.

**What is unideal:** The delay fires even on the first page of a new make, where the semaphore may have already imposed minutes of waiting. And it fires between the response arriving and the next request, meaning the actual gap is `delay + response_time`. For a 10-second first page response, the real gap is 11.5 seconds, not 1.5.

**Path:** This is not worth changing. The current behavior is conservative and that is appropriate for scraping a production website. Mentioning it only for completeness.

### 7. Toyota tail: one slow make dominates the runtime

**Observation from logs:** Toyota has 11,279 cars across 113 pages. Once Volkswagen (33 pages) finished, Toyota ran solo with only 1 of 2 worker slots occupied. The last ~15 minutes of the 80-minute run were Toyota alone.

**Why the current design causes this:** Makes are queued in alphabetical order (from the reference file). Toyota starts late and is the largest make. The semaphore fills both slots, but once the second-to-last make finishes, only Toyota remains.

**Paths:**

- **Sort makes by expected size (descending):** Start the largest makes first so they overlap with smaller ones. Toyota + Honda (the two largest) would start immediately and run in parallel. This is the biggest practical speedup available.
- **Increase `max_concurrent_makes`:** Going from 2 to 3 workers would help but increases load on CarMax.
- **Accept it:** 80 minutes is within the 90-minute timeout. If it is not causing workflow failures, the operational risk of optimizing is not zero.

---

## Design Issues

### 8. Global mutable state for cookies and start_time

**What happens:** `browser_cookies` and `start_time` are module-level globals mutated by `load_cookies()` and `main()` respectively. `get_headers()` reads `browser_cookies` implicitly. `log()` reads `start_time` implicitly.

**Why it matters:**

- It makes unit testing `get_headers()` and `log()` impossible without monkeypatching module state.
- It creates an invisible dependency — `get_headers()` looks like a pure function of `make` but is actually a function of `make` + hidden global state.
- If someone were to import `scraper` as a library (e.g., to scrape a single make from a REPL), they would need to call `load_cookies()` first or get silent partial results.

**Why it exists:** The scraper was written as a standalone script, not a library. Globals are the simplest thing that works when the entry point is `main()`.

**Path:** Move cookies into `ScraperConfig`. Pass `start_time` as a parameter to `log()` or make `log` a method on a `Scraper` class. This is a readability and testability improvement, not a correctness fix.

### 9. `scrape_result.json` records only failures

**What happens:** The scraper writes `{"failed_makes": [...]}` to `data/scrape_result.json` (line 267-270). There is no record of what succeeded — no per-make counts, no timestamps, no duration, no list of empty makes.

**Why it matters:** `generate_pr_summary.py` reads this file to determine workflow health. It knows what failed, but to know what succeeded it has to re-read every `output/<Make>.json` file and parse their counts. If the output files were corrupted or incomplete, the summary would not know.

**Downstream impact:** `generate_pr_summary.py` compensates by implementing its own `get_current_counts()` that re-reads every output file. This is duplicated work that the scraper could have provided directly.

**Path:** Expand `scrape_result.json` to include per-make status, scraped counts, and total duration. This gives downstream stages a single source of truth about the scrape without re-reading large files.

### 10. Retry re-scrapes from scratch

**What happens:** Lines 257-264 retry failed makes by calling `scrape_and_save()` again. This re-fetches every page from page 1, even if the original failure happened on page 50 of 60.

**Two failure modes to consider:**

- **Deterministic failures** (like Škoda encoding): Retrying does nothing. The same bug hits the same wall.
- **Transient failures** (like a 504 on one page): Retrying from scratch wastes all the successful page fetches from the first attempt.

**Why the current approach is still mostly right:** The REFACTOR_PLAN explicitly decided against page-level checkpointing (PR 2 non-goals). Full make-level retry is simple and fits the isolation model — each make is independent. The wasted requests on transient failures are an acceptable cost for simplicity.

**What would make it better without adding complexity:** Before retrying, check if the failure was deterministic (e.g., encoding error, 404, make not found). If so, skip the retry and record it as a permanent failure. Only retry on transient errors (timeouts, 5xx responses).

### 11. No error handling for missing config.json

**What happens:** `ScraperConfig.load()` opens `config.json` with no existence check and no error handling (line 95). If the file is missing, the user sees a raw `FileNotFoundError` traceback.

**Contrast with `load_makes()`:** Lines 30-31 explicitly check `REFERENCE_FILE.exists()` and print a friendly error before exiting. The config loading does not get the same treatment.

**Fix:** Add an existence check or a try/except with a clear message, matching the pattern already established by `load_makes()`.

---

## Structural Observations

### 12. The makes list contains non-CarMax brands

**Observation from the logs:** 5 makes returned 0 results (CUPRA, MAN, Peugeot, SEAT, comma) and 1 always fails (Škoda). These are all European/non-US brands from the opendbc reference that CarMax does not carry. Each one still costs a full API round-trip (~10s) to discover it is empty.

**Why they are in the list:** `load_makes()` pulls makes directly from `data/opendbc_ref.json`, which is generated from opendbc's `CARS.md`. Opendbc tracks global openpilot support, not US availability. The scraper does not filter for US-market makes.

**Paths:**

- **Maintain an exclusion list:** A `carmax_excluded_makes` list in `config.json` or the reference file. Simple, explicit, easy to update.
- **Cache empty results:** If a make returned 0 results on the last run, skip it next time unless the reference data changed. Adds statefulness and complexity.
- **Accept it:** 6 makes × 10 seconds = 1 minute of overhead on an 80-minute run. Operationally insignificant. The "Make not found" log lines are clear and the makes are reported in the summary. The only real cost is that Škoda forces a degraded run state every time due to the encoding bug.

**Recommendation:** Fix the Škoda encoding bug. After that, these makes are a non-issue — they return 0 results cleanly and the pipeline handles them correctly.

### 13. The scraper has one dependency: curl_cffi

**Observation:** The entire project depends on a single HTTP library — `curl_cffi` — for its core functionality. This is unusual. Most Python scrapers use `httpx`, `aiohttp`, or `requests`.

**Why curl_cffi:** CarMax likely has bot detection (Akamai, based on the `_abck` cookie). `curl_cffi` can impersonate real browser TLS fingerprints (`impersonate="chrome120"`), which is essential for getting past fingerprint-based bot detection. Standard Python HTTP libraries have recognizable TLS fingerprints that get blocked.

**Risk:** `curl_cffi` is a less mature library than `httpx` or `aiohttp`. It wraps libcurl via CFFI, which means:

- Debugging connection issues is harder (errors come from C, not Python)
- The `latin-1` encoding error on Škoda is a curl_cffi behavior, not a Python one
- Async support is newer and has had bugs in past versions

**Mitigation:** The dependency is pinned to `>=0.7.0` in `pyproject.toml`. The `impersonate` feature is the reason this library exists, and there is no realistic alternative that provides the same capability. This is a justified dependency.

### 14. Cookie expiration is invisible

**Observation:** Line 22 has a comment `# Expires 01/2027` next to `COOKIES_FILE`. But there is no runtime check for cookie expiration. If the cookies expire, the scraper silently gets partial inventory (mentioned on line 59: "partial inventory only").

**Why it matters:** The pipeline would produce a "healthy" run with half the expected inventory. `verify_counts.py` might catch it via HTML vs API count mismatches, but only if the mismatch exceeds the threshold (currently 3 cars, which it probably would).

**Path:** This is already covered by the existing count-check infrastructure. If cookies go stale, counts will diverge and the run will be marked degraded. No additional work needed — just be aware that cookie staleness manifests as count anomalies, not errors.

---

## Is this the simplest robust pythonic solution?

### What it gets right

1. **Scrape-by-make isolation.** Each make is independent. A failure in Toyota does not affect Honda. This is the single most important design decision and it is correct.

2. **Semaphore-based concurrency.** `asyncio.Semaphore` is the right primitive for limiting concurrent work in an async context. No thread pools, no process pools, no external task queue. Simple and correct.

3. **One file per make.** The output format (`output/<Make>.json`) is simple, inspectable, and naturally atomic — if the scraper crashes mid-make, the file either exists (complete from a previous run) or does not (incomplete from this run). There is no half-written state to worry about.

4. **Retry at the right granularity.** Make-level retry is the right abstraction. Page-level retry within a make exists (in `fetch_page`), and make-level retry exists (in `main`). These are the two natural failure boundaries.

5. **Minimal dependencies.** One library (`curl_cffi`), stdlib for everything else. No ORM, no task framework, no config library. This is maintainable.

### What makes it less than ideal

1. **Global state makes it a script, not a composable module.** You cannot import `scraper.py` and call `scrape_make("Toyota")` without first calling `load_cookies()` to set up hidden global state. This is the biggest gap between "script that works" and "robust component."

2. **No structured output metadata.** The scraper knows exactly what happened — which makes succeeded, which failed, how long each took, how many pages were fetched — but it only prints this to stdout. The only persisted metadata is `{"failed_makes": [...]}`. Every downstream stage has to re-derive scrape results from the output files.

3. **No data validation on API responses.** `response.json()` is trusted completely. If CarMax changes their API schema (renames `items` to `results`, changes `totalCount` to `total`), the scraper silently produces empty or broken output. A simple check like `if "items" not in data: raise` would fail fast instead of silently producing bad data.

4. **The make ordering is suboptimal for parallelism.** Alphabetical order means the two largest makes (Honda, Toyota) start far apart in the queue. Starting large makes first would reduce the long tail.

### Verdict

The scraper is 85% of the way to being the simplest robust version of itself. The core architecture — async, make-isolated, semaphore-limited, with retry — is sound. The remaining 15% is:

- Fix the encoding bug (5 minutes)
- Eliminate global state (30 minutes)
- Enrich scrape_result.json (15 minutes)
- Share one AsyncSession (15 minutes)
- Drop indent=2 on output (1 minute)

None of these require rethinking the design. They are all incremental improvements within the existing architecture.

---

## Prioritized recommendations

| # | Fix | Effort | Impact | Why |
|---|-----|--------|--------|-----|
| 1 | Fix Škoda Referer encoding | 1 line | Unblocks a make, fixes degraded state | Deterministic bug causing permanent failure |
| 2 | Track failed pages in output metadata | Small | Prevents silent data loss | Failed pages are invisible today |
| 3 | Enrich `scrape_result.json` with success data | Small | Simplifies all downstream stages | Eliminates re-reading output files |
| 4 | Share one AsyncSession across makes | Small | ~4 min faster, fewer connections | Correct pattern for connection reuse |
| 5 | Drop `indent=2` on output JSON | 1 line | ~3x smaller files, faster I/O and git | No human reads these files |
| 6 | Add config.json error handling | Small | Better DX on first setup | Matches existing pattern in load_makes |
| 7 | Sort makes by expected size descending | Small | Reduces long tail by ~15 min | Toyota+Honda overlap instead of sequencing |
| 8 | Move cookies/start_time off globals | Medium | Testable, importable scraper | Enables unit tests and REPL usage |

Items 1-6 are all backward-compatible, require no design decisions, and could each be a single commit. Items 7-8 are small refactors that improve the scraper without changing its contract with the rest of the pipeline.
