#!/usr/bin/env python3
"""
Türkiye POI verilerini Overpass API'den çeker — tam Türkiye sorgusu (hızlı).
"""
import requests, json, os, time, sys

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "poi")
os.makedirs(DATA_DIR, exist_ok=True)

TIMEOUT = 300  # 5 dakika


HEADERS = {
    "User-Agent": "TurkiyeGIS-GraduationProject/1.0 (educational use)",
    "Content-Type": "application/x-www-form-urlencoded",
}

def query(ql: str) -> list:
    resp = requests.post(
        OVERPASS_URL,
        data={"data": ql},
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json().get("elements", [])


def to_geojson(elements: list) -> dict:
    features = []
    for el in elements:
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lon = el.get("lon") or (el.get("center") or {}).get("lon")
        if lat is None or lon is None:
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {"osm_id": el.get("id"), "osm_type": el.get("type"), **el.get("tags", {})}
        })
    return {"type": "FeatureCollection", "features": features}


def save(path: str, geojson: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, separators=(',', ':'))
    print(f"  Saved {len(geojson['features'])} features → {os.path.basename(path)}")


def fetch(label: str, path: str, ql: str):
    if os.path.exists(path):
        with open(path) as f:
            existing = json.load(f)
        if len(existing.get("features", [])) > 50:
            print(f"  [SKIP] {label} — already has {len(existing['features'])} features")
            return
    print(f"  Fetching {label}...")
    try:
        elements = query(ql)
        gj = to_geojson(elements)
        save(path, gj)
    except Exception as e:
        print(f"  [ERROR] {label}: {e}")
    time.sleep(4)  # rate limit


TR = 'area["ISO3166-1"="TR"]->.tr;'

QUERIES = [
    ("Camiler / Mescidler", os.path.join(DATA_DIR, "mosques_turkey.geojson"), f"""
[out:json][timeout:{TIMEOUT}];
{TR}
(
  node["amenity"="place_of_worship"]["religion"="muslim"](area.tr);
  way["amenity"="place_of_worship"]["religion"="muslim"](area.tr);
);
out center qt;
"""),
    ("Kiliseler", os.path.join(DATA_DIR, "churches_turkey.geojson"), f"""
[out:json][timeout:{TIMEOUT}];
{TR}
(
  node["amenity"="place_of_worship"]["religion"~"christian"](area.tr);
  way["amenity"="place_of_worship"]["religion"~"christian"](area.tr);
);
out center qt;
"""),
    ("Diğer İbadethaneler", os.path.join(DATA_DIR, "worship_other_turkey.geojson"), f"""
[out:json][timeout:{TIMEOUT}];
{TR}
(
  node["amenity"="place_of_worship"]["religion"!="muslim"]["religion"!~"christian"](area.tr);
  way["amenity"="place_of_worship"]["religion"!="muslim"]["religion"!~"christian"](area.tr);
);
out center qt;
"""),
    ("Üniversiteler", os.path.join(DATA_DIR, "universities_turkey.geojson"), f"""
[out:json][timeout:{TIMEOUT}];
{TR}
(
  node["amenity"~"university|college"](area.tr);
  way["amenity"~"university|college"](area.tr);
);
out center qt;
"""),
    ("Anaokulları", os.path.join(DATA_DIR, "kindergartens_turkey.geojson"), f"""
[out:json][timeout:{TIMEOUT}];
{TR}
(
  node["amenity"="kindergarten"](area.tr);
  way["amenity"="kindergarten"](area.tr);
);
out center qt;
"""),
    ("Okullar", os.path.join(DATA_DIR, "schools_turkey.geojson"), f"""
[out:json][timeout:{TIMEOUT}];
{TR}
(
  node["amenity"="school"](area.tr);
  way["amenity"="school"](area.tr);
);
out center qt;
"""),
]

if __name__ == "__main__":
    print("=== Türkiye POI Veri Çekici ===")
    for label, path, ql in QUERIES:
        print(f"\n[{label}]")
        fetch(label, path, ql)
    print("\nTamamlandı.")
