import json

import scripts.validate_store_coords as validate_script
from scripts.validate_store_coords import (
  collect_store_ids_from_cars,
  find_missing_store_ids,
  main,
)


def test_collect_store_ids_from_cars_extracts_ids():
  cars_data = {
    "entries": [
      {
        "available_years": [
          {"car": {"storeId": 6154}},
          {"car": {"storeId": 7298}},
          {"car": None},
        ]
      },
      {
        "available_years": [
          {"car": {"storeId": 6154}},
        ]
      },
    ]
  }

  assert collect_store_ids_from_cars(cars_data) == {"6154", "7298"}


def test_find_missing_store_ids_returns_sorted_numeric_ids():
  store_ids = {"7298", "6056", "6154"}
  coords = {"7298": {"lat": 0.0, "lng": 0.0}}

  assert find_missing_store_ids(store_ids, coords) == ["6056", "6154"]


def test_main_returns_1_when_missing_ids(tmp_path, monkeypatch, capsys):
  cars_path = tmp_path / "openpilot_cars.json"
  coords_path = tmp_path / "store-coords.json"

  cars_path.write_text(
    json.dumps(
      {
        "entries": [
          {"available_years": [{"car": {"storeId": 6154}}, {"car": {"storeId": 7298}}]},
        ]
      }
    )
  )
  coords_path.write_text(json.dumps({"7298": {"lat": 1.0, "lng": 2.0}}))

  monkeypatch.setattr(validate_script, "OPENPILOT_CARS_PATH", cars_path)
  monkeypatch.setattr(validate_script, "STORE_COORDS_PATH", coords_path)

  exit_code = main()

  captured = capsys.readouterr()
  assert exit_code == 1
  assert "missing 1 store(s): 6154" in captured.err
  assert "geocode_stores.py" in captured.err


def test_main_returns_0_when_all_ids_present(tmp_path, monkeypatch, capsys):
  cars_path = tmp_path / "openpilot_cars.json"
  coords_path = tmp_path / "store-coords.json"

  cars_path.write_text(
    json.dumps(
      {
        "entries": [
          {"available_years": [{"car": {"storeId": 6154}}, {"car": {"storeId": 7298}}]},
        ]
      }
    )
  )
  coords_path.write_text(
    json.dumps(
      {
        "6154": {"lat": 1.0, "lng": 2.0},
        "7298": {"lat": 3.0, "lng": 4.0},
      }
    )
  )

  monkeypatch.setattr(validate_script, "OPENPILOT_CARS_PATH", cars_path)
  monkeypatch.setattr(validate_script, "STORE_COORDS_PATH", coords_path)

  exit_code = main()

  captured = capsys.readouterr()
  assert exit_code == 0
  assert "All stores accounted for" in captured.out
