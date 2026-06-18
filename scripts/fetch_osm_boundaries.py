#!/usr/bin/env python3
"""
Türkiye il ve ilçe sınırlarını OpenStreetMap (OSM) verisinden indirir ve
uygulamanın beklediği formata dönüştürür.

Neden GADM yerine OSM?
  - Basemap (CARTO/OSM tile'ları) OSM kaynaklı; GADM sınırları bu tile'larla
    hizalanmıyordu (özellikle kıyılarda belirgin kayma vardı).
  - OSM admin-level-4 (il) / admin-level-6 (ilçe) verisi basemap ile aynı
    kaynaktan geldiği için sınırlar tile'larla örtüşür.

Kaynak: github.com/izzetkalic/geojsons-of-turkey (TKGM + OSM, Git LFS)

Adımlar:
  1. admin-level-4 (il) ve admin-level-6 (ilçe) GeoJSON'larını indirir.
  2. İlleri kanonik alfabetik sıraya (il_kodu 1..81) eşler — demografi ve
     choropleth bu kodlarla çalıştığı için sıralama korunmalıdır.
  3. İlçeleri il poligonlarına NOKTASAL (point-in-polygon) atar, il içinde
     Türkçe alfabetik sıralayıp ilce_kodu = "il_kodu.N" atar.
  4. mapshaper (npx) ile TOPOLOJİ-KORUMALI sadeleştirme yapar (komşu sınırlar
     tutarlı sadeleşir, boşluk oluşmaz).
  5. data/boundaries/ altına yazar.

Gereksinimler:
    pip install requests          (indirme)
    npx mapshaper                 (sadeleştirme; node.js gerekir)

Sadeleştirmeden sonra ilçe demografisini yenilemek için:
    python scripts/seed_district_demographics.py
"""
import os
import sys
import json
import subprocess
import tempfile

try:
    import requests
except ImportError:
    print("requests gerekli: pip install requests")
    sys.exit(1)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "boundaries")
os.makedirs(DATA_DIR, exist_ok=True)

LFS_BASE = "https://media.githubusercontent.com/media/izzetkalic/geojsons-of-turkey/master/geojsons"
PROV_URL = f"{LFS_BASE}/turkey-admin-level-4.geojson"
DIST_URL = f"{LFS_BASE}/turkey-admin-level-6.geojson"

# İl kodu → ad (standart Türkçe alfabetik sıra; demografi bu kodları kullanır)
IL_KODU_AD = {
    1: 'Adana', 2: 'Adıyaman', 3: 'Afyonkarahisar', 4: 'Ağrı', 5: 'Aksaray',
    6: 'Amasya', 7: 'Ankara', 8: 'Antalya', 9: 'Ardahan', 10: 'Artvin',
    11: 'Aydın', 12: 'Balıkesir', 13: 'Bartın', 14: 'Batman', 15: 'Bayburt',
    16: 'Bilecik', 17: 'Bingöl', 18: 'Bitlis', 19: 'Bolu', 20: 'Burdur',
    21: 'Bursa', 22: 'Çanakkale', 23: 'Çankırı', 24: 'Çorum', 25: 'Denizli',
    26: 'Diyarbakır', 27: 'Düzce', 28: 'Edirne', 29: 'Elazığ', 30: 'Erzincan',
    31: 'Erzurum', 32: 'Eskişehir', 33: 'Gaziantep', 34: 'Giresun', 35: 'Gümüşhane',
    36: 'Hakkari', 37: 'Hatay', 38: 'Iğdır', 39: 'Isparta', 40: 'İstanbul',
    41: 'İzmir', 42: 'Kahramanmaraş', 43: 'Karabük', 44: 'Karaman', 45: 'Kars',
    46: 'Kastamonu', 47: 'Kayseri', 48: 'Kilis', 49: 'Kırıkkale', 50: 'Kırklareli',
    51: 'Kırşehir', 52: 'Kocaeli', 53: 'Konya', 54: 'Kütahya', 55: 'Malatya',
    56: 'Manisa', 57: 'Mardin', 58: 'Mersin', 59: 'Muğla', 60: 'Muş',
    61: 'Nevşehir', 62: 'Niğde', 63: 'Ordu', 64: 'Osmaniye', 65: 'Rize',
    66: 'Sakarya', 67: 'Samsun', 68: 'Şanlıurfa', 69: 'Siirt', 70: 'Sinop',
    71: 'Şırnak', 72: 'Sivas', 73: 'Tekirdağ', 74: 'Tokat', 75: 'Trabzon',
    76: 'Tunceli', 77: 'Uşak', 78: 'Van', 79: 'Yalova', 80: 'Yozgat',
    81: 'Zonguldak',
}

