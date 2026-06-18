#!/usr/bin/env python3
"""
data/demographics/tuik_2025_*.csv → SQLite (demographics_province / district).

fetch_tuik.py'nin ürettiği gerçek TÜİK 2025 CSV'lerini veritabanına yükler.
Tam (kanonik) veri seti olduğu için ilgili tablolar temizlenip yeniden yazılır.
Excel import yolu ayrıca kısmi UPSERT yapar (excel_upload.py).
"""
import os
import sys
import csv
import sqlite3

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(ROOT, "data", "demographics")
DB = os.path.join(ROOT, "data", "db", "app.db")

IL_CSV = os.path.join(DATA, "tuik_2025_il.csv")
ILCE_CSV = os.path.join(DATA, "tuik_2025_ilce.csv")


def _i(v):
    v = (v or "").strip()
    return int(float(v)) if v not in ("", "None") else None


def _f(v):
    v = (v or "").strip()
    return float(v) if v not in ("", "None") else None


def ensure_schema(con):
    con.execute("""
        CREATE TABLE IF NOT EXISTS demographics_province (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            il_kodu TEXT NOT NULL UNIQUE, il_adi TEXT NOT NULL,
            toplam_nufus INTEGER, erkek_nufus INTEGER, kadin_nufus INTEGER,
            yas_0_14 INTEGER, yas_15_64 INTEGER, yas_65_ust INTEGER,
            medyan_yas REAL, nufus_yogunluk REAL, nufus_artis_hizi REAL,
            veri_yili INTEGER DEFAULT 2025)
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS demographics_district (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            il_kodu TEXT NOT NULL, il_adi TEXT, ilce_kodu TEXT NOT NULL UNIQUE,
            ilce_adi TEXT NOT NULL,
            toplam_nufus INTEGER, erkek_nufus INTEGER, kadin_nufus INTEGER,
            yas_0_14 INTEGER, yas_15_64 INTEGER, yas_65_ust INTEGER,
            medyan_yas REAL, nufus_yogunluk REAL,
            veri_yili INTEGER DEFAULT 2025)
    """)
    # eski DB'lerde yeni kolonları ekle
    for table, col, typ in [
        ("demographics_province", "medyan_yas", "REAL"),
        ("demographics_province", "nufus_yogunluk", "REAL"),
        ("demographics_province", "nufus_artis_hizi", "REAL"),
        ("demographics_district", "medyan_yas", "REAL"),
        ("demographics_district", "nufus_yogunluk", "REAL"),
    ]:
        cols = [r[1] for r in con.execute(f"PRAGMA table_info({table})")]
        if col not in cols:
            con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")


def main():
    if not (os.path.exists(IL_CSV) and os.path.exists(ILCE_CSV)):
        print("CSV bulunamadı. Önce: python scripts/fetch_tuik.py")
        sys.exit(1)

    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = sqlite3.connect(DB)
    ensure_schema(con)

    con.execute("DELETE FROM demographics_province")
    with open(IL_CSV, encoding="utf-8") as f:
        n = 0
        for r in csv.DictReader(f):
            con.execute("""INSERT INTO demographics_province
                (il_kodu, il_adi, toplam_nufus, erkek_nufus, kadin_nufus,
                 medyan_yas, nufus_yogunluk, nufus_artis_hizi, veri_yili)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (r["il_kodu"], r["il_adi"], _i(r["toplam_nufus"]),
                 _i(r["erkek_nufus"]), _i(r["kadin_nufus"]), _f(r["medyan_yas"]),
                 _f(r["nufus_yogunluk"]), _f(r["nufus_artis_hizi"]), _i(r["veri_yili"])))
            n += 1
    print(f"✓ {n} il yüklendi")

    con.execute("DELETE FROM demographics_district")
    with open(ILCE_CSV, encoding="utf-8") as f:
        m = 0
        for r in csv.DictReader(f):
            con.execute("""INSERT INTO demographics_district
                (il_kodu, il_adi, ilce_kodu, ilce_adi, toplam_nufus,
                 erkek_nufus, kadin_nufus, veri_yili)
                VALUES (?,?,?,?,?,?,?,?)""",
                (r["il_kodu"], r["il_adi"], r["ilce_kodu"], r["ilce_adi"],
                 _i(r["toplam_nufus"]), _i(r["erkek_nufus"]), _i(r["kadin_nufus"]),
                 _i(r["veri_yili"])))
            m += 1
    print(f"✓ {m} ilçe yüklendi")

    con.commit()
    # özet
    tr = con.execute("SELECT SUM(toplam_nufus) FROM demographics_province").fetchone()[0]
    print(f"Türkiye toplam: {tr:,}")
    con.close()


if __name__ == "__main__":
    main()
