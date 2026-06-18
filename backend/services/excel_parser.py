import pandas as pd
from typing import List, Dict, Any
import io


# Beklenen sütun isimleri (il sheet) — din alanları KALDIRILDI;
# gerçek TÜİK metrikleri eklendi. il_kodu opsiyonel (il_adi'dan çözülür).
PROVINCE_COLUMNS = [
    "il_kodu", "il_adi", "toplam_nufus", "erkek_nufus", "kadin_nufus",
    "yas_0_14", "yas_15_64", "yas_65_ust",
    "medyan_yas", "nufus_yogunluk", "nufus_artis_hizi", "veri_yili"
]

# Beklenen sütun isimleri (ilçe sheet) — ilce_kodu opsiyonel (il+ilçe adından çözülür)
DISTRICT_COLUMNS = [
    "il_kodu", "il_adi", "ilce_kodu", "ilce_adi", "toplam_nufus",
    "erkek_nufus", "kadin_nufus",
    "yas_0_14", "yas_15_64", "yas_65_ust",
    "medyan_yas", "nufus_yogunluk", "veri_yili"
]

# Etiket sheet sütunları
LABEL_COLUMNS = ["etiket_adi", "enlem", "boylam", "renk", "aciklama", "ikon"]


def _is_empty(val) -> bool:
    """Değerin boş/NaN olup olmadığını kontrol eder (pandas ve None dahil)."""
    if val is None:
        return True
    if isinstance(val, str):
        return val.strip() == "" or val.strip().lower() == "nan"
    try:
        return bool(pd.isna(val))
    except (TypeError, ValueError):
        return False


def _read_sheet(buf: io.BytesIO, sheet_name: str) -> pd.DataFrame:
    """Excel sheet'ini oku, sütun adlarını normalize et."""
    df = pd.read_excel(buf, sheet_name=sheet_name, dtype=str)
    # Sütun adlarını küçük harfe çevir, boşlukları alt çizgiye çevir
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    return df


def _clean_val(val):
    """Boş değerleri None'a, diğerlerini string'e dönüştürür."""
    if _is_empty(val):
        return None
    return str(val).strip()


def parse_province_sheet(buf: io.BytesIO) -> List[Dict[str, Any]]:
    """'Nufus_Il' sheet'ini parse eder."""
    df = _read_sheet(buf, "Nufus_Il")

    missing = [c for c in ["il_adi", "toplam_nufus"] if c not in df.columns]
    if missing:
        raise ValueError(f"Eksik zorunlu sütunlar: {missing}")

    records = []
    for _, row in df.iterrows():
        il_adi = _clean_val(row.get("il_adi"))
        if not il_adi:
            continue
        record = {col: _clean_val(row.get(col)) for col in PROVINCE_COLUMNS}
        records.append(record)
    return records


def parse_district_sheet(buf: io.BytesIO) -> List[Dict[str, Any]]:
    """'Nufus_Ilce' sheet'ini parse eder."""
    df = _read_sheet(buf, "Nufus_Ilce")

    missing = [c for c in ["il_adi", "ilce_adi"] if c not in df.columns]
    if missing:
        raise ValueError(f"Eksik zorunlu sütunlar: {missing}")

    records = []
    for _, row in df.iterrows():
        ilce_adi = _clean_val(row.get("ilce_adi"))
        if not ilce_adi:
            continue
        record = {col: _clean_val(row.get(col)) for col in DISTRICT_COLUMNS}
        records.append(record)
    return records


REGION_STATS_INDICATORS = [
    "population", "population_m", "population_f",
    "density", "median_age", "growth_rate",
    "erkek_oran", "kadin_oran",
]


def parse_region_stats_sheet(buf: io.BytesIO) -> List[Dict[str, Any]]:
    """'Region_Stats' sheet'ini parse eder — her satır bir NUTS kodu, kolonlar göstergeler."""
    df = _read_sheet(buf, "Region_Stats")

    if "code" not in df.columns:
        raise ValueError("Zorunlu 'code' sütunu eksik.")

    records = []
    for _, row in df.iterrows():
        code = _clean_val(row.get("code"))
        if not code:
            continue
        raw_year = _clean_val(row.get("year"))
        year = int(raw_year) if raw_year and raw_year.isdigit() else 2025
        for indicator in REGION_STATS_INDICATORS:
            raw = _clean_val(row.get(indicator))
            if raw is None:
                continue
            try:
                value = float(raw.replace(",", "."))
                records.append({"code": code, "indicator": indicator, "year": year, "value": value})
            except ValueError:
                pass
    return records


def parse_labels_sheet(buf: io.BytesIO) -> List[Dict[str, Any]]:
    """'Disaridan_Etiketler' sheet'ini parse eder."""
    df = _read_sheet(buf, "Disaridan_Etiketler")

    missing = [c for c in ["etiket_adi", "enlem", "boylam"] if c not in df.columns]
    if missing:
        raise ValueError(f"Eksik zorunlu sütunlar: {missing}")

    records = []
    for _, row in df.iterrows():
        enlem = _clean_val(row.get("enlem"))
        boylam = _clean_val(row.get("boylam"))
        if not enlem or not boylam:
            continue
        record = {col: _clean_val(row.get(col)) for col in LABEL_COLUMNS}
        if not record.get("etiket_adi"):
            record["etiket_adi"] = "Etiket"
        if not record.get("renk"):
            record["renk"] = "#FF5733"
        if not record.get("ikon"):
            record["ikon"] = "pin"
        records.append(record)
    return records
