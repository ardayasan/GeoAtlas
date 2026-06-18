#!/usr/bin/env python3
"""
Overpass API'den ülke bazlı POI verilerini (cami, okul, kilise vb.) çeker
ve data/poi/ klasörüne GeoJSON olarak kaydeder. Türkiye için mevcut eski
dosya adları korunur; diğer ülkeler data/poi/europe/{COUNTRY}/{category}.geojson
altına yazılır.

Kullanım:
    python scripts/fetch_overpass.py [--country TR] [--category all|mosques|schools|churches]

Notlar:
- Tüm Türkiye sorgusunu tek seferde çekmek timeout verebilir.
- Bu script il bbox'larına bölerek çeker (yavaş ama güvenilir).
- Her kategori ayrı ayrı çekilebilir.
"""

import requests
import json
import os
import time
import argparse
import sys

# overpass-api.de ana sunucusu ülke-çapı sorgularda sık timeout veriyor;
# varsayılan olarak daha hızlı kumi.systems mirror'ı kullanılır.
# OVERPASS_URL ortam değişkeniyle değiştirilebilir.
OVERPASS_URL = os.environ.get(
    "OVERPASS_URL", "https://overpass-api.de/api/interpreter")
REQUEST_TIMEOUT = int(os.environ.get("OVERPASS_TIMEOUT", "180"))
# Public Overpass, varsayılan python-requests UA'sını 406 ile reddediyor;
# tanımlı bir User-Agent şart.
HTTP_HEADERS = {
    "User-Agent": "TR-GIS-Project/1.0 (graduation project; OSM POI fetch)",
    "Accept": "application/json",
}
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "poi")
os.makedirs(DATA_DIR, exist_ok=True)

LEGACY_TR_FILES = {
    "mosques": "mosques_turkey.geojson",
    "churches": "churches_turkey.geojson",
    "worship_other": "worship_other_turkey.geojson",
    "schools": "schools_turkey.geojson",
    "universities": "universities_turkey.geojson",
    "kindergartens": "kindergartens_turkey.geojson",
}

