#!/usr/bin/env python3
"""
Eurostat GISCO NUTS sınırlarını indirir ve viewport yüklemeye uygun dosyalara böler.

Çıktılar:
  data/boundaries/nuts/index.json
  data/boundaries/nuts/L0/ALL.geojson
  data/boundaries/nuts/L1/{CC}.geojson
  data/boundaries/nuts/L2/{CC}.geojson
  data/boundaries/nuts/L3/{CC}.geojson
  data/boundaries/nuts/L4/TR.geojson

Türkiye için L3/L4 hibrit kullanılır:
  L3/TR.geojson = mevcut OSM il geometrileri + NUTS3 kodları
  L4/TR.geojson = mevcut OSM ilçe geometrileri + TR'ye özel LAU kodları
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from collections import defaultdict

import requests

from tr_util import IL_KODU_AD, il_nuts_code, ilce_lau_code

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BOUNDARY_DIR = os.path.join(ROOT, "data", "boundaries")
NUTS_DIR = os.path.join(BOUNDARY_DIR, "nuts")
DB_PATH = os.path.join(ROOT, "data", "db", "app.db")
YEAR = 2024

GISCO_URL = (
    "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/"
    "NUTS_RG_{res}_{year}_4326_LEVL_{level}.geojson"
)
LEVEL_RESOLUTION = {0: "20M", 1: "03M", 2: "03M", 3: "01M"}


def parent_code(code: str, level: int) -> str | None:
    if level <= 0:
        return None
    return code[: {1: 2, 2: 3, 3: 4, 4: 5}[level]]


def feature_collection(features: list[dict]) -> dict:
    return {"type": "FeatureCollection", "features": features}


def write_geojson(path: str, features: list[dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(feature_collection(features), f, ensure_ascii=False, separators=(",", ":"))


def iter_positions(geom):
    if not geom:
        return
    typ = geom.get("type")
    coords = geom.get("coordinates")
    if typ == "Point":
        yield coords
    elif typ in ("LineString", "MultiPoint"):
        yield from coords
    elif typ in ("Polygon", "MultiLineString"):
        for part in coords:
            yield from part
    elif typ == "MultiPolygon":
        for poly in coords:
            for ring in poly:
                yield from ring
    elif typ == "GeometryCollection":
        for child in geom.get("geometries", []):
            yield from iter_positions(child)


def bbox_for_features(features: list[dict]) -> list[float] | None:
    xs, ys = [], []
    for feature in features:
        for pos in iter_positions(feature.get("geometry")):
            if pos and len(pos) >= 2:
                xs.append(pos[0])
                ys.append(pos[1])
    if not xs:
        return None
    return [min(xs), min(ys), max(xs), max(ys)]


def normalize_gisco_feature(feature: dict, level: int) -> dict:
    props = feature.get("properties") or {}
    code = props.get("NUTS_ID")
    country = props.get("CNTR_CODE") or code[:2]
    name = props.get("NAME_LATN") or props.get("NUTS_NAME") or code
    return {
        "type": "Feature",
        "geometry": feature.get("geometry"),
        "properties": {
            "code": code,
            "country": country,
            "level": level,
            "parent": parent_code(code, level),
            "name_en": name,
            "name_tr": name,
            "source": "gisco",
        },
    }


def fetch_gisco(level: int) -> list[dict]:
    url = GISCO_URL.format(res=LEVEL_RESOLUTION[level], year=YEAR, level=level)
    print(f"GISCO indiriliyor: L{level} ({LEVEL_RESOLUTION[level]})")
    response = requests.get(url, timeout=180)
    response.raise_for_status()
    data = response.json()
    return [normalize_gisco_feature(f, level) for f in data.get("features", [])]


def load_geojson(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_tr_l3() -> list[dict]:
    src = os.path.join(BOUNDARY_DIR, "turkey_provinces.geojson")
    data = load_geojson(src)
    features = []
    for feature in data.get("features", []):
        props = feature.get("properties") or {}
        il_kodu = props.get("il_kodu") or props.get("province_code")
        code = il_nuts_code(il_kodu)
        if not code:
            continue
        name = props.get("il_adi") or IL_KODU_AD.get(int(il_kodu), code)
        features.append({
            "type": "Feature",
            "geometry": feature.get("geometry"),
            "properties": {
                "code": code,
                "country": "TR",
                "level": 3,
                "parent": parent_code(code, 3),
                "name_en": name,
                "name_tr": name,
                "source": "tuik",
                "il_kodu": str(il_kodu),
            },
        })
    return features


def build_tr_l4() -> list[dict]:
    src = os.path.join(BOUNDARY_DIR, "turkey_districts.geojson")
    data = load_geojson(src)
    features = []
    for feature in data.get("features", []):
        props = feature.get("properties") or {}
        il_kodu = props.get("il_kodu")
        ilce_kodu = props.get("ilce_kodu")
        code = ilce_lau_code(ilce_kodu, il_kodu)
        parent = il_nuts_code(il_kodu)
        if not code or not parent:
            continue
        name = props.get("ilce_adi") or code
        features.append({
            "type": "Feature",
            "geometry": feature.get("geometry"),
            "properties": {
                "code": code,
                "country": "TR",
                "level": 4,
                "parent": parent,
                "name_en": name,
                "name_tr": name,
                "source": "tuik",
                "il_kodu": str(il_kodu),
                "ilce_kodu": str(ilce_kodu),
            },
        })
    return features


def write_boundaries(skip_download: bool = False) -> None:
    os.makedirs(NUTS_DIR, exist_ok=True)

    if skip_download:
        print("GISCO indirme atlandı; mevcut dosyalar kullanılacak.")
        return

    levels = {level: fetch_gisco(level) for level in range(4)}

    write_geojson(os.path.join(NUTS_DIR, "L0", "ALL.geojson"), levels[0])
    print(f"✓ L0/ALL.geojson: {len(levels[0])} ülke")

    for level in (1, 2, 3):
        by_country = defaultdict(list)
        for feature in levels[level]:
            country = feature["properties"]["country"]
            if level == 3 and country == "TR":
                continue
            by_country[country].append(feature)
        if level == 3:
            by_country["TR"] = build_tr_l3()
        for country, features in sorted(by_country.items()):
            write_geojson(os.path.join(NUTS_DIR, f"L{level}", f"{country}.geojson"), features)
        print(f"✓ L{level}: {sum(len(v) for v in by_country.values())} bölge")

    tr_l4 = build_tr_l4()
    write_geojson(os.path.join(NUTS_DIR, "L4", "TR.geojson"), tr_l4)
    print(f"✓ L4/TR.geojson: {len(tr_l4)} ilçe")


def build_index() -> dict:
    l0_path = os.path.join(NUTS_DIR, "L0", "ALL.geojson")
    if not os.path.exists(l0_path):
        return {}
    l0 = load_geojson(l0_path)
    index = {}
    for feature in l0.get("features", []):
        props = feature.get("properties") or {}
        country = props.get("country") or props.get("code")
        if not country:
            continue
        levels = []
        for level in range(5):
            if level == 0:
                available = True
            else:
                available = os.path.exists(os.path.join(NUTS_DIR, f"L{level}", f"{country}.geojson"))
            if available:
                levels.append(level)
        index[country] = {
            "bbox": bbox_for_features([feature]),
            "levels": levels,
            "name_en": props.get("name_en") or country,
            "name_tr": props.get("name_tr") or props.get("name_en") or country,
        }
    with open(os.path.join(NUTS_DIR, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"✓ index.json: {len(index)} ülke")
    return index


def ensure_regions_schema(con: sqlite3.Connection) -> None:
    con.execute("""
        CREATE TABLE IF NOT EXISTS regions (
            code TEXT PRIMARY KEY,
            country TEXT NOT NULL,
            level INTEGER NOT NULL,
            parent TEXT,
            name_en TEXT,
            name_tr TEXT,
            source TEXT
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS region_stats (
            code TEXT NOT NULL,
            indicator TEXT NOT NULL,
            year INTEGER NOT NULL,
            value REAL,
            PRIMARY KEY (code, indicator, year)
        )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS idx_regions_country_level ON regions(country, level)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_regions_parent ON regions(parent)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_region_stats_indicator_year ON region_stats(indicator, year)")


def load_regions_table() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    ensure_regions_schema(con)
    con.execute("DELETE FROM regions")

    paths = [os.path.join(NUTS_DIR, "L0", "ALL.geojson")]
    for level in range(1, 5):
        level_dir = os.path.join(NUTS_DIR, f"L{level}")
        if os.path.isdir(level_dir):
            paths.extend(
                os.path.join(level_dir, name)
                for name in sorted(os.listdir(level_dir))
                if name.endswith(".geojson")
            )

    count = 0
    for path in paths:
        if not os.path.exists(path):
            continue
        data = load_geojson(path)
        for feature in data.get("features", []):
            props = feature.get("properties") or {}
            code = props.get("code")
            if not code:
                continue
            con.execute(
                """
                INSERT OR REPLACE INTO regions
                    (code, country, level, parent, name_en, name_tr, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    code,
                    props.get("country") or code[:2],
                    int(props.get("level", 0)),
                    props.get("parent"),
                    props.get("name_en"),
                    props.get("name_tr"),
                    props.get("source"),
                ),
            )
            count += 1
    con.commit()
    con.close()
    print(f"✓ regions tablosu: {count} kayıt")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-download", action="store_true", help="Sadece index ve DB yükleme yap")
    args = parser.parse_args()

    write_boundaries(skip_download=args.skip_download)
    build_index()
    load_regions_table()


if __name__ == "__main__":
    main()
