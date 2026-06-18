#!/usr/bin/env python3
"""
Filter POI features so they strictly fall inside the respective country's L0 boundary.
This fixes the issue where Overpass API bounding box queries returned POIs in neighboring countries.
"""

import json
import os
import glob
from shapely.geometry import shape, Point

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
EUROPE_POI_DIR = os.path.join(DATA_DIR, "poi", "europe")
L0_BOUNDARIES_FILE = os.path.join(DATA_DIR, "boundaries", "nuts", "L0", "ALL.geojson")

def main():
    print("Loading L0 boundaries...")
    try:
        with open(L0_BOUNDARIES_FILE, "r", encoding="utf-8") as f:
            l0_data = json.load(f)
    except Exception as e:
        print(f"Error loading {L0_BOUNDARIES_FILE}: {e}")
        return

    # Create a dictionary of country code -> shapely geometry
    country_shapes = {}
    for feature in l0_data.get("features", []):
        code = feature.get("properties", {}).get("code")
        if code:
            country_shapes[code] = shape(feature["geometry"])

    print(f"Loaded geometries for {len(country_shapes)} countries.")

    # Iterate over downloaded POI countries
    if not os.path.exists(EUROPE_POI_DIR):
        print(f"Directory not found: {EUROPE_POI_DIR}")
        return

    for country in os.listdir(EUROPE_POI_DIR):
        country_dir = os.path.join(EUROPE_POI_DIR, country)
        if not os.path.isdir(country_dir):
            continue

        geom = country_shapes.get(country)
        if not geom:
            print(f"Warning: No L0 boundary found for {country}. Skipping filtering.")
            continue

        print(f"\nProcessing {country}...")
        for filepath in glob.glob(os.path.join(country_dir, "*.geojson")):
            filename = os.path.basename(filepath)
            with open(filepath, "r", encoding="utf-8") as f:
                poi_data = json.load(f)
            
            features = poi_data.get("features", [])
            initial_count = len(features)
            
            valid_features = []
            for feat in features:
                coords = feat.get("geometry", {}).get("coordinates")
                if not coords or len(coords) != 2:
                    continue
                # Shapely uses (lon, lat)
                pt = Point(coords[0], coords[1])
                if geom.contains(pt):
                    valid_features.append(feat)
            
            final_count = len(valid_features)
            
            if final_count != initial_count:
                poi_data["features"] = valid_features
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(poi_data, f, ensure_ascii=False)
                print(f"  {filename}: {initial_count} -> {final_count} (removed {initial_count - final_count} points outside {country})")
            else:
                print(f"  {filename}: all {initial_count} points are inside {country}.")

if __name__ == "__main__":
    main()
