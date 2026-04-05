#!/usr/bin/env python3

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


RAW_OUTPUT_DIR = Path("output")
DATA_DIR = Path("data")
PRODUCT_ARTIFACT = DATA_DIR / "openpilot_cars.json"
SCRAPE_RESULT_FILE = DATA_DIR / "scrape_result.json"
SCRAPE_COUNTS_FILE = DATA_DIR / "scrape_counts.json"
GEOCODE_RESULT_FILE = Path(".github/geocode-summary.json")
SUMMARY_PATH = Path(".github/pr-summary.md")
HEALTHY_STATE = "healthy"
DEGRADED_STATE = "degraded"
DEFAULT_PR_TITLE = "[bot] Scheduled listings update"
MANUAL_REVIEW_PR_TITLE = "[Needs Review] [bot] Scheduled listings update"


def load_json_file(path: Path):
  try:
    with path.open(encoding="utf-8") as handle:
      return json.load(handle)
  except (OSError, json.JSONDecodeError):
    return None


def get_latest_inventory_artifact():
  if not DATA_DIR.exists():
    return None
  return max(
    DATA_DIR.glob("*_full.jsonl"),
    key=lambda p: p.stat().st_mtime,
    default=None,
  )


def get_failed_makes():
  data = load_json_file(SCRAPE_RESULT_FILE)
  if not isinstance(data, dict):
    return []
  return data.get("failed_makes", [])


def get_count_mismatches():
  data = load_json_file(SCRAPE_RESULT_FILE)
  if not isinstance(data, dict):
    return []
  return data.get("count_mismatches", [])


def get_product_summary():
  data = load_json_file(PRODUCT_ARTIFACT)
  if not isinstance(data, dict):
    return None
  entries = data.get("entries", [])
  metrics = data.get("pipeline_metrics") or {}
  return {
    "total_variants": len(entries),
    "variants_with_matches": sum(1 for e in entries if e.get("available_years")),
    "matches_found": metrics.get("matches_found", 0),
    "cars_processed": metrics.get("cars_processed", 0),
    "match_rate": metrics.get("match_rate", 0),
  }


def get_geocode_summary():
  data = load_json_file(GEOCODE_RESULT_FILE)
  if not isinstance(data, dict):
    return None
  return data


def _read_git_file(file_path):
  try:
    result = subprocess.run(
      ["git", "show", f"origin/main:{file_path}"],
      capture_output=True,
      text=True,
      check=True,
    )
    return json.loads(result.stdout)
  except (subprocess.CalledProcessError, json.JSONDecodeError):
    return None


def get_previous_counts():
  data = _read_git_file(str(SCRAPE_COUNTS_FILE))
  if isinstance(data, dict):
    return data
  return {}


def get_current_counts():
  current = {}
  if not RAW_OUTPUT_DIR.exists():
    return {}

  for json_file in RAW_OUTPUT_DIR.glob("*.json"):
    data = load_json_file(json_file)
    if not isinstance(data, dict):
      continue

    make = data.get("make", json_file.stem)
    current[make] = data.get("scraped_count", 0)

  return current


def build_comparison_rows(previous_counts, current_counts):
  rows = []
  all_makes = set(current_counts) | set(previous_counts)

  for make in all_makes:
    previous = previous_counts.get(make, 0)
    current = current_counts.get(make, 0)
    rows.append(
      {
        "make": make,
        "previous": previous,
        "current": current,
        "change": current - previous,
      }
    )

  rows.sort(key=lambda row: row["current"], reverse=True)
  return rows


def append_workflow_state(lines, workflow_state, inventory_artifact, failed_makes, count_mismatches, missing):
  lines.append("## Workflow State")
  lines.append("")

  if workflow_state == HEALTHY_STATE:
    lines.append(f"**State:** `healthy` — `{inventory_artifact.name}`")
  else:
    lines.append("**State:** `degraded`")
    if failed_makes:
      lines.append("")
      lines.append(f"Failed makes: {', '.join(f'`{m}`' for m in failed_makes)}")
    if count_mismatches:
      lines.append("")
      mismatch_items = ", ".join(
        f"`{m['make']}` (html: {m['html_count']:,}, api: {m['api_count']:,})"
        for m in count_mismatches
      )
      lines.append(f"Count mismatches: {mismatch_items}")
    if missing:
      lines.append("")
      lines.append(f"Missing artifacts: {', '.join(missing)}")

  lines.append("")


