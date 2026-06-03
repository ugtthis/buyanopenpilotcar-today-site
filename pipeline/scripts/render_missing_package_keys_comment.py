#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _build_comment_body(missing_keys: list[str], coverage_payload: str) -> str:
  lines = [
    "<!-- package-keywords-missing -->",
    "## Missing `package_keywords.json` entries",
    "",
    "This PR updates `CARS.md` with package key(s) that are not currently defined in `pipeline/package_keywords.json`.",
    "",
    "Add definitions for the keys below, then regenerate reference data:",
    "",
  ]
  lines.extend(f"- `{key}`" for key in missing_keys if key)
  lines.extend(
    [
      "",
      "Suggested skeleton (choose confidence/keywords via manual review):",
      "",
      "```json",
      "{",
      '  "KEY": {',
      '    "confidence": "TODO",',
      '    "keywords": ["TODO"]',
      "  }",
      "}",
      "```",
      "",
      "Then run:",
      "",
      "```bash",
      "cd pipeline",
      "uv run python markdown_to_json.py --input data/ref/CARS.md --output data/ref/opendbc_ref.json",
      "uv run python enricher.py",
      "# writes data/ref/opendbc_enriched_ref.json",
      "```",
      "",
      "<details>",
      "<summary>Coverage check JSON (collapsed by default)</summary>",
      "",
      "```json",
      coverage_payload.rstrip("\n"),
      "```",
      "",
      "</details>",
      "",
    ]
  )
  return "\n".join(lines)


def main() -> int:
  parser = argparse.ArgumentParser()
  parser.add_argument("--coverage-json", type=Path, required=True)
  parser.add_argument("--output-md", type=Path, required=True)
  args = parser.parse_args()

  payload_text = args.coverage_json.read_text(encoding="utf-8")
  payload = json.loads(payload_text)
  missing_keys = payload.get("missing_package_keys", [])

  comment_body = _build_comment_body(missing_keys, payload_text)
  args.output_md.write_text(comment_body, encoding="utf-8")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
