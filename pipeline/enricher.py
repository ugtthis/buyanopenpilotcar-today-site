#!/usr/bin/env python3
import json
import sys
from pathlib import Path


DATA_DIR = Path("data")
INPUT_FILE = DATA_DIR / "ref" / "opendbc_ref.json"
METADATA_FILE = DATA_DIR / "ref" / "opendbc_metadata_ref.json"
SUPPORT_SPEC_FIELDS = (
  "longitudinal",
  "fsr_longitudinal",
  "fsr_steering",
  "experimental_longitudinal_available",
  "openpilot_longitudinal_control",
  "steering_torque",
  "auto_resume_star",
)


def build_name_index(metadata_entries: list[dict]) -> dict[str, dict]:
  name_index = {}

  for entry in metadata_entries:
    name = entry["name"]
    if name in name_index:
      raise ValueError(f"Duplicate metadata name: {name}")
    name_index[name] = entry

  return name_index


def build_support_specs(metadata_entry: dict) -> dict:
  specs = {}
  metadata_name = metadata_entry.get("name", "<missing name>")

  for field in SUPPORT_SPEC_FIELDS:
    if field not in metadata_entry or metadata_entry[field] is None:
      raise ValueError(f"Metadata entry '{metadata_name}' is missing required support spec field: {field}")
    specs[field] = metadata_entry[field]

  return specs


def enrich_ref_data(reference_data: dict, metadata_entries: list[dict]) -> int:
  name_index = build_name_index(metadata_entries)
  missing_names = []
  for entry in reference_data["cars"]:
    metadata_entry = name_index.get(entry["name"])
    if metadata_entry is None:
      missing_names.append(entry["name"])
      continue

    entry["support_specs"] = build_support_specs(metadata_entry)

  if missing_names:
    missing_list = "\n".join(f"  - {name}" for name in missing_names)
    raise ValueError(
      f"{len(missing_names)} ref car(s) missing from metadata:\n"
      f"{missing_list}"
    )

  return len(reference_data["cars"])


def main():
  if not INPUT_FILE.exists():
    print(f"❌ Error: {INPUT_FILE} not found!", flush=True)
    sys.exit(1)
  if not METADATA_FILE.exists():
    print(f"❌ Error: {METADATA_FILE} not found!", flush=True)
    sys.exit(1)

  print(f"📋 Loading reference data from {INPUT_FILE}", flush=True)
  with open(INPUT_FILE) as f:
    reference_data = json.load(f)
  print(f"✅ Loaded {len(reference_data['cars'])} reference car entries", flush=True)

  print(f"📋 Loading metadata from {METADATA_FILE}", flush=True)
  with open(METADATA_FILE) as f:
    metadata_entries = json.load(f)
  print(f"✅ Loaded {len(metadata_entries)} metadata entries", flush=True)

  print("🔗 Joining support specs...", flush=True)
  enriched_count = enrich_ref_data(reference_data, metadata_entries)

  print(f"💾 Writing enriched output to {INPUT_FILE}", flush=True)
  with open(INPUT_FILE, "w") as f:
    json.dump(reference_data, f, indent=2)

  print("✅ Enrichment complete", flush=True)
  print(f"   Enriched entries: {enriched_count}", flush=True)


if __name__ == "__main__":
  try:
    main()
  except KeyboardInterrupt:
    print("\n⚠️  Interrupted", flush=True)
    sys.exit(1)
  except Exception as e:
    print(f"\n❌ Error: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)
