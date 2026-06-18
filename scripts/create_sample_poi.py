#!/usr/bin/env python3
"""
Test/demo için Türkiye'nin gerçek koordinatlarıyla örnek POI verisi oluşturur.
Overpass API'ye gerek kalmadan hızlı test yapılabilir.

Kullanım:
    python scripts/create_sample_poi.py
"""

import json, os

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "poi")
os.makedirs(OUT, exist_ok=True)


def geojson(features):
    return {"type": "FeatureCollection", "features": features}


def point(lon, lat, props):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": props,
    }


# ── CAMİLER ─────────────────────────────────────────────────────────
mosques = [
    point(28.9740, 41.0058, {"name": "Sultanahmet Camii", "amenity": "place_of_worship", "religion": "muslim", "addr:city": "İstanbul"}),
    point(28.9640, 41.0162, {"name": "Süleymaniye Camii", "amenity": "place_of_worship", "religion": "muslim", "addr:city": "İstanbul"}),
    point(28.9340, 41.0523, {"name": "Eyüp Sultan Camii", "amenity": "place_of_worship", "religion": "muslim", "addr:city": "İstanbul"}),
    point(28.9779, 41.0136, {"name": "Ayasofya Camii", "amenity": "place_of_worship", "religion": "muslim", "addr:city": "İstanbul"}),
    point(28.9501, 41.0381, {"name": "Fatih Camii", "amenity": "place_of_worship", "religion": "muslim", "addr:city": "İstanbul"}),
    point(32.8597, 39.9208, {"name": "Kocatepe Camii", "amenity": "place_of_worship", "religion": "muslim", "addr:city": "Ankara"}),
    point(32.8640, 39.9121, {"name": "Hacıbayram Camii", "amenity": "place_of_worship", "religion": "muslim", "addr:city": "Ankara"}),
    point(27.1428, 38.4237, {"name": "Hisar Camii", "amenity": "place_of_worship", "religion": "muslim", "addr:city": "İzmir"}),
    point(35.3308, 37.0017, {"name": "Lala Mustafa Paşa Camii", "amenity": "place_of_worship", "religion": "muslim", "addr:city": "Adana"}),
    point(36.1614, 36.2028, {"name": "Habib-i Neccar Camii", "amenity": "place_of_worship", "religion": "muslim", "addr:city": "Hatay"}),
    point(29.0601, 40.1825, {"name": "Ulu Cami", "amenity": "place_of_worship", "religion": "muslim", "addr:city": "Bursa"}),
    point(30.5566, 37.7662, {"name": "Ulu Cami", "amenity": "place_of_worship", "religion": "muslim", "addr:city": "Isparta"}),
    point(33.6170, 39.7670, {"name": "Ulu Cami", "amenity": "place_of_worship", "religion": "muslim", "addr:city": "Kırşehir"}),
    point(35.4667, 38.7333, {"name": "Ulu Camii", "amenity": "place_of_worship", "religion": "muslim", "addr:city": "Kayseri"}),
    point(37.3667, 37.0667, {"name": "Ulu Camii", "amenity": "place_of_worship", "religion": "muslim", "addr:city": "Kahramanmaraş"}),
    point(39.7167, 37.5667, {"name": "Ulu Camii", "amenity": "place_of_worship", "religion": "muslim", "addr:city": "Sivas"}),
    point(40.5500, 41.0167, {"name": "Rize Orta Camii", "amenity": "place_of_worship", "religion": "muslim", "addr:city": "Rize"}),
    point(43.3833, 38.5000, {"name": "Van Ulu Camii", "amenity": "place_of_worship", "religion": "muslim", "addr:city": "Van"}),
    point(38.6917, 39.1667, {"name": "Kurşunlu Camii", "amenity": "place_of_worship", "religion": "muslim", "addr:city": "Elazığ"}),
    point(41.1667, 40.5500, {"name": "Atatürk Camii", "amenity": "place_of_worship", "religion": "muslim", "addr:city": "Artvin"}),
]

