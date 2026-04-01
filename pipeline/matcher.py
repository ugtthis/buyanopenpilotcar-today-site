#!/usr/bin/env python3
"""
Usage:
  python matcher.py                         # Normal run
  python matcher.py --dry-run               # Print stats without writing
  python matcher.py --input custom.jsonl    # Use a specific JSONL input
"""

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from utils import build_index_key, CarVariant


DATA_DIR = Path("data")
REFERENCE_FILE = DATA_DIR / "opendbc_ref.json"
OUTPUT_FILE = DATA_DIR / "openpilot_cars.json"


class MatchConfidence(Enum):
  EXTRA_HIGH = "extra_high"
  HIGH = "high"
  MEDIUM = "medium"
  LOW = "low"
  NON_US = "non_us"


KEYWORD_ALIASES = {
  "acc": ["adaptive cruise", "automated cruise", "acc"],
  "lkas": ["lane keep", "lane departure", "lane assist", "lkas"],
}


def variant_id(entry: CarVariant) -> str:
  return f"{entry['make']}_{entry['model_original']}_{entry.get('package_key_used', 'default')}"


def load_reference_data() -> dict:
  if not REFERENCE_FILE.exists():
    print(f"❌ Error: {REFERENCE_FILE} not found!", flush=True)
    sys.exit(1)

  with open(REFERENCE_FILE) as f:
    return json.load(f)


def index_cars_by_key(reference_data: dict) -> dict:
  index = defaultdict(list)

  for reference_entry in reference_data["cars"]:
    if reference_entry.get("match_confidence") == MatchConfidence.NON_US.value:
      continue
    index[reference_entry["index_key"]].append(reference_entry)

  return index


def process_inventory(jsonl_path: Path, reference_index: dict) -> tuple[dict, dict]:
  cheapest = {}
  metrics = {
    "total_lines": 0,
    "cars_processed": 0,
    "json_parse_errors": 0,
    "matches_found": 0,
    "no_match_reasons": defaultdict(int)
  }

  print(f"📖 Reading inventory from {jsonl_path}", flush=True)

  with open(jsonl_path) as f:
    for line_num, line in enumerate(f, 1):
      metrics["total_lines"] += 1

      if line_num % 10000 == 0:
        print(f"  Processed {line_num:,} cars ({metrics['matches_found']:,} matches)...", flush=True)

      try:
        car = json.loads(line)
        metrics["cars_processed"] += 1
      except json.JSONDecodeError as e:
        metrics["json_parse_errors"] += 1
        print(f"  ⚠️  Line {line_num}: Invalid JSON - {e}", flush=True)
        continue

      matches = match_car(car, reference_index)

      if matches:
        metrics["matches_found"] += len(matches)
      else:
        # Track why cars didn't match for drift visibility
        if not car.get("make") or not car.get("model"):
          metrics["no_match_reasons"]["missing_make_or_model"] += 1
        else:
          index_key = build_index_key(car.get("make", ""), car.get("model", ""))
          reference_entries = reference_index.get(index_key, [])
          if not reference_entries:
            metrics["no_match_reasons"]["unsupported_models"] += 1
          else:
            car_year = car.get("year")
            year_matches_any_entry = any(
              car_year in reference_entry["years"]
              for reference_entry in reference_entries
            )
            if year_matches_any_entry:
              metrics["no_match_reasons"]["keyword_mismatch"] += 1
            else:
              metrics["no_match_reasons"]["year_mismatch"] += 1

      for entry, year, status in matches:
        key = (variant_id(entry), year)

        car_price = car.get("basePrice", float("inf"))
        car_mileage = car.get("mileage", float("inf"))

        if key not in cheapest:
          cheapest[key] = (car, status)
        else:
          current_car, current_status = cheapest[key]
          current_price = current_car.get("basePrice", float("inf"))
          current_mileage = current_car.get("mileage", float("inf"))

          if (car_price < current_price or
              (car_price == current_price and car_mileage < current_mileage)):
            cheapest[key] = (car, status)

  # Convert defaultdict to regular dict for JSON serialization
  metrics["no_match_reasons"] = dict(metrics["no_match_reasons"])

  print(f"✅ Processed {metrics['cars_processed']:,} cars, found {metrics['matches_found']:,} matches", flush=True)

  return cheapest, metrics


def match_car(car: dict, reference_index: dict) -> list[tuple]:
  matches = []

  car_make = car.get("make", "")
  car_model = car.get("model", "")
  car_year = car.get("year")

  if not car_make or not car_model or not car_year:
    return matches

  index_key = build_index_key(car_make, car_model)
  reference_entries = reference_index.get(index_key, [])

  for reference_entry in reference_entries:
    if car_year not in reference_entry["years"]:
      continue

    matched, confidence = check_entry_keywords(car, reference_entry)

    if matched:
      matches.append((reference_entry, car_year, confidence))

  return matches


def check_entry_keywords(car: dict, reference_entry: CarVariant) -> tuple[bool, MatchConfidence]:
  confidence = MatchConfidence(reference_entry["match_confidence"])
  keywords = reference_entry.get("matching_keywords")

  if keywords is None or keywords == ["-"]:
    return True, confidence

  return keywords_match(car, keywords), confidence


def keywords_match(car: dict, keywords: list[str]) -> bool:
  car_features = extract_all_feature_text(car)
  return all(keyword_appears_in(keyword, car_features) for keyword in keywords)


