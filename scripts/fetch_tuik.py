#!/usr/bin/env python3
"""
TÜİK 2025 demografik verisini OTORİTER + OTOMATİK kaynaklardan çeker ve
uygulamanın şemasına normalize ederek CSV üretir (hardcoded DEĞİL).

Kaynaklar:
  1. TÜİK Nüfus İstatistikleri Portalı statik JSON'ları (il düzeyi, otoriter):
       nip.tuik.gov.tr/maps/assets/veri/D3-<gosterge>.json
       → Ortanca (medyan) yaş, nüfus yoğunluğu, yıllık nüfus artış hızı
       Bölge eşlemesi: .../geometri/d3.json (duzeyKodu → il adı → il_kodu)
  2. nufusu.com (TÜİK kaynaklı, sunucu-render): il ve ilçe bazında
       toplam / erkek / kadın nüfus (81 il sayfası → 81 il + 973 ilçe).

Çıktı:
  data/demographics/tuik_2025_il.csv
  data/demographics/tuik_2025_ilce.csv

İl ve ilçe kodları sınır verisiyle (turkey_*.geojson) aynı olacak şekilde
İSİM eşlemesiyle atanır; eşleşmeyenler raporlanır.

Not: İlçe bazında medyan yaş / yoğunluk / yaş grupları TÜİK'in açık harita
servisinde YOK; uydurulmaz, boş bırakılır. İl yaş grupları da bu serviste
çoklu-değer (grafik) olduğundan dahil edilmez — istenirse resmi TÜİK Excel'i
Excel-import ile sonradan eklenebilir.
"""
import os
import re
import csv
import sys
import json
import time

try:
    import requests
except ImportError:
    print("requests gerekli: pip install requests"); sys.exit(1)

sys.path.insert(0, os.path.dirname(__file__))
from tr_util import IL_KODU_AD, norm, tr_sortkey, il_slug, NAME_TO_CODE

ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT_DIR = os.path.join(ROOT, "data", "demographics")
DIST_GEOJSON = os.path.join(ROOT, "data", "boundaries", "turkey_districts.geojson")
os.makedirs(OUT_DIR, exist_ok=True)

NIP = "https://nip.tuik.gov.tr/maps/assets"
UA = {"User-Agent": "Mozilla/5.0 (TurkiyeGIS-GraduationProject; educational)"}
YEAR = 2025

# nufusu ilçe adı ↔ OSM ilçe adı farkları (gerektikçe doldurulur)
ILCE_ALIAS = {
    # (il_kodu, norm(nufusu_adi)): norm(osm_adi)
}


def get_json(url):
    r = requests.get(url, headers=UA, timeout=60)
    r.raise_for_status()
    return r.json()


def get_html(url, tries=3):
    for i in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=45)
            if r.status_code == 200:
                return r.text
        except requests.RequestException:
            pass
        time.sleep(1.5)
    return None


# ── 1) TÜİK nip: il düzeyi tek-değerli göstergeler ─────────────────────────
def fetch_nip_indicator(gosterge, duzey2code):
    """D3-<gosterge>.json → {il_kodu: 2025 değeri}."""
    try:
        d = get_json(f"{NIP}/veri/D3-{gosterge}.json")
    except Exception as e:
        print(f"  [UYARI] nip {gosterge} alınamadı: {e}")
        return {}
    sureler = d.get("sureler", [])
    idx = sureler.index(YEAR) if YEAR in sureler else -1
    out = {}
    for row in d.get("veriler", []):
        dk = int(row["duzeyKodu"])
        code = duzey2code.get(dk)
        if code and row["veri"] and idx < len(row["veri"]):
            out[code] = row["veri"][idx]
    return out


def build_duzey2code():
    geo = get_json(f"{NIP}/geometri/d3.json")
    d2c = {}
    for f in geo["features"]:
        code = NAME_TO_CODE.get(norm(f["properties"]["AD"]))
        if code:
            d2c[int(f["properties"]["duzeyKodu"])] = code
    if len(d2c) != 81:
        print(f"  [UYARI] duzeyKodu→il_kodu eşleşmesi {len(d2c)}/81")
    return d2c


# ── 2) nufusu.com: il + ilçe toplam/cinsiyet ───────────────────────────────
def _num(s):
    s = re.sub(r"[^\d]", "", s or "")
    return int(s) if s else 0


