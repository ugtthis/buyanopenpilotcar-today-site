#!/bin/bash
# Complete Workflow Example
# This script demonstrates the full end-to-end pipeline

set -e  # Exit on error

echo "========================================"
echo "Openpilot CarMax Matcher - Full Workflow"
echo "========================================"

# Step 1: Scrape CarMax (optional - we already have sample data)
# echo ""
# echo "Step 1: Scraping CarMax inventory..."
# python3 scraper.py

# Step 2: Merge inventory into JSONL
echo ""
echo "Step 2: Merging inventory files..."
python3 merge_inventory.py

# Step 3: Match against supported cars
echo ""
echo "Step 3: Matching against openpilot-supported cars..."
python3 matcher.py

# Step 4: Run tests
echo ""
echo "Step 4: Running tests..."
python3 tests/test_matcher.py

# Step 5: Show sample results
echo ""
echo "Step 5: Sample results..."
python3 << 'PYTHON'
import json

with open('data/openpilot_cars.json') as f:
    data = json.load(f)

print(f"\n✅ Generated {len(data['entries'])} variant entries")
print(f"⚠️  {len(data['warnings'])} warnings")

# Show a few sample matches
rivian = next((e for e in data['entries'] if 'Rivian' in e['make']), None)
if rivian:
    print(f"\nSample: {rivian['make']} {rivian['model_original']}")
    for available in rivian.get('available_years', [])[:3]:
        car = available['car']
        print(f"  {available['year']}: ${car['basePrice']:,.0f} @ {car['mileage']:,} mi")
PYTHON

echo ""
echo "========================================"
echo "✅ Complete! Output: data/openpilot_cars.json"
echo "========================================"