# Türkiye il merkezleri ve yaklaşık bbox'ları
# Format: (il_adi, min_lat, min_lon, max_lat, max_lon)
TURKEY_PROVINCES_BBOX = [
    ("Adana",       36.5, 35.0, 38.0, 36.5),
    ("Adıyaman",    37.4, 37.5, 38.2, 38.8),
    ("Afyonkarahisar", 38.0, 29.8, 39.2, 31.2),
    ("Ağrı",        39.0, 42.5, 40.0, 44.5),
    ("Amasya",      40.2, 35.0, 41.0, 36.2),
    ("Ankara",      39.0, 31.5, 40.5, 33.5),
    ("Antalya",     36.0, 29.0, 37.8, 32.5),
    ("Artvin",      40.8, 41.0, 41.5, 42.5),
    ("Aydın",       37.3, 27.0, 38.3, 28.8),
    ("Balıkesir",   39.0, 26.5, 40.2, 28.8),
    ("Bilecik",     39.8, 29.5, 40.5, 30.5),
    ("Bingöl",      38.5, 40.0, 39.5, 41.5),
    ("Bitlis",      38.0, 42.0, 38.8, 43.0),
    ("Bolu",        40.2, 30.5, 41.2, 32.0),
    ("Burdur",      37.0, 29.5, 38.0, 30.5),
    ("Bursa",       39.8, 28.0, 40.5, 30.0),
    ("Çanakkale",   39.5, 25.8, 40.6, 27.5),
    ("Çankırı",     40.0, 32.5, 41.0, 34.0),
    ("Çorum",       40.0, 34.0, 41.0, 35.5),
    ("Denizli",     37.2, 28.5, 38.5, 30.0),
    ("Diyarbakır",  37.5, 39.0, 38.5, 41.0),
    ("Edirne",      41.0, 26.0, 42.0, 27.0),
    ("Elazığ",      38.2, 38.5, 39.3, 40.0),
    ("Erzincan",    39.0, 38.5, 40.0, 40.5),
    ("Erzurum",     39.5, 40.5, 41.0, 42.5),
    ("Eskişehir",   39.0, 30.0, 40.0, 31.5),
    ("Gaziantep",   36.8, 36.5, 37.5, 38.0),
    ("Giresun",     40.2, 38.0, 41.0, 39.0),
    ("Gümüşhane",   40.0, 39.0, 41.0, 40.0),
    ("Hakkari",     37.0, 43.0, 38.0, 44.5),
    ("Hatay",       36.0, 35.8, 37.0, 36.7),
    ("Isparta",     37.5, 30.0, 38.5, 31.5),
    ("Mersin",      36.0, 32.8, 37.5, 35.0),
    ("İstanbul",    40.8, 27.9, 41.5, 29.5),
    ("İzmir",       37.8, 26.5, 38.8, 28.0),
    ("Kars",        40.0, 42.5, 41.0, 43.5),
    ("Kastamonu",   41.0, 33.0, 42.0, 35.0),
    ("Kayseri",     38.0, 35.0, 39.5, 37.0),
    ("Kırklareli",  41.5, 26.5, 42.0, 28.0),
    ("Kırşehir",    39.0, 33.5, 39.8, 34.5),
    ("Kocaeli",     40.5, 29.5, 41.0, 30.5),
    ("Konya",       37.0, 31.5, 39.5, 34.5),
    ("Kütahya",     38.5, 28.8, 39.8, 30.5),
    ("Malatya",     37.8, 37.5, 39.0, 39.0),
    ("Manisa",      38.2, 27.0, 39.5, 28.8),
    ("Kahramanmaraş", 37.0, 36.0, 38.2, 37.8),
    ("Mardin",      37.0, 40.0, 37.8, 41.5),
    ("Muğla",       36.5, 27.8, 37.8, 29.5),
    ("Muş",         38.5, 40.5, 39.5, 42.0),
    ("Nevşehir",    38.3, 34.0, 39.0, 35.0),
    ("Niğde",       37.5, 34.0, 38.5, 35.5),
    ("Ordu",        40.5, 37.0, 41.2, 38.5),
    ("Rize",        40.8, 40.5, 41.5, 41.5),
    ("Sakarya",     40.5, 30.0, 41.0, 31.0),
    ("Samsun",      41.0, 35.5, 41.8, 37.5),
    ("Siirt",       37.5, 41.5, 38.5, 42.5),
    ("Sinop",       41.5, 34.5, 42.2, 36.0),
    ("Sivas",       38.5, 36.0, 40.0, 38.5),
    ("Tekirdağ",    40.5, 26.5, 41.5, 28.0),
    ("Tokat",       39.8, 35.5, 40.8, 37.0),
    ("Trabzon",     40.5, 38.5, 41.5, 40.0),
    ("Tunceli",     38.8, 39.0, 39.8, 40.5),
    ("Şanlıurfa",   36.8, 38.0, 38.0, 40.0),
    ("Uşak",        38.2, 28.8, 39.0, 29.8),
    ("Van",         37.8, 43.0, 39.5, 44.5),
    ("Yozgat",      39.0, 34.5, 40.2, 36.5),
    ("Zonguldak",   41.0, 31.5, 42.0, 32.5),
    ("Aksaray",     38.0, 33.5, 39.0, 34.5),
    ("Bayburt",     40.0, 40.0, 41.0, 40.8),
    ("Karaman",     36.8, 32.5, 37.8, 34.0),
    ("Kırıkkale",   39.5, 33.3, 40.0, 34.0),
    ("Batman",      37.5, 41.0, 38.0, 42.0),
    ("Şırnak",      37.0, 42.0, 37.8, 43.5),
    ("Bartın",      41.3, 32.0, 42.0, 33.0),
    ("Ardahan",     40.8, 42.5, 41.5, 43.5),
    ("Iğdır",       39.5, 43.5, 40.0, 44.5),
    ("Yalova",      40.5, 29.0, 40.8, 29.5),
    ("Karabük",     41.0, 32.5, 41.5, 33.5),
    ("Kilis",       36.5, 37.0, 37.0, 37.5),
    ("Osmaniye",    36.8, 36.0, 37.5, 36.8),
    ("Düzce",       40.5, 30.8, 41.2, 31.5),
]


def overpass_query(query: str, retries: int = 3) -> dict:
    """Overpass API'ye sorgu gönder."""
    for attempt in range(retries):
        try:
            resp = requests.post(
                OVERPASS_URL,
                data={"data": query},
                headers=HTTP_HEADERS,
                timeout=REQUEST_TIMEOUT
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt < retries - 1:
                print(f"  Hata: {e}. {3}s sonra tekrar deneniyor...")
                time.sleep(3)
            else:
                raise


def osm_to_geojson(elements: list) -> dict:
    """OSM element listesini GeoJSON FeatureCollection'a çevir."""
    features = []
    for el in elements:
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if lat is None or lon is None:
            continue
        feature = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "osm_id": el.get("id"),
                "osm_type": el.get("type"),
                **el.get("tags", {})
            }
        }
        features.append(feature)
    return {"type": "FeatureCollection", "features": features}


