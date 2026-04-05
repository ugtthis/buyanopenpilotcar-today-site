#!/usr/bin/env python3

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
OPENPILOT_CARS_PATH = SCRIPT_DIR.parent / "data" / "openpilot_cars.json"
STORE_COORDS_PATH = SCRIPT_DIR.parent / "data" / "store-coords.json"
USER_AGENT = "openpilot-car-finder/1.0 (geocoding carmax stores)"
REQUEST_DELAY_SECONDS = 1.1


def load_json(path: Path) -> dict:
  return json.loads(path.read_text())


def save_json(path: Path, value: dict) -> None:
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
  stores = collect_stores_by_id(cars_data)
  print(f"Found {len(stores)} unique stores. Starting geocoding...")

  coords: dict[str, dict] = {}
  failed_stores: list[dict] = []
  done_count = 0

  for store in stores.values():
    try:
      geocoded = geocode_store(store)
      if geocoded is not None:
        coords[store["id"]] = geocoded
        done_count += 1
        if done_count % 20 == 0:
          print(f"  {done_count}/{len(stores)} done...")
      else:
        failed_stores.append(store)
        print(
          f'FAILED: storeId={store["id"]} name="{store["name"]}" '
          f'city="{store["city"]}" state="{store["state"]}"'
        )
    except Exception as error:  # noqa: BLE001 - keep full context in CLI output
      failed_stores.append(store)
      print(
        f'ERROR: storeId={store["id"]} name="{store["name"]}" '
        f'city="{store["city"]}" state="{store["state"]}" -> {error}'
      )

    time.sleep(REQUEST_DELAY_SECONDS)

  save_json(STORE_COORDS_PATH, sort_coords_by_store_id(coords))
  print(f"\nDone! {done_count} stores geocoded, {len(failed_stores)} failed.")

  if failed_stores:
    print(f"Failed stores: {failed_stores}")

  return 1 if failed_stores else 0


if __name__ == "__main__":
  raise SystemExit(main())
