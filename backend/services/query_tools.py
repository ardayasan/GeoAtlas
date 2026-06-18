"""
Yerel LLM asistanı için KISITLI sorgu araçları.

Model serbest SQL yazmaz; yalnızca buradaki önceden tanımlı, doğrulanan
fonksiyonları çağırır. Her araç:
  - il/ilçe adlarını tr_util ile koda çözer,
  - SALT-OKUNUR SQLite sorgusu yapar (demographics_province/district),
  - kompakt sonuç + dokunulan bölge kodlarını ("_codes") döner
    (harita aksiyonu backend'de bu kodlardan üretilir).

Sonuçtaki sayılar gerçektir; model yalnızca bunları kullanır (uydurma yok).
"""
import os
import sys
import json
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
from tr_util import NAME_TO_CODE, IL_KODU_AD, norm  # noqa: E402
from services.db_service import get_db  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
POI_DIR = os.path.join(ROOT, "data", "poi")
PROV_GEOJSON = os.path.join(ROOT, "data", "boundaries", "turkey_provinces.geojson")

# Metrik adı → (DB kolonu, görünen ad, birim)
METRIC_INFO = {
    "toplam_nufus":     ("toplam_nufus",     "Toplam nüfus",            "kişi"),
    "erkek_nufus":      ("erkek_nufus",      "Erkek nüfus",             "kişi"),
    "kadin_nufus":      ("kadin_nufus",      "Kadın nüfus",             "kişi"),
    "medyan_yas":       ("medyan_yas",       "Medyan yaş",              "yaş"),
    "nufus_yogunluk":   ("nufus_yogunluk",   "Nüfus yoğunluğu",         "kişi/km²"),
    "nufus_artis_hizi": ("nufus_artis_hizi", "Yıllık nüfus artış hızı", "‰"),
}
# Choropleth chip'leriyle birebir eşleşen metrikler (harita aksiyonu için)
CHIP_METRICS = {"toplam_nufus", "medyan_yas", "nufus_yogunluk", "nufus_artis_hizi"}

POI_FILES = {
    "mosques": "mosques_turkey.geojson",
    "churches": "churches_turkey.geojson",
    "worship_other": "worship_other_turkey.geojson",
    "schools": "schools_turkey.geojson",
    "universities": "universities_turkey.geojson",
    "kindergartens": "kindergartens_turkey.geojson",
}
POI_LABEL = {
    "mosques": "cami/mescid", "churches": "kilise", "worship_other": "diğer ibadethane",
    "schools": "okul", "universities": "üniversite", "kindergartens": "anaokulu/kreş",
}


def _poi_path(kategori, ulke="TR"):
    ulke = (ulke or "TR").strip().upper()
    if kategori not in POI_FILES:
        return None
    candidates = [
        os.path.join(POI_DIR, "europe", ulke, f"{kategori}.geojson"),
        os.path.join(POI_DIR, f"{kategori}_{ulke.lower()}.geojson"),
    ]
    if ulke == "TR":
        candidates.append(os.path.join(POI_DIR, POI_FILES[kategori]))
    return next((path for path in candidates if os.path.exists(path)), None)


def _ro_conn():
    return sqlite3.connect(f"file:{get_db()}?mode=ro", uri=True)


def _col(metrik):
    if metrik not in METRIC_INFO:
        raise ValueError(
            f"Geçersiz metrik '{metrik}'. Geçerli: {', '.join(METRIC_INFO)}")
    return METRIC_INFO[metrik]


def _il_kodu(il_adi):
    code = NAME_TO_CODE.get(norm(il_adi))
    if code is None:
        raise ValueError(f"İl bulunamadı: '{il_adi}'")
    return str(code)


def _fmt(v):
    if v is None:
        return None
    return round(v, 1) if isinstance(v, float) else v


# ── Araçlar ────────────────────────────────────────────────────────────────
def il_istatistik(il_adi, metrik):
    col, label, birim = _col(metrik)
    code = _il_kodu(il_adi)
    with _ro_conn() as db:
        db.row_factory = sqlite3.Row
        row = db.execute(
            f"SELECT il_adi, {col} AS v, veri_yili FROM demographics_province WHERE il_kodu=?",
            (code,)).fetchone()
    if not row or row["v"] is None:
        return {"hata": f"{il_adi} için '{metrik}' verisi yok."}
    return {"il": row["il_adi"], "metrik": label, "deger": _fmt(row["v"]),
            "birim": birim, "yil": row["veri_yili"], "kaynak": "TÜİK", "_codes": [code]}


