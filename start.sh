#!/bin/bash
# Türkiye GIS Uygulamasını Başlatır
# Kullanım: bash start.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/venv"
BACKEND="$SCRIPT_DIR/backend"

echo "================================================="
echo "  Türkiye GIS Uygulaması Başlatılıyor"
echo "================================================="

# Sanal ortam kontrol
if [ ! -d "$VENV" ]; then
    echo "Sanal ortam bulunamadı. Oluşturuluyor..."
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install -r "$BACKEND/requirements.txt" -q
    echo "Bağımlılıklar yüklendi."
fi

# Sınır verisi kontrol (OSM kaynaklı — basemap ile hizalı)
PROV="$SCRIPT_DIR/data/boundaries/turkey_provinces.geojson"
if [ ! -f "$PROV" ]; then
    echo "Sınır verisi eksik. OSM'den indiriliyor..."
    "$VENV/bin/python3" "$SCRIPT_DIR/scripts/fetch_osm_boundaries.py"
fi

# Demografik veri kontrol (gerçek TÜİK 2025 — koddan ayrık CSV)
DEMO="$SCRIPT_DIR/data/demographics/tuik_2025_il.csv"
if [ ! -f "$DEMO" ]; then
    echo "Demografik veri eksik. TÜİK 2025 çekiliyor..."
    "$VENV/bin/python3" "$SCRIPT_DIR/scripts/fetch_tuik.py"
fi
echo "Demografik veri yükleniyor (TÜİK 2025)..."
"$VENV/bin/python3" "$SCRIPT_DIR/scripts/load_demographics.py"

# Avrupa/NUTS verisi commit'lenmiş veya manuel üretilmişse DB indeksini yenile.
NUTS_INDEX="$SCRIPT_DIR/data/boundaries/nuts/index.json"
if [ -f "$NUTS_INDEX" ]; then
    echo "Avrupa NUTS bölge indeksi veritabanına yükleniyor..."
    "$VENV/bin/python3" "$SCRIPT_DIR/scripts/fetch_nuts_boundaries.py" --skip-download
else
    echo "Avrupa NUTS sınırları henüz yok (manuel: scripts/fetch_nuts_boundaries.py)."
fi
echo "Genel bölge istatistikleri yükleniyor..."
"$VENV/bin/python3" "$SCRIPT_DIR/scripts/load_regions_stats.py"

# Excel şablonu kontrol
TMPL="$SCRIPT_DIR/data/excel/template_nufus.xlsx"
if [ ! -f "$TMPL" ]; then
    echo "Excel şablonu oluşturuluyor..."
    "$VENV/bin/python3" "$SCRIPT_DIR/scripts/create_excel_template.py"
fi

echo ""
echo "Backend başlatılıyor: http://localhost:8000"
echo "Tarayıcıda açın: http://localhost:8000"
echo "(Durdurmak için Ctrl+C)"
echo ""

cd "$BACKEND"
"$VENV/bin/python3" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
