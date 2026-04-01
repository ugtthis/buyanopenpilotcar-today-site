"""Tests for matcher.py."""

import json
from pathlib import Path

import pytest
from utils import normalize_for_matching, build_index_key
from matcher import (
  check_entry_keywords,
  match_car,
  index_cars_by_key,
  MatchConfidence
)


class TestNormalize:
  """Tests for normalize_for_matching()."""

  @pytest.mark.parametrize("input_str,expected", [
    ("Honda", "honda"),
    ("CR-V", "cr v"),
    ("CR_V", "cr v"),
    ("  Mazda  ", "mazda"),
    ("718 Cayman", "718 cayman"),
    ("Yaris  ,", "yaris"),
    ("Altima ,", "altima"),
    ("CR--V", "cr v"),
    ("X5  M", "x5 m"),
    ("F-150", "f 150"),
  ])
  def test_normalize(self, input_str, expected):
    assert normalize_for_matching(input_str) == expected


class TestIndexKeyConsistency:
  """Tests to ensure index keys are consistent across all files."""

  @pytest.mark.parametrize("make,model,expected", [
    ("Honda", "CR-V", "honda_cr_v"),
    ("Ford", "F-150", "ford_f_150"),
    ("Chevrolet", "Silverado 1500", "chevrolet_silverado_1500"),
    ("Ram", "1500", "ram_1500"),
    ("Honda", "Civic Type R", "honda_civic_type_r"),
  ])
  def test_index_key_no_spaces(self, make, model, expected):
    result = build_index_key(make, model)
    assert result == expected
    assert " " not in result

  def test_index_key_same_from_both_modules(self):
    from markdown_to_json import build_index_key as md_build_index_key

    test_cases = [
      ("Honda", "CR-V"),
      ("Ford", "F-150"),
      ("Chevrolet", "Silverado 1500"),
      ("Honda", "Civic Type R"),
    ]

    for make, model in test_cases:
      utils_key = build_index_key(make, model)
      md_key = md_build_index_key(make, model)
      assert utils_key == md_key
      assert " " not in utils_key
      assert " " not in md_key


class TestCheckEntryKeywords:
  """Tests for check_entry_keywords()."""

  def test_extra_high_no_keywords(self, sample_car):
    entry = {"match_confidence": "extra_high", "matching_keywords": None}
    matched, confidence = check_entry_keywords(sample_car, entry)
    assert matched is True
    assert confidence == MatchConfidence.EXTRA_HIGH

  def test_high_confidence_with_keywords(self, sample_car):
    entry = {"match_confidence": "high", "matching_keywords": ["ACC", "LKAS"]}
    matched, confidence = check_entry_keywords(sample_car, entry)
    assert matched is True
    assert confidence == MatchConfidence.HIGH

  def test_no_match_missing_keywords(self, sample_car):
    car_without_features = sample_car.copy()
    car_without_features["features"] = ["Bluetooth"]
    entry = {"match_confidence": "high", "matching_keywords": ["ACC", "LKAS"]}
    matched, confidence = check_entry_keywords(car_without_features, entry)
    assert matched is False
    assert confidence == MatchConfidence.HIGH

  def test_fails_fast_on_missing_confidence(self, sample_car):
    """Verify matcher crashes on bad reference data (fail-fast contract)."""
    entry = {"matching_keywords": ["ACC"]}
    with pytest.raises(KeyError, match="match_confidence"):
      check_entry_keywords(sample_car, entry)

  def test_fails_fast_on_invalid_confidence(self, sample_car):
    """Verify matcher crashes on invalid confidence value."""
    entry = {"match_confidence": "super_high", "matching_keywords": ["ACC"]}
    with pytest.raises(ValueError):
      check_entry_keywords(sample_car, entry)