def il_karsilastir(iller, metrik):
    col, label, birim = _col(metrik)
    sonuc, codes = [], []
    with _ro_conn() as db:
        db.row_factory = sqlite3.Row
        for il in iller:
            code = _il_kodu(il)
            row = db.execute(
                f"SELECT il_adi, {col} AS v FROM demographics_province WHERE il_kodu=?",
                (code,)).fetchone()
            if row and row["v"] is not None:
                sonuc.append({"il": row["il_adi"], "deger": _fmt(row["v"])})
                codes.append(code)
    return {"metrik": label, "birim": birim, "yil": 2025, "kaynak": "TÜİK",
            "karsilastirma": sonuc, "_codes": codes}


def siralama(metrik, yon="desc", n=10, seviye="il"):
    col, label, birim = _col(metrik)
    n = max(1, min(int(n), 81 if seviye == "il" else 50))
    order = "DESC" if str(yon).lower().startswith("d") else "ASC"
    tablo = "demographics_province" if seviye == "il" else "demographics_district"
    ad_col = "il_adi" if seviye == "il" else "ilce_adi"
    kod_col = "il_kodu" if seviye == "il" else "ilce_kodu"
    with _ro_conn() as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(
            f"SELECT {ad_col} AS ad, {kod_col} AS kod, {col} AS v FROM {tablo} "
            f"WHERE {col} IS NOT NULL ORDER BY {col} {order} LIMIT ?", (n,)).fetchall()
    liste = [{"ad": r["ad"], "deger": _fmt(r["v"])} for r in rows]
    return {"metrik": label, "birim": birim, "yon": order, "seviye": seviye,
            "yil": 2025, "kaynak": "TÜİK", "siralama": liste,
            "_codes": [r["kod"] for r in rows], "_metric": metrik, "_seviye": seviye}


def ilce_istatistik(il_adi, ilce_adi, metrik):
    col, label, birim = _col(metrik)
    code = _il_kodu(il_adi)
    target = norm(ilce_adi)
    with _ro_conn() as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(
            f"SELECT ilce_adi, ilce_kodu, {col} AS v, veri_yili "
            f"FROM demographics_district WHERE il_kodu=?", (code,)).fetchall()
    for r in rows:
        if norm(r["ilce_adi"]) == target:
            if r["v"] is None:
                return {"hata": f"{ilce_adi} ({il_adi}) için '{metrik}' verisi yok."}
            return {"il": IL_KODU_AD.get(int(code)), "ilce": r["ilce_adi"],
                    "metrik": label, "deger": _fmt(r["v"]), "birim": birim,
                    "yil": r["veri_yili"], "kaynak": "TÜİK", "_codes": [r["ilce_kodu"]]}
    return {"hata": f"{il_adi} ilinde '{ilce_adi}' ilçesi bulunamadı."}


def il_ilceleri(il_adi):
    code = _il_kodu(il_adi)
    with _ro_conn() as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT ilce_adi, ilce_kodu, toplam_nufus FROM demographics_district "
            "WHERE il_kodu=? ORDER BY toplam_nufus DESC", (code,)).fetchall()
    if not rows:
        return {"hata": f"{il_adi} için ilçe verisi yok."}
    return {"il": IL_KODU_AD.get(int(code)), "ilce_sayisi": len(rows), "yil": 2025,
            "kaynak": "TÜİK",
            "ilceler": [{"ilce": r["ilce_adi"], "toplam_nufus": r["toplam_nufus"]} for r in rows],
            "_codes": [r["ilce_kodu"] for r in rows]}


