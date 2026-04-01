#!/usr/bin/env python3
import asyncio
import json
import os
import re
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from math import ceil
from pathlib import Path
from urllib.parse import quote

from curl_cffi.requests import AsyncSession


MAX_RESULTS_PER_PAGE = 100  # CarMax API limit
COUNT_MISMATCH_THRESHOLD = 3  # tolerate normal churn between SSR fetch and API call (cars sold in between)
MIN_COMPLETENESS = 0.95  # tolerate loss from failed API pages before warning
BASE_URL = "https://www.carmax.com/cars/api/search/run"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
OUTPUT_DIR = Path("output")
DATA_DIR = Path("data")
SCRAPE_RESULT_FILE = DATA_DIR / "scrape_result.json"
COOKIES_FILE = Path("cookies.json") # Expires 01/2027
REFERENCE_FILE = DATA_DIR / "opendbc_ref.json"

start_time = None
browser_cookies = ""


def load_makes() -> list[str]:
  if not REFERENCE_FILE.exists():
    print(f"❌ {REFERENCE_FILE} not found", flush=True)
    sys.exit(1)

  try:
    with open(REFERENCE_FILE) as f:
      data = json.load(f)
    makes = list(data["stats"]["total_by_make"].keys())
    print(f"✅ Loaded {len(makes)} makes", flush=True)
    return makes
  except Exception as e:
    print(f"❌ Loading makes: {e}", flush=True)
    sys.exit(1)


def load_cookies() -> str:
  global browser_cookies

  # Try environment variables first (for GitHub Actions)
  abck = os.getenv('ABCK_COOKIE')
  kmx = os.getenv('KMXVISITOR_COOKIE')

  if abck and kmx:
    browser_cookies = f"_abck={abck}; KmxVisitor_0={kmx}"
    print("✅ Cookies from env", flush=True)
    return browser_cookies

  # Fallback to cookies.json (for local testing)
  if not COOKIES_FILE.exists():
    print("⚠️  No cookies.json - partial inventory only", flush=True)
    return ""

  try:
    with open(COOKIES_FILE) as f:
      cookies = json.load(f)

    # Build cookie string
    cookie_parts = []
    for name, value in cookies.items():
      cookie_parts.append(f"{name}={value}")

    browser_cookies = "; ".join(cookie_parts)
    print(f"✅ Cookies from {COOKIES_FILE.name}", flush=True)
    return browser_cookies
  except Exception as e:
    print(f"⚠️  Loading cookies: {e}", flush=True)
    return ""


def log(make: str, msg: str, level: str = "info"):
  elapsed = f"[{time.time() - start_time:6.1f}s] " if start_time else ""
  symbols = {"info": "  ", "start": "🚗", "done": "✅", "warn": "⚠️ ", "error": "❌", "save": "💾"}
  symbol = symbols.get(level, "  ")
  print(f"{elapsed}{symbol} [{make:<12}] {msg}", flush=True)


@dataclass
class ScraperConfig:
  delay_seconds: float = 1.5
  delay_jitter: float = 0.8
  max_retries: int = 3
  max_concurrent_makes: int = 2

  @classmethod
  def load(cls, config_path: Path = Path("config.json")) -> "ScraperConfig":
    with open(config_path) as f:
      data = json.load(f)
    return cls(**data)


def get_headers(make: str) -> dict:
  headers = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": f"https://www.carmax.com/cars/{quote(make)}",
    "Origin": "https://www.carmax.com",
    "User-Agent": USER_AGENT,
  }

  # Without cookies, the API returns partial inventory(i.e. Porsche)
  if browser_cookies:
    headers["Cookie"] = browser_cookies

  return headers


async def fetch_page(
  session: AsyncSession,
  make: str,
  skip: int,
  max_retries: int = 3
) -> dict | None:
  uri = f"/cars/{quote(make)}"
  params = {
    "uri": uri,
    "skip": skip,
    "take": MAX_RESULTS_PER_PAGE,
    "shipping": -1,
    "sort": "price-desc"
  }

  for attempt in range(max_retries):
    try:
      response = await session.get(
        BASE_URL,
        params=params,
        headers=get_headers(make),
        impersonate="chrome120",
        timeout=30
      )

      if response.status_code == 200:
        return response.json()
      else:
        log(make, f"HTTP {response.status_code} (skip={skip})", "warn")

    except Exception as e:
      log(make, f"{e} (skip={skip})", "warn")

    # Wait before retry (exponential backoff)
    if attempt < max_retries - 1:
      wait_time = 2 ** attempt
      log(make, f"Retrying in {wait_time}s...", "warn")
      await asyncio.sleep(wait_time)

  log(make, f"Failed after {max_retries} attempts (skip={skip})", "error")
  return None


async def check_make_exists(session: AsyncSession, make: str) -> int | None:
  url = f"https://www.carmax.com/cars/{quote(make.lower())}"

  try:
    response = await session.get(
      url,
      headers={"User-Agent": USER_AGENT},
      impersonate="chrome120",
      timeout=30,
    )

    if response.status_code != 200:
      return None

    html = response.text

    # CarMax serves 200 for unknown makes but shows all 83k cars unfiltered
    make_filter_active = re.search(rf'{{"value":"{re.escape(make)}"[^}}]*"isSelected":true', html, re.IGNORECASE)
    if not make_filter_active:
      return None

    match = re.search(r'const totalCount = (\d+);', html) or re.search(r'"totalCount":(\d+)', html)
    return int(match.group(1)) if match else None

  except Exception:
    return None


