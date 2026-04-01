"""Shared pytest fixtures for all tests."""

import tempfile
import shutil
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
  """Create a temporary directory that's cleaned up after the test."""
  path = Path(tempfile.mkdtemp())
  yield path
  shutil.rmtree(path)


@pytest.fixture
def fixtures_dir():
  """Return the path to the test fixtures directory."""
  return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_reference_entry():
  """Sample reference car entry for testing."""
  return {
    "make": "Rivian",
    "model": "R1S",
    "model_original": "R1S 2022-24",
    "index_key": "rivian_r1s",
    "years": [2022, 2023, 2024],
    "package_requirements": "All",
    "match_confidence": "extra_high",
    "matching_keywords": None,
    "package_key_used": "All"
  }


@pytest.fixture
def sample_car():
  """Sample car listing for testing."""
  return {
    "stockNumber": 12345,
    "vin": "TEST123456789",
    "year": 2023,
    "make": "Rivian",
    "model": "R1S",
    "basePrice": 60000.0,
    "mileage": 5000,
    "features": ["Lane Departure Warning", "Automated Cruise Control"],
    "highlightedFeatures": "AWD,Leatherette Seats"
  }
