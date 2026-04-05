#!/usr/bin/env python3

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
OPENPILOT_CARS_PATH = SCRIPT_DIR.parent / "data" / "openpilot_cars.json"
STORE_COORDS_PATH = SCRIPT_DIR.parent / "data" / "store-coords.json"


def load_json(path: Path) -> dict:
  return json.loads(path.read_text())


def collect_store_ids_from_cars(cars_data: dict) -> set[str]:
  store_ids = set()
  for entry in cars_data.get("entries", []):
    for available_year in entry.get("available_years", []):
      car = available_year.get("car")
      if car is None:
        continue
      store_ids.add(str(car["storeId"]))
  return store_ids


def find_missing_store_ids(store_ids: set[str], coords: dict) -> list[str]:
  missing = [store_id for store_id in store_ids if coords.get(store_id) is None]
  return sorted(missing, key=int)


def main() -> int:
  cars_data = load_json(OPENPILOT_CARS_PATH)
  coords = load_json(STORE_COORDS_PATH)

  store_ids = collect_store_ids_from_cars(cars_data)
  missing_ids = find_missing_store_ids(store_ids, coords)

  if missing_ids:
    print(
      f"\n❌ store-coords.json is missing {len(missing_ids)} store(s): {', '.join(missing_ids)}",
      file=sys.stderr,
    )
    print("Re-run: uv run python scripts/geocode_stores.py\n", file=sys.stderr)
    return 1

  print("✓ All stores accounted for in store-coords.json")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