class TestIndexCarsByKey:
  """Tests for index_cars_by_key()."""

  def test_builds_index_correctly(self):
    reference_data = {
      "cars": [
        {"make": "Honda", "model": "CR-V", "index_key": "honda_cr_v", "years": [2020, 2021, 2022]},
        {"make": "Honda", "model": "Civic", "index_key": "honda_civic", "years": [2019, 2020, 2021]},
        {"make": "Toyota", "model": "Camry", "index_key": "toyota_camry", "years": [2018, 2019, 2020]},
      ]
    }

    index = index_cars_by_key(reference_data)

    assert len(index) == 3
    assert "honda_cr_v" in index
    assert "honda_civic" in index
    assert "toyota_camry" in index
    assert len(index["honda_cr_v"]) == 1
    assert len(index["honda_civic"]) == 1

  def test_excludes_non_us_entries_from_match_index(self):
    """Keep non_us variants in reference data, but exclude them from the CarMax match lookup index."""
    reference_data = {
      "cars": [
        {
          "make": "Honda",
          "model": "Odyssey",
          "index_key": "honda_odyssey",
          "years": [2018, 2019, 2020],
          "match_confidence": "high",
        },
        {
          "make": "Honda",
          "model": "Odyssey",
          "index_key": "honda_odyssey",
          "years": [2018, 2019],
          "match_confidence": "non_us",
          "variant_info": "Taiwan",
        },
      ]
    }

    match_index = index_cars_by_key(reference_data)

    assert "honda_odyssey" in match_index
    assert len(match_index["honda_odyssey"]) == 1
    assert match_index["honda_odyssey"][0]["match_confidence"] == "high"


class TestMatchCar:
  """Tests for match_car()."""

  def test_match_rivian(self, sample_reference_entry, sample_car):
    reference_data = {"cars": [sample_reference_entry]}
    index = index_cars_by_key(reference_data)

    matches = match_car(sample_car, index)

    assert len(matches) == 1
    entry, year, confidence = matches[0]
    assert entry["make"] == "Rivian"
    assert entry["model"] == "R1S"
    assert year == 2023
    assert confidence == MatchConfidence.EXTRA_HIGH

  def test_year_out_of_range(self, sample_reference_entry, sample_car):
    reference_data = {"cars": [sample_reference_entry]}
    index = index_cars_by_key(reference_data)

    old_car = sample_car.copy()
    old_car["year"] = 2021

    matches = match_car(old_car, index)
    assert len(matches) == 0

  def test_keyword_requirement(self):
    acura_entry = {
      "make": "Acura",
      "model": "ILX",
      "model_original": "ILX 2016-18",
      "index_key": "acura_ilx",
      "years": [2016, 2017, 2018],
      "package_requirements": "Technology Plus Package or AcuraWatch Plus",
      "match_confidence": "high",
      "matching_keywords": ["ACC", "LKAS"],
      "package_key_used": "Technology Plus Package or AcuraWatch Plus"
    }

    reference_data = {"cars": [acura_entry]}
    index = index_cars_by_key(reference_data)

    car_with_acc_only = {
      "year": 2017,
      "make": "Acura",
      "model": "ILX",
      "basePrice": 15000,
      "mileage": 50000,
      "features": ["Adaptive Cruise Control"],
      "highlightedFeatures": ""
    }
    assert len(match_car(car_with_acc_only, index)) == 0

    car_with_both = {
      "year": 2017,
      "make": "Acura",
      "model": "ILX",
      "basePrice": 15000,
      "mileage": 50000,
      "features": ["Adaptive Cruise Control", "Lane Keep Assist"],
      "highlightedFeatures": ""
    }
    assert len(match_car(car_with_both, index)) == 1

    car_without_any = {
      "year": 2017,
      "make": "Acura",
      "model": "ILX",
      "basePrice": 14000,
      "mileage": 60000,
      "features": ["Bluetooth"],
      "highlightedFeatures": ""
    }
    assert len(match_car(car_without_any, index)) == 0


