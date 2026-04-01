"""CLI integration tests for markdown_to_json.py."""

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "markdown_to_json.py"


def run_markdown_to_json_cli(input_path: Path, output_path: Path, validate_only: bool = False) -> subprocess.CompletedProcess:
  command = [sys.executable, str(SCRIPT_PATH), "--input", str(input_path), "--output", str(output_path)]
  if validate_only:
    command.append("--validate-only")

  return subprocess.run(
    command,
    capture_output=True,
    text=True,
    check=False,
  )


def test_cli_fails_on_missing_required_fields(tmp_path):
  input_path = tmp_path / "bad_cars_10_rows.md"
  output_path = tmp_path / "out.json"
  input_path.write_text(
    "| Make | Model | Package | Support Level |\n"
    "| --- | --- | --- | --- |\n"
    "| Honda | Civic 2019-21 | Honda Sensing | [Upstream](#upstream) |\n"
    "| Acura |  | Technology Plus Package | [Upstream](#upstream) |\n"
    "|  | Accord 2018-20 | Honda Sensing | [Upstream](#upstream) |\n"
    "| Toyota | Camry 2018-22 |  | [Upstream](#upstream) |\n"
    "| Ford | F-150 2021-23 | Co-Pilot360 | [Community](#community) |\n"
    "| Hyundai | Ioniq 5 2022-24 | HDA II | [Upstream](#upstream) |\n"
    "| Nissan | Leaf 2018-21 | ProPILOT | [Dashcam](#dashcam) |\n"
    "| Chevrolet | Bolt EUV 2022-24 | Super Cruise | [Community](#community) |\n"
    "| Kia | EV6 2022-24 | HDA II | [Upstream](#upstream) |\n"
    "| Subaru | Outback 2020-23 | EyeSight | [Community](#community) |\n"
  )

  result = run_markdown_to_json_cli(input_path, output_path)

  assert result.returncode == 1
  assert "Every car must include make, model, and package_requirements." in result.stdout
  assert "row 4 missing: model" in result.stdout
  assert "row 5 missing: make" in result.stdout
  assert "row 6 missing: package_requirements" in result.stdout
  assert not output_path.exists()


def test_cli_validate_only_prints_checkmark_for_valid_table(tmp_path):
  input_path = tmp_path / "valid_cars.md"
  output_path = tmp_path / "out.json"
  input_path.write_text(
    "| Make | Model | Package | Support Level |\n"
    "| --- | --- | --- | --- |\n"
    "| Honda | Civic 2019-21 | Honda Sensing | [Upstream](#upstream) |\n"
  )

  result = run_markdown_to_json_cli(input_path, output_path, validate_only=True)

  assert result.returncode == 0
  assert "✓ Validation passed: valid_cars.md (1 vehicles)" in result.stdout
  assert not output_path.exists()
