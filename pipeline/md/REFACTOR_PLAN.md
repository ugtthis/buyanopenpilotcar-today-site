# Refactor Plan

This document captures the current intended operating model for the CarMax to openpilot pipeline and proposes a PR roadmap that favors accuracy, simplicity, maintainability, and operational clarity.

The goal is not to make the system clever. The goal is to make it boring in the best way:

- easy to explain
- easy to debug
- hard to publish bad data
- clear about what is raw data vs curated product data

---

## Current Understanding

### What the pipeline is for

The real product output is `data/openpilot_cars.json`.

That file is the curated dataset the web experience should consume. It is the whole point of the pipeline:

- scrape CarMax inventory
- identify which listings are openpilot-compatible
- attach support level and confidence
- publish a clean user-facing data product

### Why scraping is done by make

Scraping by make isolates failures. If one make fails, the whole run does not have to restart from scratch.

This is a good design choice and should be preserved.

Desired behavior:

1. Scrape by make.
2. If a make fails, retry it once later in the same run.
3. If it still fails, keep processing other makes.
4. Mark the failed makes clearly in the workflow output and PR summary.
5. Allow manual resume only if more than one retry is needed.

### Why `merge_inventory.py` exists

`merge_inventory.py` is not just accidental glue. It exists because the scraper produces many per-make files, while `matcher.py` is intentionally designed to consume one flat streamed inventory artifact.

That single inventory artifact is `data/*_full.jsonl`.

JSONL is still a good fit here because:

- it is stream-friendly for `matcher.py`
- it avoids loading the full inventory into memory at once
- it is simple to inspect and debug
- it preserves a clean boundary between raw scraped inventory and curated matching logic

At this stage, keeping JSONL as the matcher input is the simplest and most robust choice.

### Where the current mismatch is

The pipeline currently computes more than it persists:

- `output/*.json` is committed in the workflow
- `data/*_full.jsonl` is generated but not persisted
- `data/openpilot_cars.json` is generated but not persisted

That is the main architectural mismatch in the current system.

If `openpilot_cars.json` is the canonical product artifact, the workflow should treat it that way.

---

## Design Principles

These should drive every refactor decision:

1. Accuracy over freshness.
2. Curated product output must not be published from an incomplete run.
3. Raw scrape artifacts and curated product artifacts should be clearly separated.
4. Every stage should have one clear responsibility.
5. Magic values and implicit contracts should be removed.
6. Validation should happen at data boundaries, not only at the end.
7. Healthy runs should be automated; degraded runs should be visible and reviewable.

---

## Recommended Operating Model

### Healthy run

A healthy run means:

- all makes scraped successfully
- no unrecovered make failures after the final retry pass
- no severe count anomalies
- matcher runs on complete inventory
- `openpilot_cars.json` is produced
- PR is eligible for auto-merge

### Degraded run

A degraded run means:

- one or more makes failed after retry
- or one or more makes show suspicious count anomalies
- or the reference-data validation failed

In a degraded run:

- do not publish curated product data as if it were complete
- do not auto-merge
- open a PR clearly marked for manual review
- include failed makes and anomaly details in the PR body
- keep enough artifacts to debug the run

### Matching policy

`matcher.py` should be treated as a completeness-sensitive stage.

Recommendation:

- block production matching when a make failed
- allow optional debug-only matcher runs on partial data if useful for investigation
- do not treat a partial `openpilot_cars.json` as publishable product output

Why:

- partial curated output is worse than delayed curated output
- the web experience should not silently undercount supported cars
- this keeps the product contract simple: published data is complete unless explicitly flagged otherwise

---

## Artifact Strategy

This is the cleanest mental model for the pipeline.

### Reference artifact

Produced by `markdown_to_json.py`

- Inputs: `CARS.md`, `package_keywords.json`
- Output: `data/opendbc_ref.json`
- Role: trusted normalized reference data

### Raw inventory artifact

Produced by scraper + merge stage

- Inputs: CarMax per-make scrape results
- Output: `data/*_full.jsonl`
- Role: complete raw inventory stream for matching

### Curated product artifact

Produced by matcher

- Inputs: `data/opendbc_ref.json`, `data/*_full.jsonl`
- Output: `data/openpilot_cars.json`
- Role: canonical user-facing data product for the web experience

This separation is clean, explainable, and data-engineering-friendly.

---

## Count Checks and Drift Detection

There is already a useful count-check concept in `check_counts.py`, but it is not currently wired into the main workflow.

That file compares:

- HTML make count
- API make count
- mismatch percentage

This is valuable because suspiciously low counts often mean:

- cookies are stale or missing
- CarMax changed API behavior
- a make page redirected unexpectedly
- scraping returned partial inventory

Recommendation:

- wire count checks into CI
- surface the results in the PR body
- use them as a gating signal for auto-merge

Suggested behavior:

- normal variation: warning only
- severe anomaly: manual review required

