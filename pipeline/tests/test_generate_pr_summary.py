import json
from pathlib import Path

import scripts.generate_pr_summary as summary_script
from scripts.generate_pr_summary import (
  get_failed_makes,
  get_count_mismatches,
  get_product_summary,
  get_geocode_summary,
  get_workflow_state,
  append_geocode_summary,
  append_workflow_state,
  save_scrape_counts,
  HEALTHY_STATE,
  DEGRADED_STATE,
)


INVENTORY = Path("data/2024-01-01_full.jsonl")
TOYOTA_MISMATCH = [{"make": "Toyota", "html_count": 3200, "api_count": 310}]


class TestGetFailedMakes:
  def test_returns_failed_makes_from_file(self, tmp_path, monkeypatch):
    result_file = tmp_path / "scrape_result.json"
    result_file.write_text(json.dumps({"failed_makes": ["Porsche", "BMW"]}))
    monkeypatch.setattr(summary_script, "SCRAPE_RESULT_FILE", result_file)

    assert get_failed_makes() == ["Porsche", "BMW"]

  def test_returns_empty_when_file_missing(self, tmp_path, monkeypatch):
    monkeypatch.setattr(summary_script, "SCRAPE_RESULT_FILE", tmp_path / "missing.json")

    assert get_failed_makes() == []

  def test_returns_empty_when_file_malformed(self, tmp_path, monkeypatch):
    result_file = tmp_path / "scrape_result.json"
    result_file.write_text("not json")
    monkeypatch.setattr(summary_script, "SCRAPE_RESULT_FILE", result_file)

    assert get_failed_makes() == []


class TestGetCountMismatches:
  def test_returns_mismatches_from_file(self, tmp_path, monkeypatch):
    result_file = tmp_path / "scrape_result.json"
    result_file.write_text(json.dumps({"count_mismatches": TOYOTA_MISMATCH}))
    monkeypatch.setattr(summary_script, "SCRAPE_RESULT_FILE", result_file)

    assert get_count_mismatches() == TOYOTA_MISMATCH

  def test_returns_empty_when_file_missing(self, tmp_path, monkeypatch):
    monkeypatch.setattr(summary_script, "SCRAPE_RESULT_FILE", tmp_path / "missing.json")

    assert get_count_mismatches() == []

  def test_returns_empty_when_file_malformed(self, tmp_path, monkeypatch):
    result_file = tmp_path / "scrape_result.json"
    result_file.write_text("not json")
    monkeypatch.setattr(summary_script, "SCRAPE_RESULT_FILE", result_file)

    assert get_count_mismatches() == []


PRODUCT_FILE_CONTENT = {
  "entries": [
    {"make": "Toyota", "model": "Camry", "available_years": [{"year": 2022}]},
    {"make": "Honda", "model": "Civic", "available_years": []},
    {"make": "Ford", "model": "F-150", "available_years": [{"year": 2021}]},
  ],
  "pipeline_metrics": {
    "cars_processed": 50000,
    "matches_found": 2500,
    "match_rate": 0.05,
  },
}


class TestGetProductSummary:
  def test_returns_stats_from_product_file(self, tmp_path, monkeypatch):
    product_file = tmp_path / "openpilot_cars.json"
    product_file.write_text(json.dumps(PRODUCT_FILE_CONTENT))
    monkeypatch.setattr(summary_script, "PRODUCT_ARTIFACT", product_file)

    result = get_product_summary()

    assert result["total_variants"] == 3
    assert result["variants_with_matches"] == 2
    assert result["matches_found"] == 2500
    assert result["cars_processed"] == 50000
    assert result["match_rate"] == 0.05

  def test_returns_none_when_file_missing(self, tmp_path, monkeypatch):
    monkeypatch.setattr(summary_script, "PRODUCT_ARTIFACT", tmp_path / "missing.json")

    assert get_product_summary() is None


