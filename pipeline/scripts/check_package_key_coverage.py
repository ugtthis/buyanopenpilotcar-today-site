#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PIPELINE_DIR = SCRIPT_DIR.parent
if str(PIPELINE_DIR) not in sys.path:
  sys.path.insert(0, str(PIPELINE_DIR))

from markdown_to_json import (  # noqa: E402
  RowValidationError,
  find_package_errors,
  parse_cars_from_markdown,
  validate_package_keywords,
)


def check_package_key_coverage(cars_path: Path, package_keywords_path: Path) -> dict:
  result = {
    "errors": [],
    "missing_package_keys": [],
    "unused_package_keys": [],
  }

  try:
    package_keywords = json.loads(package_keywords_path.read_text(encoding="utf-8"))
  except Exception as exc:
    result["errors"].append(f"Failed to load {package_keywords_path}: {exc}")
    return result

  validation_errors = validate_package_keywords(package_keywords)
  if validation_errors:
    result["errors"].extend(validation_errors)
    return result

  try:
    cars = parse_cars_from_markdown(cars_path, package_keywords)
  except RowValidationError as exc:
    result["errors"].append(str(exc))
    return result
  except Exception as exc:
    result["errors"].append(f"Failed to parse {cars_path}: {exc}")
    return result

  unused_package_keys, missing_package_keys = find_package_errors(cars, package_keywords)
  result["missing_package_keys"] = sorted(missing_package_keys)
  result["unused_package_keys"] = sorted(unused_package_keys)
  return result


def write_github_output(result: dict, output_path: Path, exit_code: int) -> None:
  missing_keys = result.get("missing_package_keys", [])
  with output_path.open("a", encoding="utf-8") as fh:
    fh.write(f"validate_status={exit_code}\n")
    fh.write(f"has_missing={'true' if missing_keys else 'false'}\n")
    if missing_keys:
      fh.write("missing_keys<<EOF\n")
      fh.write("\n".join(missing_keys) + "\n")
      fh.write("EOF\n")


def main() -> int:
  parser = argparse.ArgumentParser()
  parser.add_argument("--input", type=Path, required=True, help="Path to CARS.md")
  parser.add_argument(
    "--package-keywords",
    type=Path,
    default=PIPELINE_DIR / "package_keywords.json",
    help="Path to package_keywords.json",
  )
  parser.add_argument(
    "--output-json",
    type=Path,
    help="Optional path to write machine-readable JSON output",
  )
  parser.add_argument(
    "--github-output",
    type=Path,
    help="Optional GitHub Actions output file path (usually $GITHUB_OUTPUT)",
  )
  args = parser.parse_args()

  result = check_package_key_coverage(args.input, args.package_keywords)
  payload = json.dumps(result, indent=2)

  if args.output_json:
    args.output_json.write_text(payload + "\n", encoding="utf-8")
  else:
    print(payload)

  exit_code = 0
  if not result["errors"] and not result["missing_package_keys"]:
    print(f"✓ Package key coverage passed for {args.input.name}", flush=True)
  else:
    exit_code = 1

    if result["errors"]:
      print("\n❌ Coverage check errors:", flush=True)
      for error in result["errors"]:
        print(f"  - {error}", flush=True)

    if result["missing_package_keys"]:
      print("\n⚠ Missing package key definitions:", flush=True)
      for key in result["missing_package_keys"]:
        print(f'  - "{key}"', flush=True)

  if args.github_output:
    write_github_output(result, args.github_output, exit_code)

  return exit_code


if __name__ == "__main__":
  raise SystemExit(main())
