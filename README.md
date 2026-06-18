# GeoAtlas - Demografik Harita Platformu

## Kurulum ve Çalıştırma

### 1. Hızlı Başlangıç (Demo Modu)

En kolay yol — tüm kurulumu otomatik yapıp uygulamayı açar:

```bash
bash start_demo.sh
```

Bu komut:
- Sanal ortam (`venv`) oluşturur (yoksa)
- Bağımlılıkları yükler
- Veritabanını hazırlar
- Sunucuyu başlatır
- Tarayıcıda `http://localhost:8000` otomatik açılır

### 2. Manual Kurulum (Geliştiriciler)

#### A. Sanal Ortam Oluştur

```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# Windows: venv\Scripts\activate
```

#### B. Bağımlılıkları Yükle

```bash
pip install -r backend/requirements.txt
```

#### C. Veritabanı ve Verileri Hazırla

```bash
# Türkiye sınırlarını indir (OSM kaynağı)
python scripts/fetch_osm_boundaries.py

# TÜİK 2025 demografik verilerini indir
python scripts/fetch_tuik.py

# Veritabanına yükle
python scripts/load_demographics.py
python scripts/load_regions_stats.py

# Avrupa/NUTS bölgelerini indir (isteğe bağlı)
python scripts/fetch_nuts_boundaries.py

# Excel şablonu oluştur
python scripts/create_excel_template.py
```

#### D. Sunucuyu Başlat

```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Tarayıcıda açın: **http://localhost:8000**