def append_geocode_summary(lines, geocode_summary):
  if not geocode_summary:
    return

  status = geocode_summary.get("status")
  missing_count = geocode_summary.get("missing_count", 0)
  geocoded_count = geocode_summary.get("geocoded_count", 0)
  failed_count = geocode_summary.get("failed_count", 0)
  failed_store_ids = geocode_summary.get("failed_store_ids", [])

  lines.append("## Store Coordinates")
  lines.append("")

  if status == "no_missing":
    lines.append("No new stores needed geocoding.")
  else:
    lines.append(
      f"Missing stores detected: **{missing_count}** | "
      f"Geocoded: **{geocoded_count}** | "
      f"Failed: **{failed_count}**"
    )
    if failed_count:
      failed_text = ", ".join(f"`{store_id}`" for store_id in failed_store_ids)
      lines.append(f"Failed store IDs: {failed_text}")

  lines.append("")


def append_scrape_summary(lines, previous_counts, current_counts):
  total_previous = sum(previous_counts.values())
  total_current = sum(current_counts.values())
  total_change = total_current - total_previous

  lines.append("## Scrape Summary")
  lines.append("")
  lines.append(f"**Total Cars:** {total_current:,} ({total_change:+,} from previous)")
  lines.append("")
  lines.append("| Make | Previous | Current | Change |")
  lines.append("|------|----------|---------|--------|")

  for row in build_comparison_rows(previous_counts, current_counts):
    previous = f"{row['previous']:,}" if row["previous"] > 0 else "—"
    current = f"{row['current']:,}" if row["current"] > 0 else "—"
    change = f"{row['change']:+,}" if row["change"] != 0 else "—"
    lines.append(f"| **{row['make']}** | {previous} | {current} | {change} |")

  lines.append("")


def append_product_summary(lines, product_summary):
  if not product_summary:
    return
  lines.append("## Product Summary")
  lines.append("")
  lines.append(f"**Variants with inventory:** {product_summary['variants_with_matches']} of {product_summary['total_variants']}")
  lines.append(f"**Matched listings:** {product_summary['matches_found']:,} of {product_summary['cars_processed']:,} cars ({product_summary['match_rate']:.2%})")
  lines.append("")


def get_workflow_state(current_counts, inventory_artifact, product_exists, failed_makes, count_mismatches):
  if current_counts and inventory_artifact and product_exists and not failed_makes and not count_mismatches:
    return HEALTHY_STATE
  return DEGRADED_STATE


def save_scrape_counts(counts):
  DATA_DIR.mkdir(exist_ok=True)
  SCRAPE_COUNTS_FILE.write_text(json.dumps(counts, indent=2), encoding="utf-8")


def generate_summary():
  current_counts = get_current_counts()
  if current_counts:
    save_scrape_counts(current_counts)
  previous_counts = get_previous_counts()
  product_summary = get_product_summary()
  geocode_summary = get_geocode_summary()
  inventory_artifact = get_latest_inventory_artifact()
  product_artifact_exists = PRODUCT_ARTIFACT.exists()
  failed_makes = get_failed_makes()
  count_mismatches = get_count_mismatches()
  workflow_state = get_workflow_state(current_counts, inventory_artifact, product_artifact_exists, failed_makes, count_mismatches)
  missing = [
    label for condition, label in [
      (not current_counts, "scrape output"),
      (not inventory_artifact, "canonical matcher input"),
      (not product_artifact_exists, "canonical product output"),
    ]
    if condition
  ]

  lines = ["## CarMax Listings Update", ""]
  append_workflow_state(lines, workflow_state, inventory_artifact, failed_makes, count_mismatches, missing)
  append_geocode_summary(lines, geocode_summary)

  if current_counts:
    append_product_summary(lines, product_summary)
    append_scrape_summary(lines, previous_counts, current_counts)

  lines.append("---")
  lines.append(f"*Scraped at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*")
  return "\n".join(lines), workflow_state


def write_github_outputs(workflow_state):
  github_output = os.environ.get("GITHUB_OUTPUT")
  if not github_output:
    return

  with open(github_output, "a", encoding="utf-8") as handle:
    pr_title = DEFAULT_PR_TITLE if workflow_state == HEALTHY_STATE else MANUAL_REVIEW_PR_TITLE
    handle.write(f"workflow_state={workflow_state}\n")
    handle.write(f"pr_title={pr_title}\n")


def main():
  summary, workflow_state = generate_summary()
  SUMMARY_PATH.parent.mkdir(exist_ok=True)
  SUMMARY_PATH.write_text(summary, encoding="utf-8")
  write_github_outputs(workflow_state)

  print(f"Generated PR summary: {SUMMARY_PATH}")
  print(f"Workflow state: {workflow_state}")
  print("")
  print(summary)


if __name__ == "__main__":
  main()
