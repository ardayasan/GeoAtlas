#!/bin/bash
cd "/Users/ardayasan/Desktop/Bitirme Projesi /mapping-project"

COUNTRIES=("DE" "FR" "NL" "IT" "ES" "EL" "LU")
CATEGORIES=("schools" "kindergartens")

for c in "${COUNTRIES[@]}"; do
  for cat in "${CATEGORIES[@]}"; do
    echo "==========================================="
    echo "Fetching $cat for $c..."
    echo "==========================================="
    venv/bin/python scripts/fetch_overpass.py --country "$c" --category "$cat"
    
    # Wait 10 seconds to avoid HTTP 429 Too Many Requests from Overpass API
    sleep 10
  done
done

echo "==========================================="
echo "Filtering all downloaded POIs by boundaries..."
echo "==========================================="
venv/bin/python scripts/filter_poi_by_boundary.py

echo "All tasks completed successfully!"
