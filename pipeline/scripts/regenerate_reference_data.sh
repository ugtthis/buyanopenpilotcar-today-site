#!/usr/bin/env bash
set -euo pipefail

uv run python markdown_to_json.py --input data/ref/CARS.md --output data/ref/opendbc_ref.json
uv run python enricher.py
