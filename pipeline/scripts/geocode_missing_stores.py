#!/usr/bin/env python3

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
OPENPILOT_CARS_PATH = SCRIPT_DIR.parent / "data" / "openpilot_cars.json"
STORE_COORDS_PATH = SCRIPT_DIR.parent / "data" / "store-coords.json"
GEOCODE_RESULT_PATH = SCRIPT_DIR.parent / ".github" / "geocode-summary.json"
USER_AGENT = "openpilot-car-finder/1.0 (incremental geocoding carmax stores)"
REQUEST_DELAY_SECONDS = 1.1


def load_json(path: Path) -> dict:
  return json.loads(path.read_text())


def save_json(path: Path, value: dict) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(value, indent=2) + "\n")


def collect_stores_by_id(cars_data: dict) -> dict[str, dict]:
  stores_by_id: dict[str, dict] = {}
  for entry in cars_data.get("entries", []):
    for available_year in entry.get("available_years", []):
      car = available_year.get("car")
      if car is None:
        continue

      store_id = str(car["storeId"])
      if store_id in stores_by_id:
        continue

      stores_by_id[store_id] = {
        "id": store_id,
        "name": car.get("storeName", ""),
        "city": car.get("storeCity", ""),
        "state": car.get("state", ""),
      }
  return stores_by_id


def find_missing_stores(stores_by_id: dict[str, dict], existing_coords: dict) -> list[dict]:
  missing = [store for store_id, store in stores_by_id.items() if existing_coords.get(store_id) is None]
  return sorted(missing, key=lambda store: int(store["id"]))


def build_search_url(query: str) -> str:
  encoded_query = urllib.parse.quote(query, safe="")
  return f"https://nominatim.openstreetmap.org/search?q={encoded_query}&format=json&limit=1"


def fetch_first_geocode_result(query: str) -> dict | None:
  request = urllib.request.Request(
    build_search_url(query),
    headers={"User-Agent": USER_AGENT},
  )
  with urllib.request.urlopen(request) as response:
    if response.status != 200:
      raise RuntimeError(f"HTTP {response.status} for query: {query}")
    results = json.load(response)
  return results[0] if results else None


def to_store_coords(geocode_result: dict) -> dict:
  return {
    "lat": float(geocode_result["lat"]),
    "lng": float(geocode_result["lon"]),
  }


def geocode_store(store: dict) -> dict | None:
  primary_query = f"CarMax {store['city']}, {store['state']}"
  primary_result = fetch_first_geocode_result(primary_query)
  if primary_result is not None:
    return to_store_coords(primary_result)

  time.sleep(REQUEST_DELAY_SECONDS)
  fallback_query = f"{store['city']}, {store['state']}"
  fallback_result = fetch_first_geocode_result(fallback_query)
  return to_store_coords(fallback_result) if fallback_result is not None else None


def sort_coords_by_store_id(coords: dict) -> dict:
  return dict(sorted(coords.items(), key=lambda item: int(item[0])))


def main() -> int:
  cars_data = load_json(OPENPILOT_CARS_PATH)
  existing_coords = load_json(STORE_COORDS_PATH)

  stores_by_id = collect_stores_by_id(cars_data)
  missing_stores = find_missing_stores(stores_by_id, existing_coords)

  if not missing_stores:
    print("No missing store coordinates. Nothing to geocode.")
    save_json(
      GEOCODE_RESULT_PATH,
      {
        "status": "no_missing",
        "missing_count": 0,
        "geocoded_count": 0,
        "failed_count": 0,
        "failed_store_ids": [],
      },
    )
    return 0

  print(f"Found {len(missing_stores)} missing store(s). Starting incremental geocoding...")

  next_coords = dict(existing_coords)
  failed_stores: list[dict] = []
  geocoded_count = 0

  total_missing = len(missing_stores)
  for index, store in enumerate(missing_stores, start=1):
    print(
      f'[{index}/{total_missing}] Geocoding storeId={store["id"]} '
      f'({store["city"]}, {store["state"]})...',
      flush=True,
    )
    try:
      coords = geocode_store(store)
      if coords is not None:
        next_coords[store["id"]] = coords
        geocoded_count += 1
        print(f'[{index}/{total_missing}] OK storeId={store["id"]}', flush=True)
      else:
        failed_stores.append(store)
        print(
          f'[{index}/{total_missing}] FAILED: storeId={store["id"]} '
          f'name="{store["name"]}" city="{store["city"]}" state="{store["state"]}"',
          flush=True,
        )
    except Exception as error:  # noqa: BLE001 - keep full context in CLI output
      failed_stores.append(store)
      print(
        f'[{index}/{total_missing}] ERROR: storeId={store["id"]} '
        f'name="{store["name"]}" city="{store["city"]}" state="{store["state"]}" -> {error}',
        flush=True,
      )

    time.sleep(REQUEST_DELAY_SECONDS)

  save_json(STORE_COORDS_PATH, sort_coords_by_store_id(next_coords))
  save_json(
    GEOCODE_RESULT_PATH,
    {
      "status": "failed" if failed_stores else "ok",
      "missing_count": total_missing,
      "geocoded_count": geocoded_count,
      "failed_count": len(failed_stores),
      "failed_store_ids": [store["id"] for store in failed_stores],
    },
  )
  print(f"Geocoded {geocoded_count} new store(s), {len(failed_stores)} failed.")

  return 1 if failed_stores else 0


if __name__ == "__main__":
  raise SystemExit(main())
