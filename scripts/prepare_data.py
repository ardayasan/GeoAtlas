#!/usr/bin/env python3
"""
Veri temizleme ve hazırlama scripti.
GeoJSON dosyalarını validate eder, gerekirse sadeleştirir.

Kullanım:
    python scripts/prepare_data.py
"""

import json
import os
import sys

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
BOUNDARIES_DIR = os.path.join(DATA_DIR, "boundaries")
POI_DIR = os.path.join(DATA_DIR, "poi")


def validate_geojson(path: str) -> dict:
    """GeoJSON dosyasını validate et ve istatistik döndür."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    valid = sum(1 for f in features if f.get("geometry") and f.get("properties") is not None)
    invalid = len(features) - valid

    return {
        "file": os.path.basename(path),
        "total_features": len(features),
        "valid": valid,
        "invalid": invalid,
        "size_mb": os.path.getsize(path) / (1024 * 1024)
    }


def remove_duplicate_poi(path: str):
    """Aynı OSM ID'ye sahip duplicate POI'ları kaldır."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    seen_ids = set()
    unique_features = []
    for feature in data.get("features", []):
        osm_id = feature.get("properties", {}).get("osm_id")
        if osm_id and osm_id in seen_ids:
            continue
        if osm_id:
            seen_ids.add(osm_id)
        unique_features.append(feature)

    removed = len(data["features"]) - len(unique_features)
    data["features"] = unique_features

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    return removed


def simplify_boundaries(path: str, tolerance: float = 0.005):
    """Sınır GeoJSON'ını shapely ile sadeleştir (boyutu küçült)."""
    try:
        from shapely.geometry import shape, mapping
    except ImportError:
        print("  shapely yüklü değil, sadeleştirme atlandı.")
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for feature in data.get("features", []):
        try:
            geom = shape(feature["geometry"])
            simplified = geom.simplify(tolerance, preserve_topology=True)
            feature["geometry"] = mapping(simplified)
        except Exception:
            continue

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def main():
    print("=" * 60)
    print("Veri Hazırlama ve Doğrulama")
    print("=" * 60)

    # Sınır dosyalarını kontrol et
    print("\n--- Sınır Dosyaları ---")
    boundary_files = [
        "turkey_provinces.geojson",
        "turkey_districts.geojson",
    ]
    for fname in boundary_files:
        path = os.path.join(BOUNDARIES_DIR, fname)
        if not os.path.exists(path):
            print(f"  ✗ Eksik: {fname} — download_boundaries.py çalıştırın")
            continue
        stats = validate_geojson(path)
        print(f"  ✓ {stats['file']}: {stats['total_features']} feature, {stats['size_mb']:.1f} MB")

        # 5 MB'dan büyükse sadeleştir
        if stats["size_mb"] > 5:
            print(f"    Sadeleştiriliyor...")
            orig_size = stats["size_mb"]
            simplify_boundaries(path)
            new_size = os.path.getsize(path) / (1024 * 1024)
            print(f"    {orig_size:.1f} MB → {new_size:.1f} MB")

    # POI dosyalarını kontrol et
    print("\n--- POI Dosyaları ---")
    poi_files = [
        "mosques_turkey.geojson",
        "churches_turkey.geojson",
        "worship_other_turkey.geojson",
        "schools_turkey.geojson",
        "universities_turkey.geojson",
        "kindergartens_turkey.geojson",
    ]
    for fname in poi_files:
        path = os.path.join(POI_DIR, fname)
        if not os.path.exists(path):
            print(f"  ✗ Eksik: {fname} — fetch_overpass.py çalıştırın")
            continue
        stats = validate_geojson(path)
        removed = remove_duplicate_poi(path)
        print(f"  ✓ {stats['file']}: {stats['total_features']} feature "
              f"({removed} duplicate kaldırıldı), {stats['size_mb']:.1f} MB")

    print("\n✓ Veri hazırlama tamamlandı!")


if __name__ == "__main__":
    main()
