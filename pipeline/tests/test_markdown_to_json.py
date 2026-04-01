"""Tests for markdown_to_json.py parsing functions."""

import pytest
from markdown_to_json import (
  RowValidationError,
  build_package_error_messages,
  build_index_key,
  clean_model,
  find_package_errors,
  parse_cars_from_markdown,
)


class TestCleanModel:
  """Tests for clean_model() - removes years and parentheses, preserves numeric model names."""

  @pytest.mark.parametrize("input_str,expected", [
    # Ram trucks
    ("1500 2019-24", "1500"),
    ("2500 2020-24", "2500"),
    ("3500 2019-22", "3500"),
    # Regular models with years
    ("Civic 2019-21", "Civic"),
    ("Accord 2018-22", "Accord"),
    ("F-150 2021-23", "F-150"),
    # Models with parentheses
    ("CR-V (Touring) 2020-22", "CR-V"),
    ("Ioniq 5 (with HDA II) 2022-24", "Ioniq 5"),
    # Models with just years
    ("Prius 2016", "Prius"),
    ("Camry 2018-20", "Camry"),
    # Multiple discontinuous years
    ("Accord 2010, 2012", "Accord"),
    ("Civic 2010-12, 2014", "Civic"),
    ("Pilot 2015, 2017, 2019", "Pilot"),
    ("CR-V 2010-12, 2015-17", "CR-V"),
    # Numeric model names that look like years
    ("208 2019-25", "208"),
    ("2008 2018-20", "2008"),
    ("3008 2019-21", "3008"),
    # Models without years (should remain unchanged)
    ("Civic", "Civic"),
    ("1500", "1500"),
    ("F-150", "F-150"),
  ])
  def test_clean_model(self, input_str, expected):
    assert clean_model(input_str) == expected


class TestBuildIndexKey:
  """Tests for build_index_key() - creates normalized keys with underscores, no spaces."""

  @pytest.mark.parametrize("make,model,expected", [
    ("Chevrolet", "Silverado 1500", "chevrolet_silverado_1500"),
    ("Chevrolet", "Bolt EUV", "chevrolet_bolt_euv"),
    ("Ford", "Bronco Sport", "ford_bronco_sport"),
    ("Ford", "Escape Hybrid", "ford_escape_hybrid"),
    ("Ford", "F-150", "ford_f_150"),
    ("Audi", "A3 Sportback e-tron", "audi_a3_sportback_e_tron"),
  ])
  def test_build_index_key(self, make, model, expected):
    result = build_index_key(make, model)
    assert result == expected
    assert " " not in result, f"Index key should not contain spaces: '{result}'"


class TestRowValidation:
  HEADER = "| Make | Model | Package | Support Level |\n| --- | --- | --- | --- |\n"

  @staticmethod
  def _write_markdown(tmp_path, markdown_content: str):
    markdown_path = tmp_path / "cars.md"
    markdown_path.write_text(markdown_content)
    return markdown_path

  def test_raises_on_missing_model(self, tmp_path):
    markdown_path = self._write_markdown(
      tmp_path,
      self.HEADER + "| Acura |  | Technology Plus Package | [Upstream](#upstream) |\n",
    )

    with pytest.raises(RowValidationError, match=r"row 3 missing: model"):
      parse_cars_from_markdown(markdown_path, {})

  def test_raises_on_missing_make(self, tmp_path):
    markdown_path = self._write_markdown(
      tmp_path,
      self.HEADER + "|  | Civic 2019-21 | Honda Sensing | [Upstream](#upstream) |\n",
    )

    with pytest.raises(RowValidationError, match=r"row 3 missing: make"):
      parse_cars_from_markdown(markdown_path, {})

  def test_raises_on_missing_package_requirements(self, tmp_path):
    markdown_path = self._write_markdown(
      tmp_path,
      self.HEADER + "| Honda | Accord 2018-20 |  | [Upstream](#upstream) |\n",
    )

    with pytest.raises(RowValidationError, match=r"row 3 missing: package_requirements"):
      parse_cars_from_markdown(markdown_path, {})

  def test_parses_valid_row(self, tmp_path):
    markdown_path = self._write_markdown(
      tmp_path,
      self.HEADER + "| Honda | Civic 2019-21 | Honda Sensing | [Upstream](#upstream) |\n",
    )

    cars = parse_cars_from_markdown(markdown_path, {})

    assert len(cars) == 1
    assert cars[0]["make"] == "Honda"
    assert cars[0]["model"] == "Civic"
    assert cars[0]["package_requirements"] == "Honda Sensing"


class TestPackageErrorContracts:
  def test_find_package_errors_returns_expected_sets(self):
    cars = [
      {
        "package_requirements": "Honda Sensing",
        "variant_info": None,
        "package_key_used": "Honda Sensing",
        "match_confidence": "high",
      },
      {
        "package_requirements": "HDA II",
        "variant_info": None,
        "package_key_used": None,
        "match_confidence": None,
      },
      {
        "package_requirements": "HDA II",
        "variant_info": None,
        "package_key_used": None,
        "match_confidence": None,
      },
      {
        "package_requirements": "ProPILOT",
        "variant_info": "w/ Navi-link",
        "package_key_used": None,
        "match_confidence": None,
      },
    ]
    package_keywords = {
      "Honda Sensing": {"confidence": "high", "keywords": ["ACC"]},
      "Toyota Safety Sense": {"confidence": "high", "keywords": ["ACC"]},
      "Unused Package": {"confidence": "low", "keywords": ["LKAS"]},
    }

    unused_package_keys, missing_package_keys = find_package_errors(cars, package_keywords)

    assert unused_package_keys == {"Toyota Safety Sense", "Unused Package"}
    assert missing_package_keys == {"HDA II", "ProPILOT--w/ Navi-link"}

  def test_build_package_error_messages_returns_empty_for_no_errors(self):
    package_error_lines = build_package_error_messages(set(), set())
    assert package_error_lines == []

  def test_build_package_error_messages_returns_sorted_deterministic_output(self):
    package_error_lines = build_package_error_messages(
      {"Zeta Package", "Alpha Package"},
      {"Zulu Missing", "Beta Missing"},
    )

    assert package_error_lines == [
      "",
      "⚠ Warning: Package(s) below are NOT used by any car!",
      "   Remove the following from package_keywords.json:",
      "   - \"Alpha Package\"",
      "   - \"Zeta Package\"",
      "",
      "⚠ Warning: Missing package definition(s)!",
      "   Add the below to package_keywords.json:",
      "   - \"Beta Missing\"",
      "   - \"Zulu Missing\"",
      "",
      "❌ Error: Data validation failed. Please fix the issues above.",
    ]