def empty_result(make: str) -> dict:
  return {"make": make, "total_count": 0, "scraped_count": 0, "scraped_at": datetime.now(timezone.utc).isoformat(), "listings": []}


async def scrape_make(config: ScraperConfig, make: str) -> dict:
  log(make, "Starting...", "start")

  async with AsyncSession() as session:
    html_count = await check_make_exists(session, make)  # SSR count is independent of the API — mismatch = API blocked or throttled

    if html_count is None:
      log(make, "Not on CarMax", "warn")
      return empty_result(make)

    log(make, f"HTML: {html_count:,} cars")

    first_page = await fetch_page(session, make, 0, config.max_retries)

    if not first_page:
      log(make, "API request failed", "error")
      raise RuntimeError(f"{make}: API request failed")

    api_count = first_page.get("totalCount", 0)
    total_pages = ceil(api_count / MAX_RESULTS_PER_PAGE)
    diff = api_count - html_count

    if abs(diff) > COUNT_MISMATCH_THRESHOLD:
      log(make, f"Count mismatch: HTML={html_count:,} API={api_count:,} ({diff:+,})", "warn")
    else:
      log(make, f"API: {api_count:,} ({total_pages} pages) ✅")

    items = [item for item in first_page.get("items", []) if item.get("make", "").lower() == make.lower()]

    for page_num in range(1, total_pages):
      skip = page_num * MAX_RESULTS_PER_PAGE
      jitter = random.uniform(-config.delay_jitter, config.delay_jitter)
      delay = max(0.3, config.delay_seconds + jitter)
      await asyncio.sleep(delay)

      page_data = await fetch_page(session, make, skip, config.max_retries)

      if page_data and "items" in page_data:
        matching_items = [item for item in page_data["items"] if item.get("make", "").lower() == make.lower()]
        items.extend(matching_items)

        if page_num % 5 == 0 or page_num == total_pages - 1:
          log(make, f"Page {page_num + 1}/{total_pages} ({len(items):,} cars so far)")
      else:
        log(make, f"Page {page_num + 1}/{total_pages} failed", "warn")

    if len(items) < api_count * MIN_COMPLETENESS:
      log(make, f"Expected {api_count:,} but got {len(items):,}", "warn")

    log(make, f"Done! {len(items):,} cars scraped", "done")

    return {
      "make": make,
      "total_count": api_count,
      "html_count": html_count,
      "scraped_count": len(items),
      "scraped_at": datetime.now(timezone.utc).isoformat(),
      "listings": items
    }


def save_results(make: str, data: dict) -> Path:
  OUTPUT_DIR.mkdir(exist_ok=True)
  output_path = OUTPUT_DIR / f"{make}.json"

  with open(output_path, "w") as f:
    json.dump(data, f, indent=2)

  return output_path


async def main():
  global start_time

  print("🚗 CarMax Scraper", flush=True)

  makes = load_makes()
  load_cookies()

  config = ScraperConfig.load()
  start_time = time.time()

  print(f"Scraping {len(makes)} makes with {config.max_concurrent_makes} workers\n", flush=True)

  semaphore = asyncio.Semaphore(config.max_concurrent_makes)

  async def scrape_and_save(make: str) -> dict:
    async with semaphore:
      result = await scrape_make(config, make)
      save_results(make, result)
      return result

  all_successful = []
  failed_makes = []
  count_mismatches = []

  try:
    initial_results = await asyncio.gather(
      *[scrape_and_save(make) for make in makes],
      return_exceptions=True,
    )

    all_successful = [r for r in initial_results if isinstance(r, dict)]
    failed_makes = [make for make, r in zip(makes, initial_results) if isinstance(r, Exception)]

    if failed_makes:
      print(f"\n⚠️  Retrying {len(failed_makes)} makes: {', '.join(failed_makes)}", flush=True)
      retry_results = await asyncio.gather(
        *[scrape_and_save(make) for make in failed_makes],
        return_exceptions=True,
      )
      all_successful.extend(r for r in retry_results if isinstance(r, dict))
      failed_makes = [make for make, r in zip(failed_makes, retry_results) if isinstance(r, Exception)]

    count_mismatches = [
      {"make": r["make"], "html_count": r["html_count"], "api_count": r["total_count"]}
      for r in all_successful
      if r.get("html_count") and abs(r["total_count"] - r["html_count"]) > COUNT_MISMATCH_THRESHOLD
    ]

  finally:
    DATA_DIR.mkdir(exist_ok=True)
    SCRAPE_RESULT_FILE.write_text(
      json.dumps({"failed_makes": failed_makes, "count_mismatches": count_mismatches}),
      encoding="utf-8",
    )

  if failed_makes:
    print(f"\n❌ {len(failed_makes)} makes still failed: {', '.join(failed_makes)}", flush=True)

  empty_makes = [r["make"] for r in all_successful if r["scraped_count"] == 0]
  if empty_makes:
    print(f"\nℹ️  {len(empty_makes)} makes with 0 results: {', '.join(empty_makes)}", flush=True)

  total_cars = sum(r["scraped_count"] for r in all_successful)
  elapsed = time.time() - start_time
  print(f"\n✅ Complete: {total_cars:,} cars in {elapsed/60:.1f} min", flush=True)


if __name__ == "__main__":
  try:
    asyncio.run(main())
  except KeyboardInterrupt:
    print("\n⚠️  Interrupted", flush=True)
    sys.exit(1)
  except Exception as e:
    print(f"\n❌ Fatal: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)