def turkiye_ozet(metrik):
    col, label, birim = _col(metrik)
    is_count = metrik in ("toplam_nufus", "erkek_nufus", "kadin_nufus")
    with _ro_conn() as db:
        db.row_factory = sqlite3.Row
        agg = "SUM" if is_count else "AVG"
        r = db.execute(
            f"SELECT {agg}({col}) AS toplam, "
            f"(SELECT il_adi FROM demographics_province WHERE {col} IS NOT NULL ORDER BY {col} DESC LIMIT 1) AS max_il, "
            f"MAX({col}) AS max_v, "
            f"(SELECT il_adi FROM demographics_province WHERE {col} IS NOT NULL ORDER BY {col} ASC LIMIT 1) AS min_il, "
            f"MIN({col}) AS min_v FROM demographics_province WHERE {col} IS NOT NULL").fetchone()
    out = {"metrik": label, "birim": birim, "yil": 2025, "kaynak": "TÜİK",
           "en_yuksek": {"il": r["max_il"], "deger": _fmt(r["max_v"])},
           "en_dusuk": {"il": r["min_il"], "deger": _fmt(r["min_v"])},
           "_metric": metrik}
    out["turkiye_toplam" if is_count else "iller_ortalamasi"] = _fmt(r["toplam"])
    return out


