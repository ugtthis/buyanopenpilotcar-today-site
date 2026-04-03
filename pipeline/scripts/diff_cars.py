#!/usr/bin/env python3

import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from markdown_to_json import parse_cars_from_markdown, RowValidationError


CARS_FILE = Path("data/ref/CARS.md")
SUMMARY_FILE = Path(".github/cars-sync-summary.md")
HEALTHY_STATE = "healthy"
DEGRADED_STATE = "degraded"


def load_old_cars():
  result = subprocess.run(
    ["git", "show", f"HEAD:{CARS_FILE}"],
    capture_output=True,
    text=True,
  )
  if result.returncode != 0:
    return []
  with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
    f.write(result.stdout)
    tmp_path = Path(f.name)
  try:
    return parse_cars_from_markdown(tmp_path, {})
  except (RowValidationError, ValueError):
    return []
  finally:
    tmp_path.unlink()


def car_key(car):
  return (car["make"], car["model_original"], car["package_requirements"])


def compare_cars(old_cars, new_cars):
  old_by_key = {car_key(c): c for c in old_cars}
  new_by_key = {car_key(c): c for c in new_cars}

  if len(old_by_key) != len(old_cars):
    raise ValueError("Duplicate car keys in old CARS.md")
  if len(new_by_key) != len(new_cars):
    raise ValueError("Duplicate car keys in new CARS.md")

  added = [new_by_key[k] for k in new_by_key if k not in old_by_key]
  removed = [old_by_key[k] for k in old_by_key if k not in new_by_key]
  changed = [
    (old_by_key[k], new_by_key[k])
    for k in old_by_key.keys() & new_by_key.keys()
    if old_by_key[k]["support_level"] != new_by_key[k]["support_level"]
  ]
  return added, removed, changed


def car_label(car):
  return f"{car['make']} {car['model_original']} ({car['package_requirements']})"


def build_summary(added, removed, changed):
  lines = ["## CARS.md Sync", ""]
  lines.append(f"**Added:** {len(added)} | **Removed:** {len(removed)} | **Support changes:** {len(changed)}")

  if added:
    lines += ["", "### New cars"] + [f"- {car_label(c)}" for c in sorted(added, key=car_key)]

  if removed:
    lines += ["", "### Removed cars"] + [f"- {car_label(c)}" for c in sorted(removed, key=car_key)]

  if changed:
    lines += ["", "### Support level changes"]
    for old, new in sorted(changed, key=lambda x: car_key(x[0])):
      lines.append(f"- {car_label(old)}: {old['support_level']} → {new['support_level']}")

  lines.append("")
  return "\n".join(lines)


def write_github_output(sync_state):
  github_output = os.environ.get("GITHUB_OUTPUT")
  if not github_output:
    return
  with open(github_output, "a", encoding="utf-8") as f:
    f.write(f"sync_state={sync_state}\n")


def main():
  try:
    new_cars = parse_cars_from_markdown(CARS_FILE, {})
  except (RowValidationError, ValueError) as e:
    print(f"Failed to parse new CARS.md: {e}")
    write_github_output(DEGRADED_STATE)
    sys.exit(1)

  old_cars = load_old_cars()
  added, removed, changed = compare_cars(old_cars, new_cars)

  sync_state = HEALTHY_STATE if not removed and not changed else DEGRADED_STATE

  summary = build_summary(added, removed, changed)
  SUMMARY_FILE.parent.mkdir(exist_ok=True)
  SUMMARY_FILE.write_text(summary, encoding="utf-8")

  write_github_output(sync_state)

  print(f"Added: {len(added)}, Removed: {len(removed)}, Support changes: {len(changed)}")
  print(f"Sync state: {sync_state}")


if __name__ == "__main__":
  main()
