"""Tests for shared utilities in utils.py."""

import pytest
from utils import normalize_for_matching, build_index_key


class TestNormalizeForMatching:
    @pytest.mark.parametrize("input_str,expected", [
        ("Honda", "honda"),
        ("CR-V", "cr v"),
        ("CR_V", "cr v"),
        ("F-150", "f 150"),
        ("Civic Type R", "civic type r"),
        ("Silverado 1500", "silverado 1500"),
    ])
    def test_normalize_for_matching(self, input_str, expected):
        assert normalize_for_matching(input_str) == expected


class TestBuildIndexKey:
    @pytest.mark.parametrize("make,model,expected", [
        ("Honda", "CR-V", "honda_cr_v"),
        ("Ford", "F-150", "ford_f_150"),
        ("Chevrolet", "Silverado 1500", "chevrolet_silverado_1500"),
        ("Honda", "Civic Type R", "honda_civic_type_r"),
        ("Ram", "1500", "ram_1500"),
    ])
    def test_build_index_key(self, make, model, expected):
        result = build_index_key(make, model)
        assert result == expected
        assert " " not in result

    def test_build_index_key_regression_multi_word_models(self):
        """
        Regression test for the critical bug where build_index_key() in 
        matcher.py was missing .replace(" ", "_"), causing mismatched keys 
        for multi-word model names like "Civic Type R".
        
        Before fix:
          markdown_to_json: "honda_civic_type_r" (correct)
          matcher:          "honda_civic type r" (BUG - had space!)
        
        After fix:
          Both produce:     "honda_civic_type_r" ✓
        """
        test_cases = [
            ("Honda", "Civic Type R"),
            ("Ford", "Bronco Sport"),
            ("Chevrolet", "Silverado 1500"),
            ("Audi", "A3 Sportback e-tron"),
        ]
        
        for make, model in test_cases:
            key = build_index_key(make, model)
            assert " " not in key
            parts = key.split("_")
            assert all(part for part in parts)