class TestGetGeocodeSummary:
  def test_returns_geocode_summary_from_file(self, tmp_path, monkeypatch):
    geocode_file = tmp_path / "geocode-summary.json"
    geocode_file.write_text(
      json.dumps(
        {
          "status": "ok",
          "missing_count": 3,
          "geocoded_count": 3,
          "failed_count": 0,
          "failed_store_ids": [],
        }
      )
    )
    monkeypatch.setattr(summary_script, "GEOCODE_RESULT_FILE", geocode_file)

    result = get_geocode_summary()
    assert result["status"] == "ok"
    assert result["missing_count"] == 3

  def test_returns_none_when_file_missing(self, tmp_path, monkeypatch):
    monkeypatch.setattr(summary_script, "GEOCODE_RESULT_FILE", tmp_path / "missing.json")
    assert get_geocode_summary() is None


class TestAppendWorkflowState:
  def test_count_mismatches_renders_markdown_table(self):
    lines = []
    append_workflow_state(
      lines,
      DEGRADED_STATE,
      INVENTORY,
      [],
      [
        {"make": "Toyota", "html_count": 3200, "api_count": 310},
        {"make": "Honda", "html_count": 1500, "api_count": 1499},
      ],
      [],
    )
    joined = "\n".join(lines)
    assert "**Count mismatches**" in joined
    assert "| Make | HTML | API | Delta |" in joined
    assert "| **Toyota** | 3,200 | 310 | -2,890 |" in joined
    assert "| **Honda** | 1,500 | 1,499 | -1 |" in joined


class TestAppendGeocodeSummary:
  def test_appends_no_missing_message(self):
    lines = []
    append_geocode_summary(
      lines,
      {
        "status": "no_missing",
        "missing_count": 0,
        "geocoded_count": 0,
        "failed_count": 0,
        "failed_store_ids": [],
      },
    )

    joined = "\n".join(lines)
    assert "## Store Coordinates" in joined
    assert "No new stores needed geocoding." in joined

  def test_appends_failed_store_ids(self):
    lines = []
    append_geocode_summary(
      lines,
      {
        "status": "failed",
        "missing_count": 4,
        "geocoded_count": 2,
        "failed_count": 2,
        "failed_store_ids": ["6154", "7298"],
      },
    )

    joined = "\n".join(lines)
    assert "Missing stores detected: **4** | Geocoded: **2** | Failed: **2**" in joined
    assert "Failed store IDs: `6154`, `7298`" in joined

  def test_returns_none_when_file_malformed(self, tmp_path, monkeypatch):
    product_file = tmp_path / "openpilot_cars.json"
    product_file.write_text("not json")
    monkeypatch.setattr(summary_script, "PRODUCT_ARTIFACT", product_file)

    assert get_product_summary() is None


class TestSaveScrapeCounts:
  def test_writes_counts_to_file(self, tmp_path, monkeypatch):
    monkeypatch.setattr(summary_script, "DATA_DIR", tmp_path)
    monkeypatch.setattr(summary_script, "SCRAPE_COUNTS_FILE", tmp_path / "scrape_counts.json")

    counts = {"Toyota": 11279, "Honda": 9876, "Ford": 8500}
    save_scrape_counts(counts)

    written = json.loads((tmp_path / "scrape_counts.json").read_text())
    assert written == counts


class TestWorkflowState:
  def test_healthy_when_all_artifacts_present_and_no_failures(self):
    assert get_workflow_state({"Toyota": 100}, INVENTORY, True, [], []) == HEALTHY_STATE

  def test_degraded_when_makes_failed(self):
    assert get_workflow_state({"Toyota": 100}, INVENTORY, True, ["Porsche"], []) == DEGRADED_STATE

  def test_degraded_when_product_artifact_missing(self):
    assert get_workflow_state({"Toyota": 100}, INVENTORY, False, [], []) == DEGRADED_STATE

  def test_degraded_when_no_scrape_output(self):
    assert get_workflow_state({}, INVENTORY, True, [], []) == DEGRADED_STATE

  def test_degraded_when_count_mismatches(self):
    assert get_workflow_state({"Toyota": 100}, INVENTORY, True, [], TOYOTA_MISMATCH) == DEGRADED_STATE