# ── POI: nokta sayımı (opsiyonel il filtresi point-in-polygon) ─────────────
def _pir(x, y, ring):
    inside = False; n = len(ring); j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]; xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def _pip(x, y, geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for poly in polys:
        if _pir(x, y, poly[0]) and not any(_pir(x, y, h) for h in poly[1:]):
            return True
    return False


COUNTRY_MAP = {
    "almanya": "DE", "fransa": "FR", "hollanda": "NL", "italya": "IT",
    "ispanya": "ES", "yunanistan": "EL", "lüksemburg": "LU", 
    "türkiye": "TR", "turkiye": "TR"
}

DIST_GEOJSON = os.path.join(ROOT, "data", "boundaries", "turkey_districts.geojson")

def poi_say(kategori, il_adi=None, ilce_adi=None, ulke="TR"):
    # Eğer model il_adi olarak ülke ismi gönderdiyse bunu otomatik düzelt:
    if il_adi and il_adi.strip().lower() in COUNTRY_MAP:
        ulke = COUNTRY_MAP[il_adi.strip().lower()]
        il_adi = None

    # Eğer ulke ISO kodu yerine doğrudan ülke adı geldiyse düzelt:
    if ulke and ulke.strip().lower() in COUNTRY_MAP:
        ulke = COUNTRY_MAP[ulke.strip().lower()]

    ulke = (ulke or "TR").strip().upper()
    if kategori not in POI_FILES:
        return {"hata": f"Geçersiz kategori. Geçerli: {', '.join(POI_FILES)}"}
    path = _poi_path(kategori, ulke)
    if not path:
        return {"hata": f"{ulke} için '{kategori}' POI verisi yüklü değil."}
    with open(path, encoding="utf-8") as f:
        feats = json.load(f).get("features", [])
    if ulke != "TR":
        return {"kategori": POI_LABEL[kategori], "kapsam": ulke,
                "sayi": len(feats), "kaynak": "OpenStreetMap"}
    if not il_adi:
        return {"kategori": POI_LABEL[kategori], "kapsam": "Türkiye",
                "sayi": len(feats), "kaynak": "OpenStreetMap"}
    
    code = _il_kodu(il_adi)
    geom = None
    kapsam_adi = IL_KODU_AD.get(int(code))
    _codes = [code]

    if ilce_adi:
        target_ilce = norm(ilce_adi)
        dist = json.load(open(DIST_GEOJSON, encoding="utf-8"))
        # il_kodu ile eşleşen ve norm(ilce_adi) ile eşleşen ilçeyi bul
        feat = next((f for f in dist["features"]
                     if str(f["properties"].get("il_kodu")) == code and 
                     norm(f["properties"].get("ilce_adi")) == target_ilce), None)
        if not feat:
            return {"hata": f"{il_adi} ilinde '{ilce_adi}' ilçesi veya sınır verisi bulunamadı."}
        geom = feat["geometry"]
        kapsam_adi = f"{kapsam_adi} - {feat['properties'].get('ilce_adi')}"
        _codes = [str(feat["properties"].get("ilce_kodu"))]
    else:
        prov = json.load(open(PROV_GEOJSON, encoding="utf-8"))
        geom = next((f["geometry"] for f in prov["features"]
                     if str(f["properties"].get("il_kodu")) == code), None)
        if not geom:
            return {"hata": f"{il_adi} sınırı bulunamadı."}
            
    cnt = 0
    for ft in feats:
        c = ft.get("geometry", {}).get("coordinates")
        if c and _pip(c[0], c[1], geom):
            cnt += 1
    return {"kategori": POI_LABEL[kategori], "kapsam": kapsam_adi,
            "sayi": cnt, "kaynak": "OpenStreetMap", "_codes": _codes}


# ── Araç şemaları (Ollama/OpenAI function-calling formatı) ─────────────────
_METRIK_ENUM = list(METRIC_INFO.keys())

TOOLS = [
    {"type": "function", "function": {
        "name": "il_istatistik",
        "description": "Bir ilin tek bir demografik metriğini (TÜİK 2025) döndürür.",
        "parameters": {"type": "object", "properties": {
            "il_adi": {"type": "string", "description": "İl adı, ör. İstanbul"},
            "metrik": {"type": "string", "enum": _METRIK_ENUM}},
            "required": ["il_adi", "metrik"]}}},
    {"type": "function", "function": {
        "name": "il_karsilastir",
        "description": "Birden fazla ili aynı metrikte karşılaştırır.",
        "parameters": {"type": "object", "properties": {
            "iller": {"type": "array", "items": {"type": "string"}},
            "metrik": {"type": "string", "enum": _METRIK_ENUM}},
            "required": ["iller", "metrik"]}}},
    {"type": "function", "function": {
        "name": "siralama",
        "description": "Bir metriğe göre en yüksek/düşük N il veya ilçeyi sıralar.",
        "parameters": {"type": "object", "properties": {
            "metrik": {"type": "string", "enum": _METRIK_ENUM},
            "yon": {"type": "string", "enum": ["desc", "asc"], "description": "desc=en yüksek"},
            "n": {"type": "integer", "description": "kaç kayıt (vars. 10)"},
            "seviye": {"type": "string", "enum": ["il", "ilce"]}},
            "required": ["metrik"]}}},
    {"type": "function", "function": {
        "name": "ilce_istatistik",
        "description": "Bir ilçenin tek bir demografik metriğini döndürür.",
        "parameters": {"type": "object", "properties": {
            "il_adi": {"type": "string"}, "ilce_adi": {"type": "string"},
            "metrik": {"type": "string", "enum": _METRIK_ENUM}},
            "required": ["il_adi", "ilce_adi", "metrik"]}}},
    {"type": "function", "function": {
        "name": "il_ilceleri",
        "description": "Bir ilin tüm ilçelerini ve nüfuslarını listeler.",
        "parameters": {"type": "object", "properties": {
            "il_adi": {"type": "string"}}, "required": ["il_adi"]}}},
    {"type": "function", "function": {
        "name": "turkiye_ozet",
        "description": "Bir metrik için Türkiye geneli özet (toplam/ortalama + en yüksek/düşük il).",
        "parameters": {"type": "object", "properties": {
            "metrik": {"type": "string", "enum": _METRIK_ENUM}}, "required": ["metrik"]}}},
    {"type": "function", "function": {
        "name": "poi_say",
        "description": "Bir kategoride nokta (POI) sayısı; ülke ve Türkiye için opsiyonel il ve ilçe filtresi (Türkiye içi sorgularda ilçeye kadar inilebilir).",
        "parameters": {"type": "object", "properties": {
            "kategori": {"type": "string", "enum": list(POI_FILES.keys())},
            "il_adi": {"type": "string", "description": "Sadece Türkiye sorguları için il adı (örn: Ankara)"},
            "ilce_adi": {"type": "string", "description": "Sadece Türkiye sorguları için ilçe adı (örn: Çankaya)"},
            "ulke": {"type": "string", "description": "ISO ülke kodu, ör. TR, DE, FR"}},
            "required": ["kategori"]}}},
]

_DISPATCH = {
    "il_istatistik": il_istatistik, "il_karsilastir": il_karsilastir,
    "siralama": siralama, "ilce_istatistik": ilce_istatistik,
    "il_ilceleri": il_ilceleri, "turkiye_ozet": turkiye_ozet, "poi_say": poi_say,
}


def execute_tool(name, args):
    """Aracı çalıştır; her zaman dict döner (hata dahil)."""
    fn = _DISPATCH.get(name)
    if not fn:
        return {"hata": f"Bilinmeyen araç: {name}"}
    try:
        return fn(**(args or {}))
    except ValueError as e:
        return {"hata": str(e)}
    except Exception as e:  # noqa: BLE001
        return {"hata": f"Araç çalıştırılamadı: {e}"}
