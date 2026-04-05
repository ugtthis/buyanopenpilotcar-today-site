#!/usr/bin/env python3
import argparse
import json
import re
import sys
from pathlib import Path

from utils import build_index_key, CarVariant

SCRIPT_DIR = Path(__file__).parent
DEFAULT_INPUT = SCRIPT_DIR / "data" / "ref" / "CARS.md" # from opendbc/docs/CARS.md
DEFAULT_OUTPUT = SCRIPT_DIR / "data" / "ref" / "opendbc_ref.json"
PACKAGE_KEYWORDS_PATH = SCRIPT_DIR / "package_keywords.json"

EXTRACT_COLUMNS = {
  "make": ["Make"],
  "model": ["Model"],
  "package_requirements": ["Package", "Supported Package"],
  "support_level": ["Support Level"],
}

YEAR_RANGE = r'(?:19|20)\d{2}(?:-\d{2,4})?'
YEAR_SUFFIX_PATTERN = rf"(?:{YEAR_RANGE}(?:\s*,\s*)?)+\s*$"
PARENTHESES_CONTENT = r'\(([^)]*)\)'
MARKDOWN_LINK = r'\[(.*?)\]\(#(.*?)\)'

# Mirrors MatchConfidence in matcher.py — keep them in sync if confidence levels change.
VALID_CONFIDENCE_VALUES = frozenset({"extra_high", "high", "medium", "low", "non_us"})
NULL_KEYWORDS_CONFIDENCE = frozenset({"extra_high", "non_us"})


class RowValidationError(Exception):
  pass


def parse_row(text_line: str) -> list[str]:
  return [c.strip() for c in text_line.strip("|").split("|")]


def clean_model(model: str) -> str:
  model = re.sub(YEAR_SUFFIX_PATTERN, '', model)
  model = re.sub(PARENTHESES_CONTENT, '', model)
  return model.strip()


def is_table_row(text_line: str) -> bool:
  return text_line.startswith("|") and "---" not in text_line


def map_columns(headers: list[str], column_spec: dict[str, list[str]]) -> dict[str, int]:
  col_map = {}
  for key, aliases in column_spec.items():
    for header in aliases:
      if header in headers:
        col_map[key] = headers.index(header)
        break
  return col_map


def get_cell(row: list[str], col_map: dict[str, int], key: str) -> str | None:
  column_index = col_map.get(key)
  if column_index is None or column_index >= len(row):
    return None
  value = row[column_index].strip()
  return value if value else None


