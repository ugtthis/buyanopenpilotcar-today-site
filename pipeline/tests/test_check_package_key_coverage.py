from pathlib import Path

from scripts.check_package_key_coverage import check_package_key_coverage


HEADER = "| Make | Model | Package | Support Level |\n| --- | --- | --- | --- |\n"


def _write_text(path: Path, content: str) -> Path:
  path.write_text(content, encoding="utf-8")
  return path


def test_check_package_key_coverage_happy_path(tmp_path):
  cars_md = _write_text(
    tmp_path / "CARS.md",
    HEADER + "| Honda | Pilot 2026 | All | [Upstream](#upstream) |\n",
  )
  package_keywords = _write_text(
    tmp_path / "package_keywords.json",
    '{\n  "All": {"confidence": "extra_high", "keywords": null}\n}\n',
  )

  result = check_package_key_coverage(cars_md, package_keywords)

  assert result["errors"] == []
  assert result["missing_package_keys"] == []
  assert result["unused_package_keys"] == []


def test_check_package_key_coverage_reports_missing_composite_key(tmp_path):
  cars_md = _write_text(
    tmp_path / "CARS.md",
    HEADER + "| Hyundai | Ioniq 6 (without HDA II) 2023-24 | Highway Driving Assist | [Upstream](#upstream) |\n",
  )
  package_keywords = _write_text(
    tmp_path / "package_keywords.json",
    '{}\n',
  )

  result = check_package_key_coverage(cars_md, package_keywords)

  assert result["errors"] == []
  assert result["missing_package_keys"] == ["Highway Driving Assist--without HDA II"]


def test_check_package_key_coverage_reports_row_validation_errors(tmp_path):
  cars_md = _write_text(
    tmp_path / "CARS.md",
    HEADER + "| Honda | Pilot 2026 |  | [Upstream](#upstream) |\n",
  )
  package_keywords = _write_text(
    tmp_path / "package_keywords.json",
    '{\n  "All": {"confidence": "extra_high", "keywords": null}\n}\n',
  )

  result = check_package_key_coverage(cars_md, package_keywords)

  assert result["errors"] != []
  assert any("package_requirements" in error for error in result["errors"])
  assert result["missing_package_keys"] == []
