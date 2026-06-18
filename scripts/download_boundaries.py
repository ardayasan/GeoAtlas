#!/usr/bin/env python3
"""
Türkiye il ve ilçe GeoJSON sınır verilerini indirir.
Kaynak: gadm.org ve github.com/izzetkalic/geojsons-of-turkey

Kullanım:
    python scripts/download_boundaries.py

Gerekli kütüphaneler:
    pip install requests
"""

import os
import json
import requests
import sys

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "boundaries")
os.makedirs(DATA_DIR, exist_ok=True)


def download_file(url: str, dest_path: str, desc: str = ""):
    print(f"İndiriliyor: {desc or url}")
    try:
        response = requests.get(url, stream=True, timeout=120)
        response.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        size_mb = os.path.getsize(dest_path) / (1024 * 1024)
        print(f"  ✓ Kaydedildi: {dest_path} ({size_mb:.1f} MB)")
        return True
    except Exception as e:
        print(f"  ✗ Hata: {e}")
        return False


def download_provinces():
    """İl (level 1) GeoJSON'ını indir."""
    dest = os.path.join(DATA_DIR, "turkey_provinces.geojson")
    if os.path.exists(dest):
        print(f"Zaten mevcut: {dest}")
        return True

    # GADM Turkey Level 1
    url = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_TUR_1.json"
    success = download_file(url, dest, "Türkiye İl Sınırları (GADM Level 1)")

    if success:
        # Properties'e Türkçe alan ekle
        normalize_gadm_provinces(dest)
    return success


def download_districts():
    """İlçe (level 2) GeoJSON'ını indir."""
    dest = os.path.join(DATA_DIR, "turkey_districts.geojson")
    if os.path.exists(dest):
        print(f"Zaten mevcut: {dest}")
        return True

    url = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_TUR_2.json"
    success = download_file(url, dest, "Türkiye İlçe Sınırları (GADM Level 2)")

    if success:
        normalize_gadm_districts(dest)
    return success


def normalize_gadm_provinces(path: str):
    """GADM property isimlerini uygulamaya uygun hale getir."""
    print("  İl verileri normalize ediliyor...")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for feature in data.get("features", []):
        props = feature.get("properties", {})
        # GADM alanlarını Türkçe isimlere eşle
        props["il_adi"] = props.get("NAME_1", "")
        props["il_kodu"] = props.get("GID_1", "").replace("TUR.", "").replace("_1", "")
        feature["properties"] = props

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"  ✓ Normalize edildi. {len(data.get('features', []))} il.")


def normalize_gadm_districts(path: str):
    """GADM ilçe property isimlerini normalize et."""
    print("  İlçe verileri normalize ediliyor...")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for feature in data.get("features", []):
        props = feature.get("properties", {})
        props["ilce_adi"] = props.get("NAME_2", "")
        props["il_adi"] = props.get("NAME_1", "")
        props["ilce_kodu"] = props.get("GID_2", "").replace("TUR.", "").replace("_1", "")
        # İl kodunu GID_1'den çıkar
        gid1 = props.get("GID_1", "")
        props["il_kodu"] = gid1.replace("TUR.", "").replace("_1", "")
        feature["properties"] = props

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"  ✓ Normalize edildi. {len(data.get('features', []))} ilçe.")


def main():
    print("=" * 60)
    print("Türkiye Sınır Verisi İndirici")
    print("=" * 60)

    ok1 = download_provinces()
    ok2 = download_districts()

    print()
    if ok1 and ok2:
        print("✓ Tüm sınır verileri hazır!")
    else:
        print("⚠ Bazı dosyalar indirilemedi. Bağlantınızı kontrol edin.")
        sys.exit(1)


if __name__ == "__main__":
    main()