def _tables(html):
    out = []
    for t in re.findall(r"<table.*?</table>", html, re.S):
        ths = [re.sub("<[^>]+>", "", x).strip()
               for x in re.findall(r"<th[^>]*>(.*?)</th>", t, re.S)]
        rows = []
        for tr in re.findall(r"<tr>(.*?)</tr>", t, re.S):
            tds = [re.sub("<[^>]+>", "", x).strip()
                   for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
            if tds:
                rows.append(tds)
        out.append((ths, rows))
    return out


def parse_province_page(html):
    """(il_total, il_erkek, il_kadin, [(ilce_adi, total, erkek, kadin), ...])"""
    il_tot = il_e = il_k = 0
    districts = []
    for ths, rows in _tables(html):
        head = " | ".join(ths)
        if "İlçe" in head and "Erkek" in head:
            # ilçe tablosu: [Yıl, İlçe, Nüfus, Erkek, Kadın, %]
            for r in rows:
                if len(r) >= 5 and r[0] == str(YEAR):
                    districts.append((r[1], _num(r[2]), _num(r[3]), _num(r[4])))
        elif "Erkek" in head and "Kadın" in head and "İlçe" not in head:
            # il toplam tablosu: [Yıl, Nüfus, Erkek, Kadın]
            for r in rows:
                if len(r) >= 4 and r[0] == str(YEAR):
                    il_tot, il_e, il_k = _num(r[1]), _num(r[2]), _num(r[3])
                    break
    return il_tot, il_e, il_k, districts


# ── İlçe adı → ilce_kodu eşleme (sınır verisinden) ─────────────────────────
_MERKEZ_TOK = {"merkez", "merkezi"}

# nufusu ↔ OSM ad farkları (norm edilmiş): (il_kodu, nufusu_norm) → osm_stripped_norm
ILCE_ALIAS = {
    (67, "19 mayis"): "ondokuzmayis",   # Samsun: 19 Mayıs = Ondokuzmayıs
}


def _strip_merkez(nm):
    """normalize edilmiş adı 'merkez/merkezi' işaretinden arındır:
    'antakya (merkez)'→'antakya', 'rize merkezi'→'rize',
    'merkezefendi'→'merkezefendi' (tek token, korunur)."""
    nm = nm.replace("(", " ").replace(")", " ")
    toks = [t for t in nm.split() if t and t not in _MERKEZ_TOK]
    return " ".join(toks)


def _ed_le1(a, b):
    """edit distance <= 1 (yazım hatası toleransı)."""
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la == lb:  # tek harf değişimi
        return sum(c1 != c2 for c1, c2 in zip(a, b)) == 1
    # tek harf ekleme/silme
    if la > lb:
        a, b = b, a
    i = j = 0
    skipped = False
    while i < len(a) and j < len(b):
        if a[i] != b[j]:
            if skipped:
                return False
            skipped = True
            j += 1
        else:
            i += 1
            j += 1
    return True


def build_district_index():
    geo = json.load(open(DIST_GEOJSON, encoding="utf-8"))
    idx = {}        # (il_kodu, stripped_norm) → (ilce_kodu, ilce_adi)
    central = {}    # il_kodu → (ilce_kodu, ilce_adi)  (merkez ilçe)
    for f in geo["features"]:
        p = f["properties"]
        il = p["il_kodu"]
        base = _strip_merkez(norm(p["ilce_adi"]))
        idx[(il, base)] = (p["ilce_kodu"], p["ilce_adi"])
        toks = norm(p["ilce_adi"]).replace("(", " ").replace(")", " ").split()
        if _MERKEZ_TOK & set(toks):
            central[il] = (p["ilce_kodu"], p["ilce_adi"])
    return idx, central


def match_district(il_kodu, adi, idx, central):
    il = str(il_kodu)
    alias = ILCE_ALIAS.get((il_kodu, norm(adi)))
    base = alias if alias is not None else _strip_merkez(norm(adi))
    if base == "":                       # nufusu 'Merkez' → ilin merkez ilçesi
        return central.get(il)
    hit = idx.get((il, base))
    if hit:
        return hit
    # yazım hatası toleransı (ekleme/silme/değişim VE transpozisyon)
    for (i, b), v in idx.items():
        if i == il and (_ed_le1(base, b) or sorted(base) == sorted(b) and _transpose1(base, b)):
            return v
    return None


def _transpose1(a, b):
    """bitişik iki harfin yer değiştirmesi (Baklan↔Balkan)."""
    if len(a) != len(b):
        return False
    diff = [k for k in range(len(a)) if a[k] != b[k]]
    return len(diff) == 2 and diff[1] == diff[0] + 1 and \
        a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]]


