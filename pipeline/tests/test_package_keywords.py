"""Tests for package_keywords validation logic."""

from markdown_to_json import validate_package_keywords


class TestValidatePackageKeywords:
  """Tests for validate_package_keywords() function."""

  def test_valid_extra_high_with_null_keywords(self):
    """extra_high with null keywords is valid."""
    package_keywords = {
      "All": {
        "confidence": "extra_high",
        "keywords": None
      }
    }
    errors = validate_package_keywords(package_keywords)
    assert errors == []

  def test_valid_non_us_with_null_keywords(self):
    """non_us with null keywords is valid."""
    package_keywords = {
      "All--Europe only": {
        "confidence": "non_us",
        "keywords": None
      }
    }
    errors = validate_package_keywords(package_keywords)
    assert errors == []

  def test_valid_high_with_keywords(self):
    """high confidence with keyword list is valid."""
    package_keywords = {
      "Honda Sensing": {
        "confidence": "high",
        "keywords": ["ACC", "LKAS"]
      }
    }
    errors = validate_package_keywords(package_keywords)
    assert errors == []

  def test_valid_medium_with_placeholder(self):
    """medium confidence with ["-"] placeholder is valid."""
    package_keywords = {
      "ProPILOT Assist": {
        "confidence": "medium",
        "keywords": ["-"]
      }
    }
    errors = validate_package_keywords(package_keywords)
    assert errors == []

  def test_rejects_empty_list(self):
    """Empty keyword list is never valid."""
    package_keywords = {
      "Bad Package": {
        "confidence": "high",
        "keywords": []
      }
    }
    errors = validate_package_keywords(package_keywords)
    assert len(errors) == 1
    assert "empty keywords list not allowed" in errors[0]

  def test_rejects_extra_high_with_keywords(self):
    """extra_high with keywords (non-null) is invalid."""
    package_keywords = {
      "Bad Package": {
        "confidence": "extra_high",
        "keywords": ["ACC"]
      }
    }
    errors = validate_package_keywords(package_keywords)
    # Empty list is caught first, but let's test with null check
    assert len(errors) > 0

  def test_rejects_high_with_null_keywords(self):
    """high confidence requires keywords, not null."""
    package_keywords = {
      "Bad Package": {
        "confidence": "high",
        "keywords": None
      }
    }
    errors = validate_package_keywords(package_keywords)
    assert len(errors) == 1
    assert "null keywords only allowed for extra_high or non_us" in errors[0]

  def test_rejects_non_us_with_keywords(self):
    """non_us should have null keywords, not a list."""
    package_keywords = {
      "Bad Package": {
        "confidence": "non_us",
        "keywords": ["ACC"]
      }
    }
    errors = validate_package_keywords(package_keywords)
    # Will be caught as empty list error or null requirement
    assert len(errors) > 0

  def test_rejects_missing_confidence(self):
    """Missing confidence field returns error."""
    package_keywords = {
      "Bad Package": {
        "keywords": ["ACC"]
      }
    }
    errors = validate_package_keywords(package_keywords)
    assert len(errors) == 1
    assert "missing 'confidence' field" in errors[0]

  def test_rejects_missing_keywords(self):
    """Missing keywords field returns error."""
    package_keywords = {
      "Bad Package": {
        "confidence": "high"
      }
    }
    errors = validate_package_keywords(package_keywords)
    assert len(errors) == 1
    assert "missing 'keywords' field" in errors[0]

  def test_rejects_invalid_confidence_value(self):
    """Invalid confidence value returns helpful error."""
    package_keywords = {
      "Bad Package": {
        "confidence": "super_high",
        "keywords": ["ACC"]
      }
    }
    errors = validate_package_keywords(package_keywords)
    assert len(errors) == 1
    assert "invalid confidence 'super_high'" in errors[0]

  def test_rejects_non_dict_config(self):
    """Package config must be a dict."""
    package_keywords = {
      "Bad Package": "not a dict"
    }
    errors = validate_package_keywords(package_keywords)
    assert len(errors) == 1
    assert "must be a dict" in errors[0]

  def test_rejects_keywords_wrong_type(self):
    """Keywords must be null or list, not other types."""
    package_keywords = {
      "Bad Package": {
        "confidence": "high",
        "keywords": "ACC"
      }
    }
    errors = validate_package_keywords(package_keywords)
    assert len(errors) == 1
    assert "keywords must be null or list" in errors[0]

  def test_rejects_non_string_keyword(self):
    """Keywords list items must be strings."""
    package_keywords = {
      "Bad Package": {
        "confidence": "high",
        "keywords": [123]
      }
    }
    errors = validate_package_keywords(package_keywords)
    assert len(errors) == 1
    assert "keyword must be string" in errors[0]

  def test_rejects_empty_string_keyword(self):
    """Keywords cannot be empty or whitespace strings."""
    package_keywords = {
      "Bad Package": {
        "confidence": "high",
        "keywords": [""]
      }
    }
    errors = validate_package_keywords(package_keywords)
    assert len(errors) == 1
    assert "empty/whitespace keyword" in errors[0]

  def test_multiple_packages_with_mixed_validity(self):
    """Returns errors for all invalid packages."""
    package_keywords = {
      "Good Package": {
        "confidence": "high",
        "keywords": ["ACC", "LKAS"]
      },
      "Bad Package 1": {
        "confidence": "high",
        "keywords": []
      },
      "Bad Package 2": {
        "confidence": "super_duper_high",
        "keywords": ["ACC"]
      }
    }
    errors = validate_package_keywords(package_keywords)
    assert len(errors) == 2
    assert any("Bad Package 1" in err for err in errors)
    assert any("Bad Package 2" in err for err in errors)

  def test_all_confidence_levels_valid(self):
    """All valid confidence levels are accepted."""
    valid_levels = ["extra_high", "high", "medium", "low", "non_us"]
    for level in valid_levels:
      if level in ("extra_high", "non_us"):
        keywords = None
      else:
        keywords = ["-"]

      package_keywords = {
        f"Test {level}": {
          "confidence": level,
          "keywords": keywords
        }
      }
      errors = validate_package_keywords(package_keywords)
      assert errors == [], f"Valid {level} should have no errors"