def extract_years(model_string: str) -> list[int]:
  match = re.search(YEAR_SUFFIX_PATTERN, model_string)
  if not match:
    return []
  years = []
  for year_match in re.findall(YEAR_RANGE, match.group()):
    parts = year_match.split("-")
    start = int(parts[0])
    if len(parts) > 1:
      if len(parts[1]) == 4:
        raise ValueError(f"Unexpected year format in '{model_string}'")
      end = int(parts[1])
      if end < 100:
        end += (start // 100) * 100
    else:
      end = start
    years.extend(range(start, end + 1))
  return sorted(set(years))


def parse_support_level(text: str | None) -> dict[str, str]:
  match = re.search(MARKDOWN_LINK, text or "")
  if match:
    return {"type": match.group(1).lower(), "link_anchor": match.group(2)}
  return {"type": (text or "").lower()}


def load_package_keywords() -> dict[str, dict]:
  if not PACKAGE_KEYWORDS_PATH.exists():
    raise FileNotFoundError(f" {PACKAGE_KEYWORDS_PATH}. File required for package keyword matching.")

  return json.loads(PACKAGE_KEYWORDS_PATH.read_text())


def validate_package_keywords(package_keywords: dict) -> list[str]:
  errors = []
  allowed_confidences_text = ", ".join(sorted(VALID_CONFIDENCE_VALUES))
  null_allowed_confidences_text = " or ".join(sorted(NULL_KEYWORDS_CONFIDENCE))

  for package_name, config in package_keywords.items():
    if not isinstance(config, dict):
      errors.append(f"{package_name}: must be a dict with 'confidence' and 'keywords'")
      continue

    if "confidence" not in config:
      errors.append(f"{package_name}: missing 'confidence' field")
      continue

    if "keywords" not in config:
      errors.append(f"{package_name}: missing 'keywords' field")
      continue

    confidence = config["confidence"]
    keywords = config["keywords"]

    if confidence not in VALID_CONFIDENCE_VALUES:
      errors.append(f"{package_name}: invalid confidence '{confidence}' (choose from: {allowed_confidences_text})")
      continue

    keywords_is_null = keywords is None
    keywords_is_list = isinstance(keywords, list)
    confidence_requires_null = confidence in NULL_KEYWORDS_CONFIDENCE

    if keywords_is_null:
      if not confidence_requires_null:
        errors.append(f"{package_name}: null keywords only allowed for {null_allowed_confidences_text}")
      continue

    if not keywords_is_list:
      errors.append(f"{package_name}: keywords must be null or list, got {type(keywords).__name__}")
      continue

    if confidence_requires_null:
      errors.append(f"{package_name}: confidence '{confidence}' must have null keywords, not a list")
      continue

    if not keywords:
      errors.append(f"{package_name}: empty keywords list not allowed. Use null for 'no verification', or add keywords")
      continue

    for keyword in keywords:
      if not isinstance(keyword, str):
        errors.append(f"{package_name}: keyword must be string, got {type(keyword).__name__}")
      elif not keyword.strip():
        errors.append(f"{package_name}: empty/whitespace keyword not allowed")

  return errors


def extract_variant_info(model_original: str) -> str | None:
  """Extract text in between parentheses in model name"""
  match = re.search(PARENTHESES_CONTENT, model_original)
  if not match:
    return None
  content = match.group(1).strip()
  return content if content else None


def make_package_key(package: str, variant: str | None = None) -> str:
  return f"{package}--{variant}" if variant else package


def parse_car_from_table_row(
    row: list[str],
    col_map: dict[str, int],
) -> tuple[CarVariant | None, tuple[str, ...]]:
  make = get_cell(row, col_map, "make")
  raw_model = get_cell(row, col_map, "model")
  package = get_cell(row, col_map, "package_requirements")

  missing_required_fields = []
  if not make:
    missing_required_fields.append("make")
  if not raw_model:
    missing_required_fields.append("model")
  if not package:
    missing_required_fields.append("package_requirements")
  if missing_required_fields:
    return None, tuple(missing_required_fields)

  model = clean_model(raw_model)
  support_text = get_cell(row, col_map, "support_level")

  return {
    "name": f"{make} {raw_model}",
    "make": make,
    "model": model,
    "model_original": raw_model,
    "index_key": build_index_key(make, model),
    "variant_info": extract_variant_info(raw_model),
    "years": extract_years(raw_model),
    "package_requirements": package,
    "package_key_used": None,
    "match_confidence": None,
    "matching_keywords": None,
    "support_level": parse_support_level(support_text),
  }, ()


def enrich_with_package_info(car: CarVariant, package_keywords: dict[str, dict]) -> None:
  lookup_key = make_package_key(car["package_requirements"], car["variant_info"])
  package_config = package_keywords.get(lookup_key)
  car["match_confidence"] = package_config["confidence"] if package_config else None
  car["matching_keywords"] = package_config["keywords"] if package_config else None
  car["package_key_used"] = lookup_key if package_config else None


def find_first_compatible_table_header(lines: list[str]) -> tuple[dict[str, int], int]:
  for index, line in enumerate(lines):
    if not is_table_row(line):
      continue
    col_map = map_columns(parse_row(line), EXTRACT_COLUMNS)
    if "make" in col_map and "model" in col_map:
      return col_map, index
  raise ValueError("No table with Make and Model columns found.")


def parse_cars_from_markdown(input_path: Path, package_keywords: dict) -> list[CarVariant]:
  lines = input_path.read_text().splitlines()
  col_map, header_index = find_first_compatible_table_header(lines)

  cars = []
  row_validation_errors = []

  for row_number, text_line in enumerate(lines[header_index + 1:], start=header_index + 2):
    if not text_line.startswith("|"):
      break
    if not is_table_row(text_line):
      continue

    row_cells = parse_row(text_line)
    car, missing_required_fields = parse_car_from_table_row(row_cells, col_map)
    if missing_required_fields:
      missing_fields_text = ", ".join(missing_required_fields)
      row_validation_errors.append(
        f"row {row_number} missing: {missing_fields_text}. row={row_cells}"
      )
      continue

    enrich_with_package_info(car, package_keywords)
    cars.append(car)

  if row_validation_errors:
    formatted_errors = "\n".join(f"  - {error}" for error in row_validation_errors)
    raise RowValidationError(
      "Every car must include make, model, and package_requirements.\n"
      f"{formatted_errors}"
    )

  return cars


def find_package_errors(cars: list[dict], package_keywords: dict) -> tuple[set[str], set[str]]:
  used_package_keys = set()
  missing_package_keys = set()

  for car in cars:
    key = car.get("package_key_used")
    if key:
      used_package_keys.add(key)
    if car.get("match_confidence") is None:
      missing_package_keys.add(
        make_package_key(car["package_requirements"], car["variant_info"])
      )

  unused_package_keys = set(package_keywords.keys()) - used_package_keys
  return unused_package_keys, missing_package_keys


def build_package_error_messages(unused_package_keys: set[str], missing_package_keys: set[str]) -> list[str]:
  lines = []

  if unused_package_keys:
    lines.append("")
    lines.append("⚠ Warning: Package(s) below are NOT used by any car!")
    lines.append("   Remove the following from package_keywords.json:")
    for pkg in sorted(unused_package_keys):
      lines.append(f"   - \"{pkg}\"")

  if missing_package_keys:
    lines.append("")
    lines.append("⚠ Warning: Missing package definition(s)!")
    lines.append("   Add the below to package_keywords.json:")
    for key in sorted(missing_package_keys):
      lines.append(f"   - \"{key}\"")

  if lines:
    lines.append("")
    lines.append("❌ Error: Data validation failed. Please fix the issues above.")

  return lines


def compute_stats(cars: list[dict]) -> dict:
  by_make = {}
  for car in cars:
    make = car["make"]
    count = len(car["years"])
    by_make[make] = by_make.get(make, 0) + count

  return {
    "total_cars": sum(by_make.values()),
    "total_by_make": dict(sorted(by_make.items()))
  }


def build_output_data(cars: list[dict], source_filename: str) -> dict:
  return {
    "_metadata": {
      "warning": "AUTO-GENERATED FILE - DO NOT EDIT MANUALLY",
      "generator": "markdown_to_json.py",
      "source": source_filename
    },
    "stats": compute_stats(cars),
    "cars": cars
  }


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("--input", "-i", type=Path, default=DEFAULT_INPUT)
  parser.add_argument("--output", "-o", type=Path, default=DEFAULT_OUTPUT)
  parser.add_argument("--validate-only", action="store_true")
  args = parser.parse_args()

  package_keywords = load_package_keywords()

  validation_errors = validate_package_keywords(package_keywords)
  if validation_errors:
    print("\n❌ Error: Invalid package_keywords.json structure!")
    print("   Fix the following issues:\n")
    for error in validation_errors:
      print(f"   • {error}")
    print()
    sys.exit(1)

  try:
    cars = parse_cars_from_markdown(args.input, package_keywords)
  except RowValidationError as error:
    print(f"\n❌ Error: {error}\n")
    sys.exit(1)

  unused_package_keys, missing_package_keys = find_package_errors(cars, package_keywords)
  if args.validate_only:
    unused_package_keys = set()
  package_error_lines = build_package_error_messages(unused_package_keys, missing_package_keys)
  if package_error_lines:
    print("\n".join(package_error_lines))
    sys.exit(1)

  if args.validate_only:
    print(f"✓ Validation passed: {args.input.name} ({len(cars)} vehicles)")
    return

  output_data = build_output_data(cars, args.input.name)
  args.output.write_text(json.dumps(output_data, indent=2))
  print(f"✓ Processed {len(cars)} vehicles from {args.input.name}")


if __name__ == "__main__":
  main()