def output_path(category: str, country: str) -> str:
    country = country.upper()
    if country == "TR":
        return os.path.join(DATA_DIR, LEGACY_TR_FILES[category])
    out_dir = os.path.join(DATA_DIR, "europe", country)
    os.makedirs(out_dir, exist_ok=True)
    return os.path.join(out_dir, f"{category}.geojson")


def write_geojson(category: str, country: str, elements: list):
    path = output_path(category, country)
    geojson = osm_to_geojson(elements)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False)
    print(f"✓ {country} / {category}: {len(geojson['features'])} kayıt kaydedildi → {path}")


# Ülke alanı (area["ISO3166-1"]) hesabı büyük ülkelerde Overpass'ta timeout
# verdiğinden, sorgular bounding box ile yapılır (alan hesabı yok → çok daha hızlı).
# Bazı ülkelerin NUTS index bbox'ı denizaşırı topraklar yüzünden devasa olur
# (FR: Guyana/Réunion, NL: Karayipler, ES: Kanarya, PT: Azor); bu ülkeler için
# anakara bbox'ı kullanılır. Format: (güney_lat, batı_lon, kuzey_lat, doğu_lon).
CONTINENTAL_BBOX = {
    "FR": (41.3, -5.2, 51.1, 9.6),     # metropol Fransa
    "NL": (50.7, 3.3, 53.6, 7.3),      # Avrupa Hollanda
    "ES": (35.9, -9.4, 43.8, 4.4),     # İber yarımadası (Kanarya hariç)
    "PT": (36.9, -9.6, 42.2, -6.2),    # anakara Portekiz
    "NO": (57.9, 4.5, 71.2, 31.2),     # Norveç anakara
}

NUTS_INDEX = os.path.join(
    os.path.dirname(__file__), "..", "data", "boundaries", "nuts", "index.json")


def country_bbox(country: str):
    """Ülke için Overpass bbox'ı (güney,batı,kuzey,doğu) döner."""
    country = country.upper()
    if country in CONTINENTAL_BBOX:
        return CONTINENTAL_BBOX[country]
    with open(NUTS_INDEX, encoding="utf-8") as f:
        idx = json.load(f)
    meta = idx.get(country)
    bbox = meta.get("bbox") if isinstance(meta, dict) else meta
    if not bbox or len(bbox) != 4:
        raise ValueError(f"{country} için bbox bulunamadı (NUTS index).")
    min_lon, min_lat, max_lon, max_lat = bbox
    return (min_lat, min_lon, max_lat, max_lon)


def fetch_area_category(category: str, country: str):
    """Türkiye dışı ülkelerde bounding box üzerinden tek kategori çeker."""
    country = country.upper()
    path = output_path(category, country)
    if os.path.exists(path):
        print(f"Zaten mevcut: {path}")
        return

    s, w, n, e = country_bbox(country)
    bb = f"{s},{w},{n},{e}"
    category_queries = {
        "mosques": f"""
  node["amenity"="place_of_worship"]["religion"="muslim"]({bb});
  way["amenity"="place_of_worship"]["religion"="muslim"]({bb});
""",
        "schools": f"""
  node["amenity"="school"]({bb});
  way["amenity"="school"]({bb});
""",
        "kindergartens": f"""
  node["amenity"="kindergarten"]({bb});
  way["amenity"="kindergarten"]({bb});
""",
        "universities": f"""
  node["amenity"="university"]({bb});
  way["amenity"="university"]({bb});
  node["amenity"="college"]({bb});
  way["amenity"="college"]({bb});
""",
    }
    if category not in category_queries:
        raise ValueError(f"Bu kategori ayrı çekilemiyor: {category}")

    print(f"\n{country} / {category} çekiliyor... (bbox {bb})")
    query = f"""
[out:json][timeout:180];
(
{category_queries[category]}
);
out center;
"""
    data = overpass_query(query)
    write_geojson(category, country, data.get("elements", []))


