#!/usr/bin/env python3
"""
Eurostat CSV'leri ve mevcut TÜİK CSV'lerini region_stats tablosuna yükler.

Eurostat TR satırları atlanır; Türkiye için mevcut TÜİK 2025 il/ilçe verisi
önceliklidir.
"""
from __future__ import annotations

import csv
import os
import re
import sqlite3

from tr_util import IL_KODU_AD, il_nuts_code, ilce_lau_code

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data", "demographics")
DB = os.path.join(ROOT, "data", "db", "app.db")
IL_CSV = os.path.join(DATA, "tuik_2025_il.csv")
ILCE_CSV = os.path.join(DATA, "tuik_2025_ilce.csv")

EUROSTAT_RE = re.compile(r"^eurostat_(population|population_f|population_m|density|median_age|growth_rate)_(\d{4})\.csv$")


def to_int(value):
    value = (value or "").strip()
    return int(float(value)) if value not in ("", "None") else None


def to_float(value):
    value = (value or "").strip()
    return float(value) if value not in ("", "None") else None


def ensure_schema(con: sqlite3.Connection) -> None:
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
    con.execute("CREATE INDEX IF NOT EXISTS idx_region_stats_indicator_year ON region_stats(indicator, year)")


def upsert_region(con, code, country, level, parent, name, source):
    con.execute(
        """
        INSERT INTO regions (code, country, level, parent, name_en, name_tr, source)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(code) DO UPDATE SET
            country = excluded.country,
            level = excluded.level,
            parent = excluded.parent,
            name_en = COALESCE(regions.name_en, excluded.name_en),
            name_tr = COALESCE(regions.name_tr, excluded.name_tr),
            source = COALESCE(regions.source, excluded.source)
        """,
        (code, country, level, parent, name, name, source),
    )


def upsert_stat(con, code, indicator, year, value):
    if value is None:
        return
    con.execute(
        """
        INSERT INTO region_stats (code, indicator, year, value)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(code, indicator, year) DO UPDATE SET value = excluded.value
        """,
        (code, indicator, year, float(value)),
    )


def load_eurostat(con) -> int:
    count = 0
    if not os.path.isdir(DATA):
        return count
    for name in sorted(os.listdir(DATA)):
        match = EUROSTAT_RE.match(name)
        if not match:
            continue
        indicator, year_s = match.groups()
        year = int(year_s)
        with open(os.path.join(DATA, name), encoding="utf-8") as f:
            for row in csv.DictReader(f):
                code = (row.get("code") or "").strip().upper()
                if not code or code.startswith("TR"):
                    continue
                upsert_stat(con, code, indicator, year, to_float(row.get("value")))
                count += 1
        print(f"✓ {name} yüklendi")
    return count


def load_tuik_provinces(con) -> int:
    if not os.path.exists(IL_CSV):
        return 0
    count = 0
    with open(IL_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            il_kodu = row.get("il_kodu")
            code = il_nuts_code(il_kodu)
            if not code:
                continue
            year = to_int(row.get("veri_yili")) or 2025
            name = row.get("il_adi") or IL_KODU_AD.get(int(il_kodu), code)
            upsert_region(con, code, "TR", 3, code[:4], name, "tuik")
            upsert_stat(con, code, "population", year, to_int(row.get("toplam_nufus")))
            upsert_stat(con, code, "density", year, to_float(row.get("nufus_yogunluk")))
            upsert_stat(con, code, "median_age", year, to_float(row.get("medyan_yas")))
            count += 1
    print(f"✓ TÜİK il göstergeleri: {count} bölge")
    return count


def load_tuik_districts(con) -> int:
    if not os.path.exists(ILCE_CSV):
        return 0
    count = 0
    with open(ILCE_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            code = ilce_lau_code(row.get("ilce_kodu"), row.get("il_kodu"))
            parent = il_nuts_code(row.get("il_kodu"))
            if not code or not parent:
                continue
            year = to_int(row.get("veri_yili")) or 2025
            upsert_region(con, code, "TR", 4, parent, row.get("ilce_adi") or code, "tuik")
            upsert_stat(con, code, "population", year, to_int(row.get("toplam_nufus")))
            count += 1
    print(f"✓ TÜİK ilçe göstergeleri: {count} bölge")
    return count


def compute_derived_stats(con) -> int:
    """population_f ve population_m değerlerinden kadin_oran ve erkek_oran hesaplar."""
    cursor = con.cursor()
    
    # Kadın oranı hesapla
    cursor.execute("""
        INSERT INTO region_stats (code, indicator, year, value)
        SELECT pf.code, 'kadin_oran', pf.year, (pf.value / p.value) * 100.0
        FROM region_stats pf
        JOIN region_stats p ON pf.code = p.code AND pf.year = p.year AND p.indicator = 'population'
        WHERE pf.indicator = 'population_f' AND p.value > 0
        ON CONFLICT(code, indicator, year) DO UPDATE SET value = excluded.value
    """)
    kadin_count = cursor.rowcount
    
    # Erkek oranı hesapla
    cursor.execute("""
        INSERT INTO region_stats (code, indicator, year, value)
        SELECT pm.code, 'erkek_oran', pm.year, (pm.value / p.value) * 100.0
        FROM region_stats pm
        JOIN region_stats p ON pm.code = p.code AND pm.year = p.year AND p.indicator = 'population'
        WHERE pm.indicator = 'population_m' AND p.value > 0
        ON CONFLICT(code, indicator, year) DO UPDATE SET value = excluded.value
    """)
    erkek_count = cursor.rowcount
    
    print(f"✓ Türetilen oranlar: {kadin_count} kadın, {erkek_count} erkek")
    return kadin_count + erkek_count


def main() -> None:
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = sqlite3.connect(DB)
    ensure_schema(con)
    eurostat_count = load_eurostat(con)
    tr_province_count = load_tuik_provinces(con)
    tr_district_count = load_tuik_districts(con)
    derived_count = compute_derived_stats(con)
    con.commit()
    con.close()
    print(
        "Tamamlandı: "
        f"Eurostat {eurostat_count}, "
        f"TR il {tr_province_count}, "
        f"TR ilçe {tr_district_count}, "
        f"türetilen {derived_count}"
    )


if __name__ == "__main__":
    main()