_TR = {'ı': 'i', 'İ': 'i', 'ş': 's', 'ğ': 'g', 'ü': 'u', 'ö': 'o', 'ç': 'c', 'â': 'a', 'î': 'i'}
_TR_ORDER = "abcçdefgğhıijklmnoöprsştuüvyz"


def norm(s: str) -> str:
    s = (s or '').strip().lower()
    for suf in (' i̇li', ' ili'):
        if s.endswith(suf):
            s = s[:-len(suf)]
    return ''.join(_TR.get(c, c) for c in s).strip()


def tr_sortkey(s: str):
    s = s.lower()
    return [_TR_ORDER.index(c) if c in _TR_ORDER else 99 for c in s]


NAME_TO_CODE = {norm(v): k for k, v in IL_KODU_AD.items()}


def download(url: str, label: str) -> dict:
    print(f"İndiriliyor: {label} ...")
    r = requests.get(url, timeout=300)
    r.raise_for_status()
    data = r.json()
    print(f"  ✓ {len(data.get('features', []))} ham feature ({len(r.content)//1024} KB)")
    return data


# ── Geometri yardımcıları (saf Python, harici bağımlılık yok) ──────────────
def _bbox(geom):
    xs, ys = [], []
    def walk(c):
        if c and isinstance(c[0], (int, float)):
            xs.append(c[0]); ys.append(c[1])
        elif c:
            for x in c: walk(x)
    walk(geom['coordinates'])
    return (min(xs), min(ys), max(xs), max(ys))


def _point_in_ring(x, y, ring):
    inside = False; n = len(ring); j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def _point_in_geom(x, y, geom):
    polys = geom['coordinates'] if geom['type'] == 'MultiPolygon' else [geom['coordinates']]
    for poly in polys:
        if _point_in_ring(x, y, poly[0]) and not any(_point_in_ring(x, y, h) for h in poly[1:]):
            return True
    return False


def _largest_ring(geom):
    polys = geom['coordinates'] if geom['type'] == 'MultiPolygon' else [geom['coordinates']]
    best, ba = None, -1
    for poly in polys:
        ring = poly[0]
        xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
        a = (max(xs) - min(xs)) * (max(ys) - min(ys))
        if a > ba:
            ba, best = a, ring
    return best


def _centroid(ring):
    A = cx = cy = 0; n = len(ring)
    for i in range(n - 1):
        x0, y0 = ring[i][0], ring[i][1]; x1, y1 = ring[i + 1][0], ring[i + 1][1]
        cr = x0 * y1 - x1 * y0; A += cr; cx += (x0 + x1) * cr; cy += (y0 + y1) * cr
    if abs(A) < 1e-12:
        xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
        return sum(xs) / len(xs), sum(ys) / len(ys)
    A *= 0.5
    return cx / (6 * A), cy / (6 * A)


def mapshaper_simplify(features, out_path, percent):
    """mapshaper (npx) ile topoloji-korumalı sadeleştirme. Yoksa ham yazar."""
    fc = {"type": "FeatureCollection", "features": features}
    with tempfile.NamedTemporaryFile('w', suffix='.geojson', delete=False, encoding='utf-8') as tmp:
        json.dump(fc, tmp, ensure_ascii=False)
        tmp_path = tmp.name
    try:
        subprocess.run(
            ["npx", "-y", "mapshaper", tmp_path,
             "-simplify", f"{percent}%", "keep-shapes", "-clean",
             "-o", out_path, "format=geojson"],
            check=True, capture_output=True, text=True,
        )
        print(f"  ✓ mapshaper ile sadeleştirildi ({percent}%) → {os.path.basename(out_path)}")
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        print(f"  ⚠ mapshaper çalışmadı ({e}); ham (sadeleştirilmemiş) yazılıyor.")
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(fc, f, ensure_ascii=False)
    finally:
        os.unlink(tmp_path)