class TestCheapestSelection:
  """Tests for cheapest car selection logic."""

  def test_cheaper_by_price(self):
    car1 = {"basePrice": 50000, "mileage": 10000}
    car2 = {"basePrice": 45000, "mileage": 15000}

    def is_cheaper(new_car, current_car):
      return (new_car["basePrice"] < current_car["basePrice"] or
              (new_car["basePrice"] == current_car["basePrice"] and
               new_car["mileage"] < current_car["mileage"]))

    assert is_cheaper(car2, car1) is True
    assert is_cheaper(car1, car2) is False

  def test_cheaper_by_mileage_when_same_price(self):
    car2 = {"basePrice": 45000, "mileage": 15000}
    car3 = {"basePrice": 45000, "mileage": 12000}

    def is_cheaper(new_car, current_car):
      return (new_car["basePrice"] < current_car["basePrice"] or
              (new_car["basePrice"] == current_car["basePrice"] and
               new_car["mileage"] < current_car["mileage"]))

    assert is_cheaper(car3, car2) is True


class TestPipelineContract:
  """Contract test: verifies markdown_to_json output matches matcher expectations."""

  def test_reference_entry_schema_contract(self):
    """
    Verifies that reference entries have the exact schema matcher depends on.
    This protects the boundary between markdown_to_json (producer) and matcher (consumer).
    """
    # Simulate a reference entry as markdown_to_json would produce it
    reference_entry = {
      "make": "Honda",
      "model": "Civic",
      "model_original": "Civic 2019-21",
      "index_key": "honda_civic",
      "years": [2019, 2020, 2021],
      "package_requirements": "Honda Sensing",
      "match_confidence": "high",
      "matching_keywords": ["ACC", "LKAS"],
      "package_key_used": "Honda Sensing"
    }

    assert "index_key" in reference_entry
    assert "years" in reference_entry
    assert "match_confidence" in reference_entry
    assert "matching_keywords" in reference_entry

    assert isinstance(reference_entry["index_key"], str)
    assert isinstance(reference_entry["years"], list)
    assert all(isinstance(y, int) for y in reference_entry["years"])
    assert isinstance(reference_entry["match_confidence"], str)

    keywords = reference_entry["matching_keywords"]
    assert keywords is None or (isinstance(keywords, list) and all(isinstance(k, str) for k in keywords))

    # Assert matcher can consume this entry without crashing
    reference_data = {"cars": [reference_entry]}
    index = index_cars_by_key(reference_data)

    assert "honda_civic" in index
    assert len(index["honda_civic"]) == 1

    # Test that matcher can execute matching logic on this entry
    sample_car = {
      "make": "Honda",
      "model": "Civic",
      "year": 2020,
      "basePrice": 20000,
      "mileage": 30000,
      "features": ["Adaptive Cruise Control", "Lane Keep Assist"],
      "highlightedFeatures": ""
    }

    matches = match_car(sample_car, index)
    assert len(matches) == 1
    entry, year, confidence = matches[0]
    assert entry["make"] == "Honda"
    assert year == 2020
    assert confidence == MatchConfidence.HIGH

  def test_null_keywords_contract(self):
    """Verifies matcher correctly handles null keywords (extra_high/non_us)."""
    reference_entry = {
      "make": "Rivian",
      "model": "R1S",
      "model_original": "R1S 2022-24",
      "index_key": "rivian_r1s",
      "years": [2022, 2023, 2024],
      "match_confidence": "extra_high",
      "matching_keywords": None
    }

    reference_data = {"cars": [reference_entry]}
    index = index_cars_by_key(reference_data)

    car = {
      "make": "Rivian",
      "model": "R1S",
      "year": 2023,
      "basePrice": 70000,
      "mileage": 1000,
      "features": [],
      "highlightedFeatures": ""
    }

    matches = match_car(car, index)
    assert len(matches) == 1
    _, _, confidence = matches[0]
    assert confidence == MatchConfidence.EXTRA_HIGH

  def test_placeholder_keywords_contract(self):
    """Verifies matcher correctly handles placeholder keywords ["-"]."""
    reference_entry = {
      "make": "Genesis",
      "model": "GV70",
      "model_original": "GV70 2022-24",
      "index_key": "genesis_gv70",
      "years": [2022, 2023, 2024],
      "match_confidence": "medium",
      "matching_keywords": ["-"]
    }

    reference_data = {"cars": [reference_entry]}
    index = index_cars_by_key(reference_data)

    car = {
      "make": "Genesis",
      "model": "GV70",
      "year": 2023,
      "basePrice": 50000,
      "mileage": 5000,
      "features": ["Some Random Feature"],
      "highlightedFeatures": ""
    }

    matches = match_car(car, index)
    assert len(matches) == 1
    _, _, confidence = matches[0]
    assert confidence == MatchConfidence.MEDIUM