def main():
    print("=" * 60)
    print(f"TÜİK {YEAR} Demografik Veri Çekici (otomatik)")
    print("=" * 60)

    print("\n[1/3] TÜİK nip il göstergeleri...")
    d2c = build_duzey2code()
    medyan = fetch_nip_indicator("OrtancaYas", d2c)
    yogunluk = fetch_nip_indicator("NufusYogunlugu", d2c)
    artis = fetch_nip_indicator("NufusArtisHizi", d2c)
    print(f"  medyan yaş: {len(medyan)} il | yoğunluk: {len(yogunluk)} | artış: {len(artis)}")

    print("\n[2/3] nufusu.com il/ilçe nüfusları...")
    dist_idx, dist_central = build_district_index()
    il_rows, ilce_rows, unmatched = [], [], []
    for code in range(1, 82):
        slug = il_slug(IL_KODU_AD[code])
        html = get_html(f"https://www.nufusu.com/il/{slug}-nufusu")
        if not html:
            print(f"  [HATA] {IL_KODU_AD[code]} ({slug}) alınamadı")
            continue
        tot, erk, kad, dists = parse_province_page(html)
        il_rows.append({
            "il_kodu": code, "il_adi": IL_KODU_AD[code],
            "toplam_nufus": tot, "erkek_nufus": erk, "kadin_nufus": kad,
            "medyan_yas": medyan.get(code, ""), "nufus_yogunluk": yogunluk.get(code, ""),
            "nufus_artis_hizi": artis.get(code, ""), "veri_yili": YEAR,
        })
        for adi, dt, de, dk in dists:
            hit = match_district(code, adi, dist_idx, dist_central)
            if not hit:
                unmatched.append((IL_KODU_AD[code], adi))
                continue
            ilce_kodu, ilce_adi = hit
            ilce_rows.append({
                "il_kodu": code, "il_adi": IL_KODU_AD[code],
                "ilce_kodu": ilce_kodu, "ilce_adi": ilce_adi,
                "toplam_nufus": dt, "erkek_nufus": de, "kadin_nufus": dk,
                "veri_yili": YEAR,
            })
        time.sleep(0.3)
        if code % 20 == 0:
            print(f"  ...{code}/81 il işlendi")

    print(f"  il: {len(il_rows)} | ilçe: {len(ilce_rows)} | eşleşmeyen ilçe: {len(unmatched)}")
    if unmatched:
        print("  Eşleşmeyen ilçeler (alias gerekebilir):")
        for il, adi in unmatched[:40]:
            print(f"    {il} / {adi}")

    print("\n[3/3] CSV yazılıyor + bütünlük kontrolü...")
    _write_csv(os.path.join(OUT_DIR, f"tuik_{YEAR}_il.csv"), il_rows,
               ["il_kodu", "il_adi", "toplam_nufus", "erkek_nufus", "kadin_nufus",
                "medyan_yas", "nufus_yogunluk", "nufus_artis_hizi", "veri_yili"])
    _write_csv(os.path.join(OUT_DIR, f"tuik_{YEAR}_ilce.csv"), ilce_rows,
               ["il_kodu", "il_adi", "ilce_kodu", "ilce_adi",
                "toplam_nufus", "erkek_nufus", "kadin_nufus", "veri_yili"])

    # Bütünlük: il toplamı ~ ilçeleri toplamı
    by_il = {}
    for r in ilce_rows:
        by_il[r["il_kodu"]] = by_il.get(r["il_kodu"], 0) + r["toplam_nufus"]
    diffs = []
    for r in il_rows:
        d = r["toplam_nufus"] - by_il.get(r["il_kodu"], 0)
        if r["toplam_nufus"] and abs(d) / r["toplam_nufus"] > 0.02:
            diffs.append((r["il_adi"], r["toplam_nufus"], by_il.get(r["il_kodu"], 0)))
    print(f"  il=ilçe toplam tutarsızlığı (>%2): {len(diffs)} il")
    for ad, t, s in diffs[:10]:
        print(f"    {ad}: il={t:,} ilçe_top={s:,}")

    tr_total = sum(r["toplam_nufus"] for r in il_rows)
    print(f"\n✓ Türkiye toplam: {tr_total:,} (beklenen ~86.092.168)")
    print("  Yenilemek için: python scripts/load_demographics.py")


def _write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"  ✓ {len(rows)} satır → {os.path.basename(path)}")


if __name__ == "__main__":
    main()