def build_provinces():
    data = download(PROV_URL, "İl sınırları (OSM admin-level-4)")
    feats = []
    seen = set()
    for f in data['features']:
        p = f['properties']; g = f['geometry']
        if g['type'] not in ('Polygon', 'MultiPolygon'):
            continue
        if p.get('admin_level') != '4':
            continue
        name = p.get('name:tr') or p.get('name')
        iso = p.get('ISO3166-2', '')
        if not name or not iso.startswith('TR-'):
            continue
        key = norm(name)
        if key not in NAME_TO_CODE or key in seen:
            continue
        seen.add(key)
        code = NAME_TO_CODE[key]
        feats.append({
            "type": "Feature",
            "properties": {"il_kodu": str(code), "il_adi": IL_KODU_AD[code]},
            "geometry": g,
        })
    feats.sort(key=lambda f: int(f['properties']['il_kodu']))
    print(f"  Eşlenen il: {len(feats)}/81")
    out = os.path.join(DATA_DIR, "turkey_provinces.geojson")
    mapshaper_simplify(feats, out, percent=18)
    return out


def build_districts(prov_path):
    data = download(DIST_URL, "İlçe sınırları (OSM admin-level-6)")
    # İl poligonlarını (sadeleştirilmiş) point-in-polygon için yükle
    prov = json.load(open(prov_path, encoding='utf-8'))
    provs = [(f['properties']['il_kodu'], f['properties']['il_adi'],
              _bbox(f['geometry']), f['geometry']) for f in prov['features']]

    def find_prov(x, y):
        for il_kodu, il_adi, bb, geom in provs:
            if bb[0] <= x <= bb[2] and bb[1] <= y <= bb[3] and _point_in_geom(x, y, geom):
                return il_kodu, il_adi
        return None

    by_prov = {}
    unassigned = 0
    for f in data['features']:
        g = f['geometry']; p = f['properties']
        if g['type'] not in ('Polygon', 'MultiPolygon') or p.get('admin_level') != '6':
            continue
        name = p.get('name:tr') or p.get('name')
        if not name:
            continue
        ring = _largest_ring(g)
        cx, cy = _centroid(ring)
        res = find_prov(cx, cy)
        if not res:  # konkav ilçe / kıyı: kenar noktalarıyla oyla
            votes = {}
            for i in range(0, len(ring), max(1, len(ring) // 8)):
                r = find_prov(ring[i][0], ring[i][1])
                if r:
                    votes[r] = votes.get(r, 0) + 1
            res = max(votes, key=votes.get) if votes else None
        if not res:
            unassigned += 1
            continue
        by_prov.setdefault(res, []).append((name, g))

    out_feats = []
    for (il_kodu, il_adi), ds in by_prov.items():
        ds.sort(key=lambda t: tr_sortkey(t[0]))
        for i, (name, geom) in enumerate(ds, 1):
            out_feats.append({
                "type": "Feature",
                "properties": {"il_kodu": il_kodu, "il_adi": il_adi,
                               "ilce_kodu": f"{il_kodu}.{i}", "ilce_adi": name},
                "geometry": geom,
            })
    out_feats.sort(key=lambda f: (int(f['properties']['il_kodu']),
                                  int(f['properties']['ilce_kodu'].split('.')[1])))
    print(f"  Atanan ilçe: {len(out_feats)} | atanamayan: {unassigned}")
    out = os.path.join(DATA_DIR, "turkey_districts.geojson")
    mapshaper_simplify(out_feats, out, percent=12)
    return out


def main():
    print("=" * 60)
    print("Türkiye Sınır Verisi (OSM) İndirici")
    print("=" * 60)
    prov_path = build_provinces()
    build_districts(prov_path)
    print()
    print("✓ Sınır verileri hazır.")
    print("  Not: İlçe demografisini yenilemek için:")
    print("       python scripts/seed_district_demographics.py")


if __name__ == "__main__":
    main()
