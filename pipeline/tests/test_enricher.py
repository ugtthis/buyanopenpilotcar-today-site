"""Tests for enricher.py."""

import pytest

from enricher import build_name_index, build_support_specs, enrich_ref_data


def make_metadata_entry(name: str, make: str, model: str, year_list: list[str], **overrides):
  entry = {
    "name": name,
    "make": make,
    "model": model,
    "year_list": year_list,
    "longitudinal": "Stock",
    "fsr_longitudinal": "0 mph",
    "fsr_steering": "0 mph",
    "experimental_longitudinal_available": False,
    "openpilot_longitudinal_control": False,
    "steering_torque": "full",
    "auto_resume_star": "full",
  }
  entry.update(overrides)
  return entry


def make_output_entry(make: str, model: str, model_original: str, years: list[int]):
  return {
    "name": f"{make} {model_original}",
    "make": make,
    "model": model,
    "model_original": model_original,
    "years": years,
  }


class TestBuildNameIndex:
  def test_builds_name_index(self):
    metadata_entries = [
      make_metadata_entry("Acura ADX 2025-26", "Acura", "ADX", ["2025", "2026"]),
      make_metadata_entry("Honda Civic 2020", "Honda", "Civic", ["2020"]),
    ]

    name_index = build_name_index(metadata_entries)

    assert name_index == {
      "Acura ADX 2025-26": metadata_entries[0],
      "Honda Civic 2020": metadata_entries[1],
    }

  def test_raises_for_duplicate_names(self):
    metadata_entries = [
      make_metadata_entry("Honda Civic 2020", "Honda", "Civic", ["2020"]),
      make_metadata_entry("Honda Civic 2020", "Honda", "Civic", ["2020"]),
    ]

    with pytest.raises(ValueError, match="Duplicate metadata name: Honda Civic 2020"):
      build_name_index(metadata_entries)


class TestBuildSupportSpecs:
  def test_raises_for_missing_required_field(self):
    metadata_entry = make_metadata_entry("Honda Civic 2020", "Honda", "Civic", ["2020"])
    del metadata_entry["steering_torque"]

    with pytest.raises(
      ValueError,
      match="Metadata entry 'Honda Civic 2020' is missing required support spec field: steering_torque",
    ):
      build_support_specs(metadata_entry)

  def test_raises_for_none_required_field(self):
    metadata_entry = make_metadata_entry(
      "Honda Civic 2020",
      "Honda",
      "Civic",
      ["2020"],
      steering_torque=None,
    )

    with pytest.raises(
      ValueError,
      match="Metadata entry 'Honda Civic 2020' is missing required support spec field: steering_torque",
    ):
      build_support_specs(metadata_entry)


class TestEnrichRefData:
  def test_adds_support_specs_for_exact_matches(self):
    reference_data = {
      "cars": [
        make_output_entry("Acura", "ADX", "ADX 2025-26", [2025, 2026]),
        make_output_entry("Honda", "Civic", "Civic 2020", [2020]),
      ]
    }
    metadata_entries = [
      make_metadata_entry("Acura ADX 2025-26", "Acura", "ADX", ["2025", "2026"]),
      make_metadata_entry("Honda Civic 2020", "Honda", "Civic", ["2020"]),
    ]

    enriched_count = enrich_ref_data(reference_data, metadata_entries)

    assert enriched_count == 2
    assert reference_data["cars"][0]["support_specs"] == build_support_specs(metadata_entries[0])
    assert reference_data["cars"][1]["support_specs"] == build_support_specs(metadata_entries[1])

  def test_raises_for_missing_exact_match(self):
    reference_data = {
      "cars": [
        make_output_entry("Acura", "ADX", "ADX 2025-26", [2025, 2026]),
        make_output_entry("Honda", "Civic", "Civic 2020", [2020]),
      ]
    }
    metadata_entries = [
      make_metadata_entry("Acura ADX 2025-26", "Acura", "ADX", ["2025", "2026"]),
    ]

    with pytest.raises(ValueError, match=r"1 ref car\(s\) missing from metadata:\n  - Honda Civic 2020"):
      enrich_ref_data(reference_data, metadata_entries)
