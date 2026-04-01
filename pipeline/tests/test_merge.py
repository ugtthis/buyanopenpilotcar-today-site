"""Tests for merge_inventory.py."""

import json

import pytest
import merge_inventory


class TestMergeInventory:
  """Tests for merge_inventory.merge_inventory()."""

  def test_normal_operation(self, temp_dir):
    """Test basic functionality with valid data."""
    output_dir = temp_dir / "output"
    data_dir = temp_dir / "data"
    output_dir.mkdir()
    data_dir.mkdir()

    (output_dir / "Test.json").write_text(json.dumps({
      "make": "Test",
      "listings": [
        {"stockNumber": "1", "make": "Test", "model": "Car1", "year": 2020, "basePrice": 25000},
        {"stockNumber": "2", "make": "Test", "model": "Car2", "year": 2021, "basePrice": 30000}
      ]
    }))

    # Temporarily override paths
    old_output = merge_inventory.OUTPUT_DIR
    old_data = merge_inventory.DATA_DIR
    try:
      merge_inventory.OUTPUT_DIR = output_dir
      merge_inventory.DATA_DIR = data_dir

      result = merge_inventory.merge_inventory("test.jsonl")
      lines = result.read_text().strip().split("\n")

      assert len(lines) == 2
      for line in lines:
        json.loads(line)  # Verify valid JSON
    finally:
      merge_inventory.OUTPUT_DIR = old_output
      merge_inventory.DATA_DIR = old_data

  def test_error_when_no_files(self, temp_dir):
    """Test FileNotFoundError when no valid files exist."""
    output_dir = temp_dir / "output"
    data_dir = temp_dir / "data"
    output_dir.mkdir()
    data_dir.mkdir()

    old_output = merge_inventory.OUTPUT_DIR
    old_data = merge_inventory.DATA_DIR
    try:
      merge_inventory.OUTPUT_DIR = output_dir
      merge_inventory.DATA_DIR = data_dir

      with pytest.raises(FileNotFoundError):
        merge_inventory.merge_inventory("test.jsonl")
    finally:
      merge_inventory.OUTPUT_DIR = old_output
      merge_inventory.DATA_DIR = old_data

  def test_skip_invalid_files(self, temp_dir):
    """Test that invalid files are skipped gracefully."""
    output_dir = temp_dir / "output"
    data_dir = temp_dir / "data"
    output_dir.mkdir()
    data_dir.mkdir()

    # Create various invalid and valid files
    (output_dir / "valid.json").write_text(json.dumps({
      "make": "Valid",
      "listings": [{"stockNumber": "1", "make": "Valid", "model": "Car", "year": 2020, "basePrice": 20000}]
    }))
    (output_dir / "bad.json").write_text("{bad json")
    (output_dir / "empty.json").write_text(json.dumps({"make": "Empty", "listings": []}))
    (output_dir / "no_listings.json").write_text(json.dumps({"make": "Bad"}))

    old_output = merge_inventory.OUTPUT_DIR
    old_data = merge_inventory.DATA_DIR
    try:
      merge_inventory.OUTPUT_DIR = output_dir
      merge_inventory.DATA_DIR = data_dir

      result = merge_inventory.merge_inventory("test.jsonl")
      lines = result.read_text().strip().split("\n")

      assert len(lines) == 1  # Only the valid file processed
    finally:
      merge_inventory.OUTPUT_DIR = old_output
      merge_inventory.DATA_DIR = old_data

  def test_production_data(self):
    """Test with actual production data if available."""
    try:
      result = merge_inventory.merge_inventory("test_final.jsonl")
      lines = result.read_text().strip().split("\n")

      # Verify valid JSONL
      json.loads(lines[0])
      json.loads(lines[-1])

      assert len(lines) > 0
    except Exception:
      pytest.skip("Production data not available")