def fetch_area_worship(country: str):
    """Türkiye dışı ülkelerde kilise ve diğer ibadethaneleri birlikte çeker."""
    country = country.upper()
    churches_path = output_path("churches", country)
    other_path = output_path("worship_other", country)
    if os.path.exists(churches_path) and os.path.exists(other_path):
        print(f"Zaten mevcut: {churches_path}")
        print(f"Zaten mevcut: {other_path}")
        return

    s, w, n, e = country_bbox(country)
    bb = f"{s},{w},{n},{e}"
    print(f"\n{country} / kilise ve diğer ibadethaneler çekiliyor... (bbox {bb})")
    query = f"""
[out:json][timeout:180];
(
  node["amenity"="place_of_worship"]["religion"!="muslim"]({bb});
  way["amenity"="place_of_worship"]["religion"!="muslim"]({bb});
);
out center;
"""
    data = overpass_query(query)
    churches = []
    others = []
    for el in data.get("elements", []):
        religion = el.get("tags", {}).get("religion", "")
        if religion in ("christian", "christian_catholic", "christian_orthodox"):
            churches.append(el)
        else:
            others.append(el)
    write_geojson("churches", country, churches)
    write_geojson("worship_other", country, others)


def fetch_mosques():
    """Türkiye'deki cami ve mescidleri çek."""
    output_path = os.path.join(DATA_DIR, "mosques_turkey.geojson")
    if os.path.exists(output_path):
        print(f"Zaten mevcut: {output_path}")
        return

    print("\nCami ve Mescidler çekiliyor...")
    all_elements = []

    for province, min_lat, min_lon, max_lat, max_lon in TURKEY_PROVINCES_BBOX:
        query = f"""
[out:json][timeout:60];
(
  node["amenity"="place_of_worship"]["religion"="muslim"]({min_lat},{min_lon},{max_lat},{max_lon});
  way["amenity"="place_of_worship"]["religion"="muslim"]({min_lat},{min_lon},{max_lat},{max_lon});
);
out center;
"""
        try:
            data = overpass_query(query)
            elements = data.get("elements", [])
            all_elements.extend(elements)
            print(f"  {province}: {len(elements)} kayıt")
        except Exception as e:
            print(f"  {province}: HATA - {e}")
        time.sleep(2)

    geojson = osm_to_geojson(all_elements)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False)
    print(f"✓ Toplam {len(geojson['features'])} cami/mescid kaydedildi → {output_path}")


def fetch_churches():
    """Türkiye'deki kiliseleri çek."""
    output_path = os.path.join(DATA_DIR, "churches_turkey.geojson")
    other_path = os.path.join(DATA_DIR, "worship_other_turkey.geojson")
    if os.path.exists(output_path):
        print(f"Zaten mevcut: {output_path}")
        return

    print("\nKiliseler ve diğer ibadethaneler çekiliyor...")
    churches = []
    others = []

    query = """
[out:json][timeout:120];
area["ISO3166-1"="TR"]->.tr;
(
  node["amenity"="place_of_worship"]["religion"!="muslim"](area.tr);
  way["amenity"="place_of_worship"]["religion"!="muslim"](area.tr);
);
out center;
"""
    try:
        data = overpass_query(query)
        for el in data.get("elements", []):
            religion = el.get("tags", {}).get("religion", "")
            if religion in ("christian", "christian_catholic", "christian_orthodox"):
                churches.append(el)
            else:
                others.append(el)
        print(f"  Kilise: {len(churches)}, Diğer: {len(others)}")
    except Exception as e:
        print(f"  HATA: {e}")

    for path, elements in [(output_path, churches), (other_path, others)]:
        geojson = osm_to_geojson(elements)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(geojson, f, ensure_ascii=False)
    print(f"✓ Kilise ve diğer ibadet yerleri kaydedildi.")