Exact thresholds can be decided later, but the concept belongs in the pipeline.

---

## Recommended PR Roadmap

Each PR should stay narrow, testable, and easy to review.

---

## [x] PR 1 — Define workflow states and canonical artifacts
**Risk:** Low | **Effort:** Small | **Priority:** Highest

### What

Clarify the pipeline contract in docs and workflow behavior:

- `openpilot_cars.json` is the canonical product output
- `data/*_full.jsonl` is the canonical matcher input
- per-make `output/*.json` remains the raw scrape output
- healthy runs are auto-mergeable
- degraded runs require manual review

### Why

Right now the system produces the right artifacts but the workflow does not clearly treat them according to their importance.

This PR aligns the code, docs, and workflow around the true product artifact.

### Files

- `README.md`
- workflow docs / pipeline docs
- `.github/workflows/scrape.yml`

### Non-goals

- no schema changes
- no matcher refactor yet
- no retry logic changes yet

---

## [x] PR 2 — Add explicit make-level retry and degraded-run behavior
**Risk:** Medium | **Effort:** Medium | **Priority:** Highest

### What

Implement the intended scrape control flow:

- initial scrape pass across all makes
- one final retry pass for failed makes within the same run
- record makes that still failed
- distinguish healthy vs degraded runs

### Why

This is core operating behavior, not polish. It directly supports the reason scraping is partitioned by make in the first place.

Without this, the pipeline does not fully express the failure model you want.

### Files

- `scraper.py`
- `.github/workflows/scrape.yml`
- PR summary generation if needed

### Non-goals

- no cross-run resume
- no page-level checkpointing
- no history storage redesign

---

## [x] PR 3 — Gate auto-merge on completeness and anomaly checks
**Risk:** Medium | **Effort:** Medium | **Priority:** High

### What

Introduce workflow gates so that:

- complete healthy runs can auto-merge
- failed makes block auto-merge
- severe count anomalies block auto-merge
- degraded runs still open a PR with clear diagnostics

### Why

This is how you preserve both automation and trust:

- normal runs stay hands-off
- suspicious runs become visible
- users do not receive incomplete curated product data by accident

### Files

- `.github/workflows/scrape.yml`
- `check_counts.py`
- `scripts/generate_pr_summary.py`

### Non-goals

- no redesign of the count-check algorithm yet
- no long-term history storage yet

---

## [x] PR 4 — Persist the product artifact that the web experience actually uses
**Risk:** Low | **Effort:** Small | **Priority:** High

### What

Update the workflow so the canonical product artifact is handled intentionally:

- commit `data/openpilot_cars.json` on healthy runs
- optionally upload `data/*_full.jsonl` as a debug artifact
- make the PR summary reflect the curated product status, not just raw scrape counts

### Why

If `openpilot_cars.json` is the real output, the pipeline should publish it intentionally. Right now it is generated but effectively discarded.

This is the most important artifact alignment change in the whole plan.

### Files

- `.github/workflows/scrape.yml`
- `scripts/generate_pr_summary.py`

### Non-goals

- no long-term historical analytics system
- no storage backend migration

---

## [x] PR 5 — Add validation at the reference-data boundary
**Risk:** Low | **Effort:** Small | **Priority:** High

### What

Add CI that runs `python markdown_to_json.py --validate-only` on changes to:

- `CARS.md`
- `package_keywords.json`

### Why

Reference data is an upstream dependency of the entire system. Catching drift early is much cheaper than discovering bad config during a scheduled production scrape.

This is classic boundary validation and belongs in a robust pipeline.

### Files

- `.github/workflows/` new or updated validation workflow

### Non-goals

- no change to matching logic
- no new confidence semantics

---

## [x] PR 3b — Delete `check_counts.py`

Deleted. `scripts/verify_counts.py` runs automatically in CI on every scrape and surfaces mismatches in the PR body. The manual tool's job is fully covered. No consolidation needed — the duplicate `get_html_count()` in `verify_counts.py` is the only copy now.

---

## [~] PR 6 — Remove magic configuration values and duplicate helpers
**Status:** Mostly obsolete | **Remaining effort:** Trivial

### Original scope (4 items) — re-evaluated

1. **Replace `["-"]` with `null` — Wrong.** On closer inspection, `["-"]` is a meaningful placeholder used exclusively by `medium` confidence entries in `package_keywords.json`. It means "we know the package requirement but haven't written keyword matching rules yet — match anyway for now." Replacing it with `null` would break the validation rules in `markdown_to_json.py`: `null` keywords are only valid for `extra_high` and `non_us` confidence levels (enforced at lines 131-135). Changing this would require rethinking the entire confidence/keyword contract, which is a design decision, not a cleanup.
2. **Deduplicate `variant_id` creation — Real but trivial.** The same f-string appears on lines 113 and 217 of `matcher.py`. Two occurrences of a one-liner in the same file. Low drift risk. Can fold into PR 8 if typed schemas make variant_id a computed property on a data class.
3. **Consolidate cookie loading into `utils.py` — Moot.** `check_counts.py` was the second consumer and is now deleted (PR 3b). `scraper.py` is the only file that loads cookies. Cookies are a scraper concern, not a shared utility.
4. **Remove `check_counts.py` references — Done** in PR 3b.