def extract_all_feature_text(car: dict) -> str:
  features_list = car.get("features", [])
  highlighted_features = car.get("highlightedFeatures", "")
  combined = f"{' '.join(features_list)} {highlighted_features}"
  return combined.lower()


def keyword_appears_in(keyword: str, text: str) -> bool:
  keyword_lowercase = keyword.lower()
  possible_patterns = KEYWORD_ALIASES.get(keyword_lowercase, [keyword_lowercase])
  return any(pattern in text for pattern in possible_patterns)


def get_latest_inventory_file() -> Path:
  if "--input" in sys.argv:
    idx = sys.argv.index("--input")
    if idx + 1 < len(sys.argv):
      path = Path(sys.argv[idx + 1])
      if not path.exists():
        print(f"❌ Error: {path} not found!", flush=True)
        sys.exit(1)
      return path

  jsonl_files = sorted(DATA_DIR.glob("*_full.jsonl"), reverse=True)
  if not jsonl_files:
    print("❌ No JSONL inventory file found!", flush=True)
    print("   Run merge_inventory.py first or specify --input <file>", flush=True)
    sys.exit(1)

  return jsonl_files[0]


def build_output(reference_data: dict, cheapest: dict, metrics: dict) -> dict:
  entries = []
  warnings = []

  vin_to_variants = defaultdict(list)

  for reference_entry in reference_data["cars"]:
    available_years = []
    unavailable_years = []

    for year in reference_entry["years"]:
      key = (variant_id(reference_entry), year)

      if key in cheapest:
        car, confidence = cheapest[key]
        vin = car.get("vin", "unknown")

        vin_to_variants[vin].append((reference_entry["make"], reference_entry["model_original"], year))

        available_years.append({
          "year": year,
          "match_confidence": confidence.value,
          "car": car
        })
      else:
        unavailable_years.append(year)

    output_entry = {
      "make": reference_entry["make"],
      "model": reference_entry["model"],
      "model_original": reference_entry["model_original"],
      "package_requirements": reference_entry.get("package_requirements", "Unknown"),
      "package_key_used": reference_entry.get("package_key_used"),
      "matching_keywords": reference_entry.get("matching_keywords"),
      "variant_info": reference_entry.get("variant_info"),
      "support_level": reference_entry.get("support_level", {}),
      "available_years": available_years,
      "unavailable_years": unavailable_years
    }

    entries.append(output_entry)

  for vin, variants in vin_to_variants.items():
    if len(variants) > 1:
      variant_strs = [f"{make} {model} {year}" for make, model, year in variants]
      warning = f"VIN {vin} is the cheapest car for {len(variants)} variants: {', '.join(variant_strs)}"
      warnings.append(warning)

  match_rate = metrics["matches_found"] / metrics["cars_processed"] if metrics["cars_processed"] > 0 else 0

  return {
    "entries": entries,
    "warnings": warnings,
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "pipeline_metrics": {
      "total_lines": metrics["total_lines"],
      "cars_processed": metrics["cars_processed"],
      "json_parse_errors": metrics["json_parse_errors"],
      "matches_found": metrics["matches_found"],
      "match_rate": round(match_rate, 4),
      "no_match_breakdown": metrics["no_match_reasons"]
    }
  }


def main():
  dry_run = "--dry-run" in sys.argv
  jsonl_path = get_latest_inventory_file()

  print("=" * 70, flush=True)
  print("🚗 Openpilot Car Matcher", flush=True)
  print("=" * 70, flush=True)

  print(f"📋 Loading reference data from {REFERENCE_FILE}", flush=True)
  reference_data = load_reference_data()
  print(f"✅ Loaded {len(reference_data['cars'])} reference variants", flush=True)

  print("🔍 Building lookup index...", flush=True)
  reference_index = index_cars_by_key(reference_data)
  print(f"✅ Indexed {len(reference_index)} unique make/model combinations", flush=True)

  print("=" * 70, flush=True)

  cheapest, metrics = process_inventory(jsonl_path, reference_index)

  print("=" * 70, flush=True)
  print(f"📊 Found cheapest cars for {len(cheapest)} (variant, year) combinations", flush=True)
  print(f"📈 Match rate: {metrics['matches_found'] / metrics['cars_processed']:.2%} ({metrics['matches_found']:,} / {metrics['cars_processed']:,})", flush=True)
  if metrics["json_parse_errors"] > 0:
    print(f"⚠️  {metrics['json_parse_errors']} JSON parse errors", flush=True)

  print("🔨 Building output structure...", flush=True)
  output = build_output(reference_data, cheapest, metrics)

  print(f"✅ Generated {len(output['entries'])} variant entries", flush=True)
  if output["warnings"]:
    print(f"⚠️  {len(output['warnings'])} warnings (duplicate VINs)", flush=True)

  if dry_run:
    print("=" * 70, flush=True)
    print("🔍 DRY RUN - Not writing output file", flush=True)
  else:
    print("=" * 70, flush=True)
    print(f"💾 Writing output to {OUTPUT_FILE}", flush=True)
    with open(OUTPUT_FILE, "w") as f:
      json.dump(output, f, indent=2)
    print(f"✅ Complete! Output saved to {OUTPUT_FILE}", flush=True)


if __name__ == "__main__":
  try:
    main()
  except KeyboardInterrupt:
    print("\n⚠️  Interrupted", flush=True)
    sys.exit(1)
  except Exception as e:
    print(f"\n❌ Error: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)
