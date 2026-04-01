# Technical Debt & Cleanup TODO

Issues identified during code review. Not related to the HTML count check changes.

---

## scraper.py

### Dead code / redundant

- **`"save": "💾"` in log symbols dict** — never referenced anywhere in the codebase. Remove it.

- **`max_retries: int = 3` default on `fetch_page()`** — every call site passes `config.max_retries`
  explicitly, so this default is never used. Remove the default or remove the parameter and read
  from config directly.

- **`ScraperConfig` dataclass field defaults** — `load()` crashes with `FileNotFoundError` if
  `config.json` is missing, so the defaults are never reached. Either fix `load()` to fall back
  gracefully (`return cls() if not config_path.exists() else ...`) or remove the defaults to make
  the crash-on-missing behaviour explicit.

### `load_cookies()` design issues

- **Return value is discarded at the call site** — `load_cookies()` is declared `-> str` but called
  as `load_cookies()` with the return value thrown away. The real mechanism is the `browser_cookies`
  global side effect. Either remove the return value or remove the global and use the return value.

- **`# Build cookie string` comment** — narrates what the code obviously does. Remove it.
  The loop can also be simplified to a one-liner:
  ```python
  browser_cookies = "; ".join(f"{k}={v}" for k, v in cookies.items())
  ```

### `COUNT_MISMATCH_THRESHOLD = 3` — no explanation

- The value `3` is unexplained. Added a comment to `MIN_COMPLETENESS` explaining its rationale but
  `COUNT_MISMATCH_THRESHOLD` still has none. Should say why 3 (tolerate cars sold between the HTML
  fetch and the API call — normal churn on a busy make).

---

## config.json + ScraperConfig

- **Identical values in two places** — `config.json` and `ScraperConfig` defaults are mirrors of
  each other. This is fine if `config.json` is the source of truth, but the defaults on the
  dataclass imply otherwise. Decision needed: are the dataclass defaults intentional fallbacks or
  just stale copies?

---

## scripts/verify_counts.py

- **Dead URL redirect check** — line 42 checks `f"/cars/{quote(make.lower())}" not in str(response.url)`.
  CarMax never redirects (confirmed via terminal tests). Dead code. Remove it.

- **Two-regex `isSelected` check** — lines 47-48 use `.capitalize()` and `.upper()` separately.
  Should be a single `re.IGNORECASE` regex with `re.escape(make)` like the updated scraper version.

- **Duplicated `COUNT_MISMATCH_THRESHOLD = 3`** — same constant defined independently in both
  `scraper.py` and `verify_counts.py`. Drift risk.

- **Architectural question (Path A/B/C)** — see conversation context. The scraper now does the
  HTML vs API comparison inline (more accurately, tighter time window). `verify_counts.py` is
  partially redundant but still owns writing `count_check.json` which drives the PR health state.
  Decision needed before acting on this.

---

## Priority order (suggested)

1. Remove dead log symbol `"save"` — trivial, zero risk
2. Fix `# Build cookie string` comment + simplify cookie join — trivial
3. Remove `max_retries` default from `fetch_page()` — trivial
4. Add explanation comment to `COUNT_MISMATCH_THRESHOLD` — trivial
5. Fix `load_cookies()` return vs global design — small refactor
6. Fix `ScraperConfig.load()` fallback behaviour — small refactor
7. Fix `verify_counts.py` dead code and regex — small, isolated
8. Resolve `verify_counts.py` architectural question (Path A/B/C) — requires decision first
