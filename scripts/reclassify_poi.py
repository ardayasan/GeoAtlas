#!/usr/bin/env python3
"""
POI verilerini yeniden sınıflandır:
  1. Üniversiteler — fakülte/bölüm alt birimlerini, ilk/ortaokul/lise/dershane
                     olarak işaret edilen girişleri kaldır
  2. Okullar      — içinde "Anaokulu/Kreş" geçenleri kindergartens'a taşı,
                    üniversite birimlerini kaldır
  3. Anaokulları  — schools'dan taşınanlarla zenginleştir
"""
import json, os, re

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'poi')

def load(name):
    path = os.path.join(DATA_DIR, name)
    with open(path, encoding='utf-8') as f:
        return json.load(f)

def save(name, gj):
    path = os.path.join(DATA_DIR, name)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(gj, f, ensure_ascii=False, separators=(',', ':'))
    print(f"  Saved {len(gj['features'])} → {name}")

# ── Üniversiteler ─────────────────────────────────────────────────────────────
# Kaldırılacak örüntüler (alt birimler, yanlış etiketlenenler)
REMOVE_FROM_UNIV = re.compile(
    r'Fakülte|Bölüm[üuü]?|Rektörlük|Ek Bina|Girişi|Araştırma|Uygulama '
    r'Merkezi|Hastane|Kütüphane|Laboratuvar|Kafeterya|Kantin|ABD\.'
    r'|Bürosu|Yurt|Çay Bahçesi|Sosyal Tesis|Hizmet Binası|Kariyer|'
    r'İdari|Dekanlık|Müdürlük|Ofis|Otopark|Spor |Yemekhane|İletişim Merkezi|'
    r'Gençlik Merkezi|Üretim Merkezi|'
    # Yanlış etiketlenmiş okullar
    r'İlkokul|Ortaokul|İlk[- ]Orta|(?<!\w)Lise(?!\w)|Lisesi|'
    # Dershaneler / kurslar
    r'Öğretim Kursu|Dershane|Etüt|Kurs |'
    # Spesifik kuruluşlar
    r'Gündüz Bakım|Anaokul|Kreş',
    re.IGNORECASE
)

# Özel lise olarak bilinen "Kolej" girişlerini tespit et
PRIVATE_HIGHSCHOOL = re.compile(
    r'(?:Özel|Koleji|Anadolu Lisesi|Fen Lisesi|Imam Hatip|İmam Hatip)',
    re.IGNORECASE
)
LISE_KW = re.compile(r'Lise|lisesi', re.IGNORECASE)

def keep_university(feat):
    name = feat['properties'].get('name') or ''
    amenity = feat['properties'].get('amenity', '')

    # Boş isim — sadece amenity=university ise tut, college ise at
    if not name.strip():
        return amenity == 'university'

    # Açıkça kaldırılacaklar
    if REMOVE_FROM_UNIV.search(name):
        return False

    # "Kolej" ama gerçekte lise/özel okul olan girişler:
    # Türkiye'de "Kolej" genellikle özel lise anlamına gelir.
    # Gerçek kolejler (üniversite düzeyi) nadirdir ve OSM'de university olarak işaretlenir.
    if amenity == 'college' and LISE_KW.search(name):
        return False

    return True

# Orijinal (ham) dosyaları yükle — baştan yükle
# (Bir önceki çalıştırma değiştirmiş olabilir, ama burada tekrar çalıştırma güvenli)
univs = load('universities_turkey.geojson')
before = len(univs['features'])
univs['features'] = [f for f in univs['features'] if keep_university(f)]
print(f"Universities: {before} → {len(univs['features'])} (removed {before - len(univs['features'])})")
save('universities_turkey.geojson', univs)

# ── Okullar ───────────────────────────────────────────────────────────────────
KINDER_KW = re.compile(
    r'Anaokul|Ana[- ]Okul|Kreş|Anasınıf|Gündüz Bakım|Bebek Yuvası|'
    r'Çocuk Yuvası|Kids Club|Mini Kids|Little|Toddler|Nursery',
    re.IGNORECASE
)

UNIV_CONTAM = re.compile(
    r'Üniversite|Fakülte|Enstitü|Yüksekokul|MYO|Meslek Yüksek',
    re.IGNORECASE
)

# Açıkça okul olan kelimeleri içerirse üniversite olarak gitmesin
SCHOOL_SAFE = re.compile(r'İlkokul|Ortaokul|Lise|Okul', re.IGNORECASE)

schools  = load('schools_turkey.geojson')
kinders  = load('kindergartens_turkey.geojson')

before_s = len(schools['features'])
before_k = len(kinders['features'])

moved, removed, kept = [], [], []

for f in schools['features']:
    name = f['properties'].get('name') or ''
    edu  = f['properties'].get('education') or ''
    if KINDER_KW.search(name) or edu == 'kindergarten':
        moved.append(f)
    elif UNIV_CONTAM.search(name) and not SCHOOL_SAFE.search(name):
        removed.append(f)
    else:
        kept.append(f)

print(f"\nSchools: {before_s} → {len(kept)}")
print(f"  Moved to kindergartens: {len(moved)}")
print(f"  Removed (univ entries): {len(removed)}")

existing_ids = {f['properties'].get('osm_id') for f in kinders['features']}
new_k = [f for f in moved if f['properties'].get('osm_id') not in existing_ids]
kinders['features'].extend(new_k)
print(f"\nKindergartens: {before_k} → {len(kinders['features'])} (+{len(new_k)})")

schools['features'] = kept
save('schools_turkey.geojson', schools)
save('kindergartens_turkey.geojson', kinders)

# ── Özet ──────────────────────────────────────────────────────────────────────
print("\n=== Final POI counts ===")
for fname in [
    'universities_turkey.geojson', 'schools_turkey.geojson',
    'kindergartens_turkey.geojson', 'mosques_turkey.geojson',
    'churches_turkey.geojson', 'worship_other_turkey.geojson',
]:
    path = os.path.join(DATA_DIR, fname)
    if os.path.exists(path):
        with open(path) as ff:
            d = json.load(ff)
        print(f"  {fname.replace('_turkey.geojson',''):22s}: {len(d['features']):6,}")
