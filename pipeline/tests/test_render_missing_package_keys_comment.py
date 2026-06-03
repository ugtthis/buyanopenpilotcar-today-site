import json

from scripts.render_missing_package_keys_comment import _build_comment_body


def test_build_comment_body_preserves_critical_contract_literals():
  coverage_payload = '{"missing_package_keys":["All"]}'

  body = _build_comment_body(["All"], coverage_payload)

  assert body.count("<!-- package-keywords-missing -->") == 1
  assert body.count("## Missing `package_keywords.json` entries") == 1
  assert body.count("<summary>Coverage check JSON (collapsed by default)</summary>") == 1


def test_build_comment_body_includes_required_sections_and_key_bullets():
  coverage_payload = json.dumps(
    {
      "errors": [],
      "missing_package_keys": [
        "Highway Driving Assist--without HDA II",
        "All",
      ],
      "unused_package_keys": [],
    },
    indent=2,
  )

  body = _build_comment_body(
    ["Highway Driving Assist--without HDA II", "All"],
    coverage_payload,
  )

  assert body.startswith("<!-- package-keywords-missing -->\n")
  assert "## Missing `package_keywords.json` entries" in body
  assert "Add definitions for the keys below, then regenerate reference data:" in body
  assert "- `Highway Driving Assist--without HDA II`" in body
  assert "- `All`" in body
  assert body.index("- `Highway Driving Assist--without HDA II`") < body.index("- `All`")
  assert "<summary>Coverage check JSON (collapsed by default)</summary>" in body
  assert "```bash\ncd pipeline\nuv run python markdown_to_json.py" in body


def test_build_comment_body_filters_blank_missing_keys():
  coverage_payload = json.dumps(
    {
      "errors": [],
      "missing_package_keys": ["", "All"],
      "unused_package_keys": [],
    },
    indent=2,
  )

  body = _build_comment_body(["", "All"], coverage_payload)

  assert "- `All`" in body
  assert "- ``" not in body


def test_build_comment_body_embeds_payload_without_extra_trailing_newline():
  coverage_payload = '{\n  "missing_package_keys": ["All"]\n}\n'

  body = _build_comment_body(["All"], coverage_payload)

  assert '```json\n{\n  "missing_package_keys": ["All"]\n}\n```' in body