# ── KİLİSELER ────────────────────────────────────────────────────────
churches = [
    point(28.9749, 41.0046, {"name": "Küçük Ayasofya (Eski)", "amenity": "place_of_worship", "religion": "christian", "addr:city": "İstanbul"}),
    point(28.9410, 41.0328, {"name": "Ekümenik Patrikane - Aya Yorgi Katedrali", "amenity": "place_of_worship", "religion": "christian", "denomination": "orthodox", "addr:city": "İstanbul"}),
    point(28.9741, 41.0286, {"name": "Saint Antoine Kilisesi", "amenity": "place_of_worship", "religion": "christian", "denomination": "roman_catholic", "addr:city": "İstanbul"}),
    point(28.9809, 41.0413, {"name": "Surp Kevork Ermeni Kilisesi", "amenity": "place_of_worship", "religion": "christian", "addr:city": "İstanbul"}),
    point(36.1614, 36.2028, {"name": "Saint Pierre Kilisesi", "amenity": "place_of_worship", "religion": "christian", "denomination": "roman_catholic", "addr:city": "Hatay (Antakya)"}),
    point(34.6100, 36.8667, {"name": "Tarsus Kilisesi (Aziz Pavlus)", "amenity": "place_of_worship", "religion": "christian", "addr:city": "Mersin (Tarsus)"}),
    point(28.0833, 37.8500, {"name": "Aya Yorgi Kilisesi", "amenity": "place_of_worship", "religion": "christian", "addr:city": "Aydın (Selçuk)"}),
    point(27.3667, 37.0333, {"name": "Aziz Yuhanna Kilisesi", "amenity": "place_of_worship", "religion": "christian", "addr:city": "Muğla (Bodrum)"}),
    point(32.8667, 39.9167, {"name": "Ankara Katolik Kilisesi", "amenity": "place_of_worship", "religion": "christian", "denomination": "roman_catholic", "addr:city": "Ankara"}),
    point(27.1500, 38.4167, {"name": "İzmir Fransız Konsolosluk Şapeli", "amenity": "place_of_worship", "religion": "christian", "addr:city": "İzmir"}),
]

# ── DİĞER İBADETHANELER ──────────────────────────────────────────────
worship_other = [
    point(28.9667, 41.0333, {"name": "Neve Şalom Sinagogu", "amenity": "place_of_worship", "religion": "jewish", "addr:city": "İstanbul"}),
    point(28.9741, 41.0131, {"name": "Aşkenaz Sinagogu", "amenity": "place_of_worship", "religion": "jewish", "addr:city": "İstanbul"}),
    point(32.8500, 39.9333, {"name": "Ankara Sinagogu", "amenity": "place_of_worship", "religion": "jewish", "addr:city": "Ankara"}),
    point(28.9370, 41.0190, {"name": "Alevi Cemevi Balıklı", "amenity": "place_of_worship", "religion": "alevi", "addr:city": "İstanbul"}),
    point(32.8611, 39.9100, {"name": "Ankara Cemevi", "amenity": "place_of_worship", "religion": "alevi", "addr:city": "Ankara"}),
]

# ── OKULLAR ──────────────────────────────────────────────────────────
schools = [
    # İstanbul
    point(28.9784, 41.0082, {"name": "Galatasaray Lisesi", "amenity": "school", "school:level": "secondary", "addr:city": "İstanbul"}),
    point(29.0333, 41.0167, {"name": "Robert Kolej", "amenity": "school", "addr:city": "İstanbul"}),
    point(28.9950, 41.0220, {"name": "İstanbul Erkek Lisesi", "amenity": "school", "addr:city": "İstanbul"}),
    point(28.9500, 41.0280, {"name": "Kabataş Erkek Lisesi", "amenity": "school", "addr:city": "İstanbul"}),
    point(29.0200, 40.9800, {"name": "Kadıköy Anadolu Lisesi", "amenity": "school", "addr:city": "İstanbul"}),
    point(29.0400, 41.0600, {"name": "Sarıyer Anadolu Lisesi", "amenity": "school", "addr:city": "İstanbul"}),
    point(28.8700, 41.0100, {"name": "Bakırköy İlköğretim Okulu", "amenity": "school", "addr:city": "İstanbul"}),
    # Ankara
    point(32.8400, 39.9500, {"name": "TED Ankara Koleji", "amenity": "school", "addr:city": "Ankara"}),
    point(32.8600, 39.9600, {"name": "Ankara Atatürk Lisesi", "amenity": "school", "addr:city": "Ankara"}),
    point(32.8700, 39.9200, {"name": "Gazi Anadolu Lisesi", "amenity": "school", "addr:city": "Ankara"}),
    # İzmir
    point(27.1500, 38.4300, {"name": "İzmir Atatürk Lisesi", "amenity": "school", "addr:city": "İzmir"}),
    point(27.1600, 38.4100, {"name": "Bornova Anadolu Lisesi", "amenity": "school", "addr:city": "İzmir"}),
    # Diğer
    point(29.0600, 40.1800, {"name": "Bursa Anadolu Lisesi", "amenity": "school", "addr:city": "Bursa"}),
    point(35.4700, 38.7400, {"name": "Kayseri Anadolu Lisesi", "amenity": "school", "addr:city": "Kayseri"}),
    point(37.3700, 37.0600, {"name": "Kahramanmaraş Lisesi", "amenity": "school", "addr:city": "Kahramanmaraş"}),
]