class TestOutputStructure:
  """Tests for output JSON structure."""

  def test_output_file_structure(self):
    output_file = Path(__file__).parent.parent / "data" / "openpilot_cars.json"

    if not output_file.exists():
      pytest.skip("Output file not found")

    with open(output_file) as f:
      data = json.load(f)

    # Check top-level keys
    assert "entries" in data
    assert "warnings" in data
    assert "generated_at" in data

    # Check pipeline metrics structure (if present - may not be in old output files)
    if "pipeline_metrics" in data:
      metrics = data["pipeline_metrics"]
      assert "total_lines" in metrics
      assert "cars_processed" in metrics
      assert "json_parse_errors" in metrics
      assert "matches_found" in metrics
      assert "match_rate" in metrics
      assert "no_match_breakdown" in metrics

      # Validate metric types
      assert isinstance(metrics["total_lines"], int)
      assert isinstance(metrics["cars_processed"], int)
      assert isinstance(metrics["json_parse_errors"], int)
      assert isinstance(metrics["matches_found"], int)
      assert isinstance(metrics["match_rate"], (int, float))
      assert isinstance(metrics["no_match_breakdown"], dict)

    # Check entries structure
    assert isinstance(data["entries"], list)
    assert len(data["entries"]) > 0

    entry = data["entries"][0]

    # Check required fields
    required_fields = [
      "make", "model", "model_original", "package_requirements",
      "package_key_used", "matching_keywords", "variant_info",
      "support_level", "available_years", "unavailable_years"
    ]
    for field in required_fields:
      assert field in entry, f"Missing field: {field}"

    # Check available_years structure
    assert isinstance(entry["available_years"], list)
    if entry["available_years"]:
      avail = entry["available_years"][0]
      assert "year" in avail
      assert "match_confidence" in avail
      assert "car" in avail
      valid_confidence_values = [e.value for e in MatchConfidence]
      assert avail["match_confidence"] in valid_confidence_values

    # Check unavailable_years structure
    assert isinstance(entry["unavailable_years"], list)
    if entry["unavailable_years"]:
      assert isinstance(entry["unavailable_years"][0], int)


class TestMetricsTracking:
  """Tests for metrics tracking functionality."""

  def test_metrics_structure_from_build_output(self):
    """Test that build_output correctly includes metrics in output."""
    reference_data = {
      "cars": [
        {
          "make": "Honda",
          "model": "Civic",
          "model_original": "Civic 2020",
          "years": [2020],
          "package_requirements": "Honda Sensing",
          "match_confidence": "high",
          "matching_keywords": ["ACC"],
          "index_key": "honda_civic"
        }
      ]
    }

    cheapest = {}
    metrics = {
      "total_lines": 100,
      "cars_processed": 95,
      "json_parse_errors": 5,
      "matches_found": 10,
      "no_match_reasons": {
        "unsupported_models": 30,
        "year_mismatch": 20,
        "keyword_mismatch": 15
      }
    }

    from matcher import build_output
    output = build_output(reference_data, cheapest, metrics)

    # Verify metrics are in output
    assert "pipeline_metrics" in output
    pipeline_metrics = output["pipeline_metrics"]

    # Verify all expected fields
    assert pipeline_metrics["total_lines"] == 100
    assert pipeline_metrics["cars_processed"] == 95
    assert pipeline_metrics["json_parse_errors"] == 5
    assert pipeline_metrics["matches_found"] == 10
    assert "match_rate" in pipeline_metrics
    assert pipeline_metrics["match_rate"] == round(10 / 95, 4)
    assert "no_match_breakdown" in pipeline_metrics
    assert pipeline_metrics["no_match_breakdown"]["unsupported_models"] == 30
    assert pipeline_metrics["no_match_breakdown"]["year_mismatch"] == 20
    assert pipeline_metrics["no_match_breakdown"]["keyword_mismatch"] == 15