### Decision

Skip PR 6 as a standalone PR. The one real remaining item (variant_id) can fold into PR 8 (typed schemas). The `["-"]` placeholder is intentional and should stay until someone decides to redesign the confidence/keyword contract (see Open Decision #6).

---

## [x] PR 7 — Automate `CARS.md` updates from opendbc

Done. `.github/workflows/update-cars.yml` runs daily at 10am UTC (after opendbc generates at 8am UTC). `scripts/diff_cars.py` semantically diffs old vs new `CARS.md` using `parse_cars_from_markdown`, computes added/removed/support-level changes, writes a human-readable PR body to `.github/cars-sync-summary.md`, and emits `sync_state` to `GITHUB_OUTPUT`. Auto-merge fires only when `sync_state=healthy` (additions only, no removals, no support changes) AND PR5 validation passes on the PR. All three workflows now pin third-party actions to SHA and GitHub-owned actions to specific point releases (`v4.3.1`, `v4.6.2`) for reproducibility and easier debugging.

---

## [x] PR 8 — Add typed schemas for pipeline boundaries

Done in three focused sub-PRs:

**PR8a** — Extracted the duplicated `variant_id` f-string in `matcher.py` into a single `variant_id(entry: CarVariant) -> str` helper. Previously the same f-string appeared on two separate lines with no shared definition, a silent drift risk.

**PR8b** — Code hygiene, no behavior changes. Removed narrating comments and the redundant module docstring from `matcher.py` (kept the CLI usage docstring as user-facing docs). Modernized `Optional[dict]` to `dict | None` in `scraper.py` and dropped the now-unused `typing.Optional` import.

**PR8c** — Defined `CarVariant` as a `TypedDict` in `utils.py`, which both `markdown_to_json.py` and `matcher.py` already import from. Updated all three function signatures in `markdown_to_json.py` (`parse_car_from_table_row`, `enrich_with_package_info`, `parse_cars_from_markdown`) and two in `matcher.py` (`variant_id`, `check_entry_keywords`) to use `CarVariant`. No new module coupling introduced — both files already depended on `utils.py`.

Not addressed (deferred): `global` state in `scraper.py` (`start_time`, `browser_cookies`) and typed models for the scraper result and product entry shapes. These are lower priority and touch a larger surface area; reopen when a concrete debugging need arises.

---

## [x] PR 9 — Optional history and artifact retention improvements
**Status:** Done (absorbed into PR 4)

The main item — uploading `data/*_full.jsonl` as a GitHub Actions artifact — was completed in PR 4. The remaining idea ("possibly matched output snapshots") has no concrete use case yet. Better to reopen this when a real debugging need arises than to build it speculatively.

---

## Explicit Non-Recommendations For Now

These ideas may become useful later, but they are not the right next move:

- deleting `merge_inventory.py`
- replacing JSONL with a database
- auto-deriving all package keywords
- adding a large historical analytics system before the daily pipeline is stable

Why not now:

- they add complexity before the core operating model is fully enforced
- they solve secondary problems before primary correctness and workflow clarity are locked down

---

## Open Decisions

These do not block the roadmap, but they should be made explicit:

1. What count-drop threshold should trigger manual review?
2. Should degraded runs generate a debug-only partial `openpilot_cars.json`, or skip it entirely?
3. ~~Should `data/*_full.jsonl` be uploaded as a GitHub Actions artifact on every run, or only on degraded runs?~~ Resolved in PR 4: uploaded on every successful run (step skipped naturally when earlier steps fail).
4. What exact auto-merge rule should define a healthy run?
5. Should `output/*.json` (raw per-make scrape files) continue to be committed? They exist today to power the run-over-run comparison table in the PR summary, but they bloat the repo over time. The product artifact (`data/openpilot_cars.json`) is now committed — is the comparison table worth the storage cost?
6. Should the `["-"]` placeholder in `package_keywords.json` be redesigned? It works today but is semantically obscure. Any change requires rethinking the confidence/keyword validation contract — specifically, which confidence levels can have null vs placeholder vs real keywords.

---

## Summary

The simplest robust version of this pipeline is:

1. Build trusted reference data.
2. Scrape raw inventory by make with one retry pass.
3. Merge successful scrape results into one streamable JSONL.
4. Run matcher only on complete healthy inventory for publishable output.
5. Publish `openpilot_cars.json` as the canonical product artifact.
6. Auto-merge healthy runs.
7. Force manual review for degraded runs.

That keeps the pipeline simple, explicit, and production-friendly while preserving the right boundaries between raw data, matching logic, and user-facing output.