# ── ÜNİVERSİTELER ───────────────────────────────────────────────────
universities = [
    point(29.0420, 41.0841, {"name": "Boğaziçi Üniversitesi", "amenity": "university", "addr:city": "İstanbul"}),
    point(29.0233, 41.1058, {"name": "İstanbul Teknik Üniversitesi (İTÜ)", "amenity": "university", "addr:city": "İstanbul"}),
    point(29.1333, 41.0000, {"name": "Marmara Üniversitesi", "amenity": "university", "addr:city": "İstanbul"}),
    point(28.7333, 41.0667, {"name": "İstanbul Üniversitesi", "amenity": "university", "addr:city": "İstanbul"}),
    point(28.9833, 41.0583, {"name": "Yıldız Teknik Üniversitesi", "amenity": "university", "addr:city": "İstanbul"}),
    point(32.7772, 39.8910, {"name": "Orta Doğu Teknik Üniversitesi (ODTÜ)", "amenity": "university", "addr:city": "Ankara"}),
    point(32.8028, 39.9390, {"name": "Gazi Üniversitesi", "amenity": "university", "addr:city": "Ankara"}),
    point(32.8500, 39.9500, {"name": "Hacettepe Üniversitesi", "amenity": "university", "addr:city": "Ankara"}),
    point(32.8900, 39.9700, {"name": "Ankara Üniversitesi", "amenity": "university", "addr:city": "Ankara"}),
    point(27.2167, 38.4667, {"name": "Ege Üniversitesi", "amenity": "university", "addr:city": "İzmir"}),
    point(27.1500, 38.4600, {"name": "Dokuz Eylül Üniversitesi", "amenity": "university", "addr:city": "İzmir"}),
    point(29.0667, 40.2167, {"name": "Uludağ Üniversitesi", "amenity": "university", "addr:city": "Bursa"}),
    point(35.5167, 38.7333, {"name": "Erciyes Üniversitesi", "amenity": "university", "addr:city": "Kayseri"}),
    point(40.5500, 39.9167, {"name": "Karadeniz Teknik Üniversitesi (KTÜ)", "amenity": "university", "addr:city": "Trabzon"}),
    point(41.2667, 41.0167, {"name": "Recep Tayyip Erdoğan Üniversitesi", "amenity": "university", "addr:city": "Rize"}),
    point(36.1667, 36.2000, {"name": "Mustafa Kemal Üniversitesi", "amenity": "university", "addr:city": "Hatay"}),
]

# ── ANAOKULLAR ────────────────────────────────────────────────────────
kindergartens = [
    point(28.9900, 41.0150, {"name": "Kadıköy Anaokulu", "amenity": "kindergarten", "addr:city": "İstanbul"}),
    point(29.0100, 41.0250, {"name": "Üsküdar Kreş", "amenity": "kindergarten", "addr:city": "İstanbul"}),
    point(28.9300, 41.0400, {"name": "Beşiktaş Anaokulu", "amenity": "kindergarten", "addr:city": "İstanbul"}),
    point(32.8700, 39.9300, {"name": "Çankaya Anaokulu", "amenity": "kindergarten", "addr:city": "Ankara"}),
    point(32.8500, 39.9100, {"name": "Keçiören Kreş", "amenity": "kindergarten", "addr:city": "Ankara"}),
    point(27.1400, 38.4200, {"name": "Konak Anaokulu", "amenity": "kindergarten", "addr:city": "İzmir"}),
    point(29.0500, 40.1900, {"name": "Nilüfer Anaokulu", "amenity": "kindergarten", "addr:city": "Bursa"}),
    point(35.4800, 38.7200, {"name": "Kocasinan Anaokulu", "amenity": "kindergarten", "addr:city": "Kayseri"}),
]

# ── KAYDET ───────────────────────────────────────────────────────────
files = {
    "mosques_turkey.geojson":      geojson(mosques),
    "churches_turkey.geojson":     geojson(churches),
    "worship_other_turkey.geojson":geojson(worship_other),
    "schools_turkey.geojson":      geojson(schools),
    "universities_turkey.geojson": geojson(universities),
    "kindergartens_turkey.geojson":geojson(kindergartens),
}

for fname, data in files.items():
    path = os.path.join(OUT, fname)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ {fname}: {len(data['features'])} kayıt")

print("\nÖrnek POI verisi hazır! Gerçek veri için 'fetch_overpass.py' çalıştırın.")
