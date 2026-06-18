# GeoAtlas - Demografik Harita Platformu

GeoAtlas, Türkiye ve Avrupa bölgeleri için interaktif haritalar, demografik veriler ve coğrafi analiz araçları sağlayan bir web uygulamasıdır.

## 📋 Sistem Gereksinimleri

- **Python**: 3.8+
- **macOS / Linux / Windows** (bash ortamı gerekir)
- **Tarayıcı**: Modern web tarayıcısı (Chrome, Firefox, Safari vb.)

## 🚀 Kurulum ve Çalıştırma

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

## 📁 Proje Yapısı

```
mapping-project/
├── backend/                    # FastAPI sunucusu
│   ├── main.py                 # Ana uygulama
│   ├── requirements.txt         # Python bağımlılıkları
│   ├── models/                 # Veri modelleri
│   ├── routers/                # API uç noktaları
│   └── services/               # İş mantığı (DB, Geo, vb.)
├── frontend/                   # Statik web arayüzü
│   ├── index.html              # Ana sayfa
│   ├── js/                     # JavaScript uygulaması
│   ├── css/                    # Stiller
│   └── assets/                 # İkonlar vb.
├── data/                       # Veri dosyaları
│   ├── boundaries/             # Sınır verisi (GEOJSON)
│   ├── demographics/           # Demografik veriler (CSV)
│   ├── poi/                    # İlgi noktaları (POI)
│   └── db/                     # SQLite veritabanı
├── scripts/                    # Veri alma ve hazırlama
└── venv/                       # Sanal ortam (otomatik oluşturulur)
```

## 🔧 Ana Özellikler

### Harita Görselleştirmesi
- Türkiye il/ilçe sınırları (OpenStreetMap)
- Avrupa NUTS bölgeleri (3 seviye)
- Etkileşimli harita kontrolü (zoom, pan)
- GeoJSON tabanlı sınır verileri

### Demografik Veriler
- **TÜİK 2025**: Nüfus, yaş dağılımı, cinsiyet oranları
- **Eurostat**: Avrupa bölgeleri için yoğunluk, büyüme oranı, medyan yaş
- CSV kaynaklı veri (kodda hardcoded değil)
- Veritabanında indekslenmiş sorgular

### İlgi Noktaları (POI)
- Kiliseler, Camiler, Okullar, Üniversiteler, Okul öncesi
- Türkiye ve Avrupa (DE, ES, FR, IT vb.)
- OpenStreetMap/Overpass API kaynağı
- Sınır içinde filtreleme

### Diğer Özellikleri
- LLM entegrasyonu (AI sorguları)
- Excel dosyası yükleme ve çözümleme
- Grup ve Etiket yönetimi
- Dinamik veri sorguları

## 📡 API Uç Noktaları

Tüm API uç noktaları `http://localhost:8000/docs` (Swagger) veya `http://localhost:8000/redoc` (ReDoc) adreslerinde belgelenmiştir.

### Ana Kategoriler
- `/api/boundaries` - Sınır verileri
- `/api/demographics` - Demografik bilgiler
- `/api/poi` - İlgi noktaları
- `/api/regions` - Avrupa bölgeleri
- `/api/groups` - Veri grupları
- `/api/labels` - Etiketleme
- `/api/excel` - Excel işlemleri
- `/api/chat` - LLM sorguları

## 🌐 Tarayıcıda Kullanım

1. **Harita Görüntüle**: Ana sayfa açıldığında Türkiye haritası yüklenir
2. **Bölgeye Tıkla**: İl/ilçeye tıklayarak demografik bilgileri görebilirsiniz
3. **Veri Karşılaştır**: Farklı bölgeler seçerek karşılaştırmalar yapabilirsiniz
4. **Avrupa Bölgeleri**: Avrupa veri seti mevcutsa NUTS bölgelerine geçiş yapabilirsiniz
5. **Dosya Yükle**: Excel dosyası yükleyerek özel veriler ekleyebilirsiniz

## 🔍 Sorun Giderme

### Sorunu: "Port 8000 zaten kullanılıyor"
```bash
# Port temizle (macOS/Linux)
lsof -ti:8000 | xargs kill -9

# Veya farklı port kullan
python -m uvicorn main:app --port 8001
```

### Sorunu: "Veri dosyaları eksik"
```bash
# Tüm verileri yeniden indir
bash start.sh
```

### Sorunu: "Sanal ortam bulunamadı"
```bash
# Sanal ortamı sıfırla
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

### Sorunu: "Veritabanı hatası"
```bash
# Veritabanını sıfırla
rm -f data/db/app.db data/demographics.db
python scripts/load_demographics.py
```

## 📦 Bağımlılıklar

| Paket | Kullanım |
|-------|----------|
| `fastapi` | Web framework |
| `uvicorn` | ASGI sunucusu |
| `geopandas` | Coğrafi veri analizi |
| `shapely` | Geometri işlemleri |
| `pandas` | Veri işleme |
| `openpyxl` | Excel dosyaları |
| `aiosqlite` | Async SQLite |
| `requests` | HTTP istekleri |
| `httpx` | Async HTTP |

## 🛠️ Geliştirme Modu

Kodda değişiklikler yapmak ve anında görmek için:

```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

`--reload` flag'i dosya değişikliklerini izler ve sunucuyu otomatik yeniden başlatır.

## 📊 Veri Kaynakları

- **Sınırlar**: OpenStreetMap (OSM), GADM, NUTS (Eurostat)
- **Demografik**: Türkiye (TÜİK 2025), Avrupa (Eurostat)
- **POI**: OpenStreetMap (Overpass API)

## 🔐 Lisans

MIT Lisansı — Bkz. [LICENSE](LICENSE) dosyası.

## 📞 İletişim ve Destek

Sorular veya öneriler için:
- GitHub Issues: [Proje sayfası](https://github.com/ardayasan/GeoAtlas)
- E-posta: [Projeye bakın]

---

**Sürüm**: 1.0.0  
**Son Güncelleme**: Haziran 2026