def fetch_schools():
    """Türkiye'deki okulları çek (ilkokul, ortaokul, lise, anaokulu)."""
    output_path = os.path.join(DATA_DIR, "schools_turkey.geojson")
    if os.path.exists(output_path):
        print(f"Zaten mevcut: {output_path}")
        return

    print("\nOkullar çekiliyor...")
    all_elements = []

    for province, min_lat, min_lon, max_lat, max_lon in TURKEY_PROVINCES_BBOX:
        query = f"""
[out:json][timeout:60];
(
  node["amenity"="school"]({min_lat},{min_lon},{max_lat},{max_lon});
  way["amenity"="school"]({min_lat},{min_lon},{max_lat},{max_lon});
  node["amenity"="kindergarten"]({min_lat},{min_lon},{max_lat},{max_lon});
  way["amenity"="kindergarten"]({min_lat},{min_lon},{max_lat},{max_lon});
);
out center;
"""
        try:
            data = overpass_query(query)
            elements = data.get("elements", [])
            all_elements.extend(elements)
            print(f"  {province}: {len(elements)} kayıt")
        except Exception as e:
            print(f"  {province}: HATA - {e}")
        time.sleep(2)

    geojson = osm_to_geojson(all_elements)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False)
    print(f"✓ Toplam {len(geojson['features'])} okul kaydedildi → {output_path}")


def fetch_universities():
    """Türkiye'deki üniversiteleri çek."""
    output_path = os.path.join(DATA_DIR, "universities_turkey.geojson")
    if os.path.exists(output_path):
        print(f"Zaten mevcut: {output_path}")
        return

    print("\nÜniversiteler çekiliyor...")

    query = """
[out:json][timeout:120];
area["ISO3166-1"="TR"]->.tr;
(
  node["amenity"="university"](area.tr);
  way["amenity"="university"](area.tr);
  node["amenity"="college"](area.tr);
  way["amenity"="college"](area.tr);
);
out center;
"""
    try:
        data = overpass_query(query)
        elements = data.get("elements", [])
        geojson = osm_to_geojson(elements)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(geojson, f, ensure_ascii=False)
        print(f"✓ {len(geojson['features'])} üniversite kaydedildi → {output_path}")
    except Exception as e:
        print(f"  HATA: {e}")


def fetch_kindergartens():
    """Anaokulu / kreş verilerini schools'dan ayır."""
    schools_path = os.path.join(DATA_DIR, "schools_turkey.geojson")
    kg_path = os.path.join(DATA_DIR, "kindergartens_turkey.geojson")

    if not os.path.exists(schools_path):
        print("Önce okulları çekiniz (--category schools)")
        return
    if os.path.exists(kg_path):
        print(f"Zaten mevcut: {kg_path}")
        return

    with open(schools_path, "r", encoding="utf-8") as f:
        schools = json.load(f)

    kg_features = [
        f for f in schools["features"]
        if f["properties"].get("amenity") == "kindergarten"
    ]
    geojson = {"type": "FeatureCollection", "features": kg_features}
    with open(kg_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False)
    print(f"✓ {len(kg_features)} anaokulu ayrıştırıldı → {kg_path}")


def main():
    parser = argparse.ArgumentParser(description="Overpass API POI veri çekici")
    parser.add_argument(
        "--country",
        default="TR",
        help="ISO 3166-1 alpha-2 ülke kodu (varsayılan: TR)"
    )
    parser.add_argument(
        "--category",
        choices=["all", "mosques", "schools", "churches", "worship_other", "universities", "kindergartens"],
        default="all",
        help="Hangi kategoriyi çekeceğinizi seçin (varsayılan: all)"
    )
    args = parser.parse_args()
    country = args.country.strip().upper()

    print("=" * 60)
    print(f"{country} POI Veri Çekici (Overpass API)")
    print("=" * 60)
    print("Not: Bu işlem ağ hızınıza bağlı olarak uzun sürebilir.")
    if country != "TR":
        print("Not: Büyük ülkeler/kategoriler için public Overpass yavaşlayabilir; üretimde Geofabrik extract önerilir.")

    cat = args.category
    if country == "TR":
        if cat in ("all", "mosques"):
            fetch_mosques()
        if cat in ("all", "churches", "worship_other"):
            fetch_churches()
        if cat in ("all", "schools"):
            fetch_schools()
        if cat in ("all", "universities"):
            fetch_universities()
        if cat in ("all", "kindergartens"):
            fetch_kindergartens()
    else:
        if cat in ("all", "mosques"):
            fetch_area_category("mosques", country)
        if cat in ("all", "churches", "worship_other"):
            fetch_area_worship(country)
        if cat in ("all", "schools"):
            fetch_area_category("schools", country)
        if cat in ("all", "universities"):
            fetch_area_category("universities", country)
        if cat in ("all", "kindergartens"):
            fetch_area_category("kindergartens", country)

    print("\n✓ İşlem tamamlandı!")


if __name__ == "__main__":
    main()
