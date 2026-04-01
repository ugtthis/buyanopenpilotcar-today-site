#!/usr/bin/env python3
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path


OUTPUT_DIR = Path("output")
DATA_DIR = Path("data")


def merge_inventory(output_filename=None):
  if output_filename is None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    output_filename = f"{today}_full.jsonl"

  output_path = DATA_DIR / output_filename
  DATA_DIR.mkdir(exist_ok=True)

  json_files = sorted(OUTPUT_DIR.glob("*.json"))
  if not json_files:
    raise FileNotFoundError(f"No JSON files found in {OUTPUT_DIR}/")

  print(f"📋 Found {len(json_files)} JSON files to merge")
  print(f"📁 Output: {output_path}")
  print("=" * 70)

  total_cars = 0
  makes_processed = 0
  skipped = []

  with open(output_path, "w") as outfile:
    for json_file in json_files:
      try:
        with open(json_file) as f:
          data = json.load(f)

        is_valid = (
          isinstance(data, dict) and
          "listings" in data and
          isinstance(data["listings"], list)
        )

        if not is_valid:
          skipped.append(f"{json_file.name} (invalid structure)")
          continue

        listings = data["listings"]

        if not listings:
          skipped.append(f"{json_file.name} (empty)")
          continue

        make_name = data.get("make", json_file.stem)

        for car in listings:
          outfile.write(json.dumps(car) + "\n")

        total_cars += len(listings)
        makes_processed += 1
        print(f"  ✓ {make_name:<15} {len(listings):>6,} cars")

      except json.JSONDecodeError as e:
        skipped.append(f"{json_file.name} (JSON error: {e})")
      except Exception as e:
        skipped.append(f"{json_file.name} (error: {e})")

  print("=" * 70)
  print(f"✅ Complete: {makes_processed} makes, {total_cars:,} total cars")
  print(f"💾 Saved to: {output_path}")

  if skipped:
    print(f"\n⚠️  Skipped {len(skipped)} file(s):")
    for item in skipped:
      print(f"  - {item}")

  return output_path


if __name__ == "__main__":
  try:
    output_filename = None
    if len(sys.argv) > 2 and sys.argv[1] == "--output":
      output_filename = sys.argv[2]

    merge_inventory(output_filename)

  except KeyboardInterrupt:
    print("\n⚠️  Interrupted")
    sys.exit(1)
  except FileNotFoundError as e:
    print(f"\n❌ {e}")
    sys.exit(1)
  except Exception as e:
    print(f"\n❌ Error: {e}")
    traceback.print_exc()
    sys.exit(1)
