import json
from pathlib import Path

import scripts.generate_pr_summary as summary_script
from scripts.generate_pr_summary import (
  get_failed_makes,
  get_count_mismatches,
  get_product_summary,
  get_workflow_state,
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
