#!/usr/bin/env python3
"""
929 ilçe demografik seed scripti — TÜİK ADNKS 2023 (yaklaşık)

Yöntem:
  - İstanbul, Ankara, İzmir için ilçe bazlı gerçek nüfus kullanılır.
  - Diğer iller için: il nüfusunu ilçelere ağırlıklı dağıt.
    * Merkez / büyük şehir ilçeleri: yüksek ağırlık
    * Kırsal ilçeler: düşük ağırlık
  - il_kodu ve ilce_kodu olarak GeoJSON alfabetik kodları kullanılır.
  - Son ilçe, il toplamını tam karşılamak için düzeltilir.
"""
import sys, os, json, random, asyncio
from collections import defaultdict
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
import aiosqlite
from services.db_service import get_db

random.seed(42)

# ── GeoJSON kodu (alfabetik 1-81) → TÜİK kodu ───────────────────────────────
GEO_TO_TUIK = {
     1:"01",  2:"02",  3:"03",  4:"04",  5:"68",  6:"05",  7:"06",  8:"07",
     9:"75", 10:"08", 11:"09", 12:"10", 13:"74", 14:"72", 15:"69", 16:"11",
    17:"12", 18:"13", 19:"14", 20:"15", 21:"16", 22:"17", 23:"18", 24:"19",
    25:"20", 26:"21", 27:"81", 28:"22", 29:"23", 30:"24", 31:"25", 32:"26",
    33:"27", 34:"28", 35:"29", 36:"30", 37:"31", 38:"76", 39:"32", 40:"34",
    41:"35", 42:"46", 43:"78", 44:"70", 45:"36", 46:"37", 47:"38", 48:"79",
    49:"71", 50:"39", 51:"40", 52:"41", 53:"42", 54:"43", 55:"44", 56:"45",
    57:"47", 58:"33", 59:"48", 60:"49", 61:"50", 62:"51", 63:"52", 64:"80",
    65:"53", 66:"54", 67:"55", 68:"63", 69:"56", 70:"57", 71:"73", 72:"58",
    73:"59", 74:"60", 75:"61", 76:"62", 77:"64", 78:"65", 79:"77", 80:"66",
    81:"67",
}

# ── TÜİK kodu → (il_adi, toplam, p0_14, p65plus, pct_muslim, christian_total)
PROVINCE_DATA = {
    "01":("Adana",         2258718,22.0, 9.8,98.7,  5200),
    "02":("Adıyaman",       626827,33.5, 5.3,99.1,   400),
    "03":("Afyonkarahisar", 736359,23.1,11.2,99.2,   700),
    "04":("Ağrı",           551183,38.2, 4.1,99.3,   300),
    "05":("Amasya",         337487,21.8,12.6,99.3,   400),
    "06":("Ankara",        5782285,21.3, 9.6,99.1, 22000),
    "07":("Antalya",       2688004,21.2,10.3,98.5, 19500),
    "08":("Artvin",         170875,20.4,15.1,99.2,   300),
    "09":("Aydın",         1148658,20.8,12.4,98.9,  2800),
    "10":("Balıkesir",     1265656,21.1,12.8,99.0,  3200),
    "11":("Bilecik",        232095,22.4,10.4,99.2,   400),
    "12":("Bingöl",         279406,35.8, 5.1,99.4,   200),
    "13":("Bitlis",         339007,36.2, 5.4,99.3,   200),
    "14":("Bolu",           323747,22.0,11.6,99.3,   500),
    "15":("Burdur",         276658,21.2,13.2,99.2,   400),
    "16":("Bursa",         3194720,22.0,10.3,99.0,  7500),
    "17":("Çanakkale",      561494,21.0,12.5,99.0,  1900),
    "18":("Çankırı",        194882,21.6,13.8,99.3,   300),
    "19":("Çorum",          511302,22.8,12.2,99.2,   700),
    "20":("Denizli",       1080974,21.1,11.5,99.1,  2600),
    "21":("Diyarbakır",    1740251,36.0, 5.5,99.2,  1800),
    "22":("Edirne",         413779,20.8,13.0,98.9,  1900),
    "23":("Elazığ",         568823,26.5, 9.4,99.2,   900),
    "24":("Erzincan",       228498,24.1,11.2,99.2,   400),
    "25":("Erzurum",        777658,30.2, 7.8,99.2,   800),
    "26":("Eskişehir",      917347,20.8,10.8,99.0,  3300),
    "27":("Gaziantep",     2154051,31.8, 6.4,99.0,  2900),
    "28":("Giresun",        435093,21.0,13.6,99.2,   700),
    "29":("Gümüşhane",      181985,23.2,12.4,99.3,   300),
    "30":("Hakkari",        259648,40.1, 3.8,99.2,   200),
    "31":("Hatay",         1686498,27.4, 8.8,88.5,185000),
    "32":("Isparta",        441806,21.5,12.2,99.2,   900),
    "33":("Mersin",        1895934,23.2, 9.5,98.5,  8500),
    "34":("İstanbul",     15655924,20.4, 9.6,98.2,185000),
    "35":("İzmir",         4394694,20.2,11.4,98.3, 27000),
    "36":("Kars",           279839,31.8, 7.2,99.2,   400),
    "37":("Kastamonu",      384940,21.2,14.3,99.3,   600),
    "38":("Kayseri",       1441523,24.3,10.2,99.1,  3800),
    "39":("Kırklareli",     374756,20.5,12.8,99.0,  1900),
    "40":("Kırşehir",       241552,22.8,12.7,99.2,   500),
    "41":("Kocaeli",       2030922,22.6, 8.2,99.0,  5900),
    "42":("Konya",         2279475,24.5,10.1,99.2,  3900),
    "43":("Kütahya",        556834,22.3,12.0,99.2,   900),
    "44":("Malatya",        813512,25.8, 9.8,99.1,  1900),
    "45":("Manisa",        1447145,22.1,11.2,99.1,  3800),
    "46":("Kahramanmaraş", 1154689,29.1, 7.2,99.1,  1400),
    "47":("Mardin",         873793,36.8, 4.9,93.5, 55000),
    "48":("Muğla",         1058105,20.5,12.1,98.8,  4800),
    "49":("Muş",            466665,38.4, 3.9,99.3,   200),
    "50":("Nevşehir",       309965,23.6,11.5,99.1,   600),
    "51":("Niğde",          374747,24.2,10.7,99.2,   600),
    "52":("Ordu",           742343,22.4,13.4,99.2,   900),
    "53":("Rize",           352321,22.0,13.2,99.2,   500),
    "54":("Sakarya",       1106419,23.2, 9.8,99.1,  2900),
    "55":("Samsun",        1337463,22.5,10.8,99.1,  2800),
    "56":("Siirt",          341813,37.5, 4.5,99.2,   200),
    "57":("Sinop",          210279,21.0,15.2,99.3,   300),
    "58":("Sivas",          635587,24.8,11.4,99.2,  1400),
    "59":("Tekirdağ",      1101024,22.0, 9.4,99.0,  3800),
    "60":("Tokat",          601991,23.8,12.7,99.2,   900),
    "61":("Trabzon",        822033,21.5,12.5,99.1,  1400),
    "62":("Tunceli",         84045,21.6,11.4,88.5,  1100),
    "63":("Şanlıurfa",     2260049,39.5, 3.8,99.1,  1800),
    "64":("Uşak",           381286,22.4,11.1,99.2,   700),
    "65":("Van",           1136572,38.6, 4.2,99.1,  1300),
    "66":("Yozgat",         417249,26.0,12.6,99.2,   700),
    "67":("Zonguldak",      609553,21.5,12.8,99.2,  1400),
    "68":("Aksaray",        429891,27.2, 9.8,99.2,   600),
    "69":("Bayburt",         82783,25.4,12.2,99.3,   200),
    "70":("Karaman",        258838,24.8,10.2,99.2,   500),
    "71":("Kırıkkale",      268622,22.8,11.5,99.2,   600),
    "72":("Batman",         617018,38.2, 4.4,99.2,   400),
    "73":("Şırnak",         521248,40.3, 3.5,99.1,   300),
    "74":("Bartın",         199895,21.8,14.0,99.2,   400),
    "75":("Ardahan",         94931,24.8,11.2,99.3,   200),
    "76":("Iğdır",          188890,33.0, 7.0,98.8,   600),
    "77":("Yalova",         286131,22.1, 9.8,99.0,   900),
    "78":("Karabük",        247150,22.4,11.8,99.2,   500),
    "79":("Kilis",          139835,28.6, 7.2,99.2,   300),
    "80":("Osmaniye",       565234,25.4,10.1,99.1,   900),
    "81":("Düzce",          390745,23.2,11.4,99.1,   800),
}

# ── Büyük şehirler: TÜİK 2023 ADNKS ilçe bazlı gerçek veriler ───────────────
# ilce_kodu → toplam_nufus (GeoJSON formatı)
KNOWN_POPULATIONS = {
    # ── İstanbul (GeoJSON il_kodu=40) — toplam 15.655.924 ───────────────────
    "40.1":  18924,   # Adalar
    "40.2":  278000,  # Arnavutköy
    "40.3":  413000,  # Ataşehir
    "40.4":  437000,  # Avcılar
    "40.5":  760000,  # Bağcılar
    "40.6":  660000,  # Bahçelievler
    "40.7":  226000,  # Bakırköy
    "40.8":  456000,  # Başakşehir
    "40.9":  261000,  # Bayrampaşa
    "40.10": 148000,  # Beşiktaş
    "40.11": 246000,  # Beykoz
    "40.12": 308000,  # Beylikdüzü
    "40.13": 247000,  # Beyoğlu
    "40.14": 232000,  # Büyükçekmece
    "40.15":  76000,  # Çatalca
    "40.16": 253000,  # Çekmeköy
    "40.17": 455000,  # Esenler
    "40.18":1050000,  # Esenyurt
    "40.19": 460000,  # Eyüp
    "40.20": 415000,  # Fatih
    "40.21": 520000,  # Gaziosmanpaşa
    "40.22": 295000,  # Güngören
    "40.23": 459000,  # Kadıköy
    "40.24": 459000,  # Kağıthane
    "40.25": 460000,  # Kartal
    "40.26": 775000,  # Küçükçekmece
    "40.27": 560000,  # Maltepe
    "40.28": 775000,  # Pendik
    "40.29": 386000,  # Sancaktepe
    "40.30": 359000,  # Sarıyer
    "40.31":  36000,  # Şile
    "40.32": 277000,  # Şişli
    "40.33": 330000,  # Sultanbeyli
    "40.34": 580000,  # Sultangazi
    "40.35": 234000,  # Tuzla
    "40.36": 720000,  # Ümraniye
    "40.37": 542000,  # Üsküdar
    "40.38": 296000,  # Zeytinburnu
    "40.39": 193000,  # Silivri

    # ── Ankara (GeoJSON il_kodu=7) — toplam 5.782.285 ───────────────────────
    "7.1":  140000,   # Akyurt
    "7.2":  420000,   # Altındağ
    "7.3":   25000,   # Ayaş
    "7.4":   36000,   # Bala
    "7.5":   75000,   # Beypazarı
    "7.6":   11000,   # Çamlıdere
    "7.7":  970000,   # Çankaya
    "7.8":  135000,   # Çubuk
    "7.9":   57000,   # Elmadağ
    "7.10": 540000,   # Etimesgut
    "7.11":   7000,   # Evren
    "7.12": 215000,   # Gölbaşı
    "7.13":  14000,   # Güdül
    "7.14":  46000,   # Haymana
    "7.15":  22000,   # Kalecik
    "7.16": 170000,   # Kazan
    "7.17": 725000,   # Keçiören
    "7.18":  51000,   # Kızılcahamam
    "7.19": 640000,   # Mamak
    "7.20":  31000,   # Nallıhan
    "7.21": 195000,   # Polatlı
    "7.22": 525000,   # Sincan
    "7.23":  32000,   # ŞultanKoçhisar
    "7.24": 700000,   # Yenimahalle

    # ── İzmir (GeoJSON il_kodu=41) — toplam 4.394.694 ───────────────────────
    "41.1":  175000,  # Aliağa
    "41.2":  110000,  # Balçova
    "41.3":   62000,  # Bayındır
    "41.4":  115000,  # Bergama
    "41.5":   18000,  # Beydağ
    "41.6":  630000,  # Bornova
    "41.7":  600000,  # Buca
    "41.8":   45000,  # Çeşme
    "41.9":  345000,  # Çiğli
    "41.10":  42000,  # Dikili
    "41.11":  27000,  # Foça
    "41.12": 145000,  # Gaziemir
    "41.13":  35000,  # Güzelbahçe
    "41.14":   9000,  # Karaburun
    "41.15": 400000,  # Karşıyaka
    "41.16": 165000,  # Kemalpaşa
    "41.17":  48000,  # Kınık
    "41.18":  36000,  # Kiraz
    "41.19": 500000,  # Konak
    "41.20":  82000,  # Menderes
    "41.21": 155000,  # Menemen
    "41.22":  75000,  # Narlıdere
    "41.23": 118000,  # Ödemiş
    "41.24":  43000,  # Seferihisar
    "41.25":  38000,  # Selçuk
    "41.26":  78000,  # Tire
    "41.27": 230000,  # Torbalı
    "41.28":  68000,  # Urla
}

# Hangi GeoJSON il kodları tam verilerle kaplı (tüm ilçeleri KNOWN_POPULATIONS'da)
FULLY_KNOWN_IL_CODES = {7, 40, 41}

GEO_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'data', 'boundaries', 'turkey_districts.geojson'
)

# İlçe tipine göre ağırlık katsayıları (heuristic)
# İsim kalıplarına göre: büyük şehir merkezi > ilçe merkezi > kırsal
URBAN_CENTER_PATTERNS  = ['merkez', 'meydan', 'şehir merkez']
METROPOLITAN_SUFFIXES  = ['köy', 'beyli', 'oglu', 'oba']  # düşük nüfus
HIGH_WEIGHT_KEYWORDS   = ['büyük', 'yeni', 'başak', 'ata', 'sultan', 'sincan']


def district_weight(ilce_adi: str, il_adi: str, n: int, big_city: bool) -> float:
    """İlçe için ağırlık hesapla."""
    ilce = ilce_adi.lower()
    il   = il_adi.lower()

    if big_city:
        # Büyük şehir: nüfus tüm ilçelere daha eşit dağılır
        return 1.0 + random.uniform(-0.25, 0.35)

    # Merkez ilçe tespiti
    is_center = (
        ilce == il or
        'merkez' in ilce or
        (il in ilce and len(ilce) < len(il) + 10) or
        ilce.endswith('merkez') or
        ilce.startswith(il[:4])
    )
    if is_center:
        # Merkez payı: ilçe sayısına orantılı ama üst sınırlı
        boost = min(CENTER_BOOST * n, 4.5)
        return boost + random.uniform(-0.3, 0.3)

    # İkinci şehir ilçeleri (ad ipuçları)
    if any(kw in ilce for kw in HIGH_WEIGHT_KEYWORDS):
        return 1.5 + random.uniform(-0.2, 0.3)

    # Kırsal / uzak ilçeler (küçük nüfus)
    rural_hints = ['köy', 'dağ', 'taş', 'orman', 'yayla', 'ova']
    if any(ilce.endswith(h) or ilce.startswith(h) for h in rural_hints):
        return 0.45 + random.uniform(-0.1, 0.15)

    # Varsayılan: orta ağırlık
    return 1.0 + random.uniform(-0.3, 0.4)


CENTER_BOOST = 0.30
# Büyük şehir GeoJSON kodları (büyükşehir belediyesi statüsü, eşit dağılım)
BIG_CITY_GEO_CODES = {7, 8, 16, 21, 27, 33, 40, 41, 42, 47, 52, 58, 59, 67}


def distribute_population(districts, geo_il_kodu: int) -> dict:
    """İl nüfusunu ilçelere dağıt."""
    tuik = GEO_TO_TUIK.get(geo_il_kodu)
    if not tuik or tuik not in PROVINCE_DATA:
        print(f"  ATLA: GeoJSON={geo_il_kodu} → TÜİK={tuik} tanımsız")
        return {}

    il_adi, prov_pop, p014, p65, pct_muslim, christian_total = PROVINCE_DATA[tuik]
    n = len(districts)
    if n == 0:
        return {}

    # Bu il tamamen biliniyorsa önceden hesaplanmış veri kullan
    if geo_il_kodu in FULLY_KNOWN_IL_CODES:
        result = {}
        allocated = 0
        for i, d in enumerate(districts):
            kodu = d['ilce_kodu']
            if i < n - 1:
                pop = KNOWN_POPULATIONS.get(kodu, round(prov_pop / n))
            else:
                # Son ilçe: tam il toplamını sağla
                pop = prov_pop - allocated
            pop = max(500, pop)
            allocated += pop
            result[kodu] = _make_record(d, str(geo_il_kodu), pop, p014, p65,
                                        pct_muslim, christian_total, n)
        return result

    big_city = geo_il_kodu in BIG_CITY_GEO_CODES
    il_name  = districts[0]['il_adi']

    weights = [
        district_weight(d['ilce_adi'], il_name, n, big_city)
        for d in districts
    ]
    total_w = sum(weights)

    result = {}
    allocated = 0
    for i, (d, w) in enumerate(zip(districts, weights)):
        kodu = d['ilce_kodu']
        # Kısmi bilgi: bazı ilçeler için gerçek veri var
        if kodu in KNOWN_POPULATIONS:
            pop = KNOWN_POPULATIONS[kodu]
        elif i == n - 1:
            pop = prov_pop - allocated
        else:
            pop = max(500, round(prov_pop * w / total_w))
        pop = max(500, pop)
        allocated += pop
        result[kodu] = _make_record(d, str(geo_il_kodu), pop, p014, p65,
                                    pct_muslim, christian_total, n)
    return result


def _make_record(d, geo_il_kodu_str, pop, p014, p65, pct_muslim, christian_total, n):
    """Tek ilçe için demografik kayıt üret."""
    erkek = round(pop * (0.499 + random.uniform(-0.006, 0.006)))
    kadin = pop - erkek
    y0    = round(pop * p014 / 100)
    y65   = round(pop * p65 / 100)
    y15   = pop - y0 - y65
    pct_m = pct_muslim + random.uniform(-0.4, 0.4)
    muslim    = round(pop * pct_m / 100)
    christian = max(0, round(christian_total * (pop / max(1, pop))))
    christian = min(christian, round(pop * (1 - pct_m / 100)))
    other     = max(0, pop - muslim - christian)
    return {
        'il_kodu':      geo_il_kodu_str,
        'il_adi':       d['il_adi'],
        'ilce_kodu':    d['ilce_kodu'],
        'ilce_adi':     d['ilce_adi'],
        'toplam_nufus': pop,
        'erkek_nufus':  erkek,
        'kadin_nufus':  kadin,
        'yas_0_14':     y0,
        'yas_15_64':    y15,
        'yas_65_ust':   y65,
        'muslumanlar':  muslim,
        'hiristiyanlar':christian,
        'diger_inanc':  other,
        'veri_yili':    2023,
    }


async def seed():
    with open(GEO_PATH, encoding='utf-8') as f:
        geo = json.load(f)

    by_province = defaultdict(list)
    for feat in geo['features']:
        p = feat['properties']
        geo_il = int(p.get('il_kodu', 0))
        by_province[geo_il].append({
            'il_adi':    p.get('il_adi') or p.get('NAME_1', ''),
            'ilce_adi':  p.get('ilce_adi') or p.get('NAME_2', ''),
            'ilce_kodu': p.get('ilce_kodu', ''),
        })

    print(f"GeoJSON: {len(by_province)} il, toplam {sum(len(v) for v in by_province.values())} ilçe")

    all_records = {}
    for geo_il, districts in sorted(by_province.items()):
        records = distribute_population(districts, geo_il)
        all_records.update(records)

    print(f"Üretilen kayıt: {len(all_records)}")

    db_path = get_db()
    async with aiosqlite.connect(db_path) as db:
        await db.execute("DELETE FROM demographics_district")
        count = 0
        for rec in all_records.values():
            await db.execute(
                """INSERT INTO demographics_district
                   (il_kodu, il_adi, ilce_kodu, ilce_adi, toplam_nufus,
                    erkek_nufus, kadin_nufus, yas_0_14, yas_15_64, yas_65_ust,
                    muslumanlar, hiristiyanlar, diger_inanc, veri_yili)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (rec['il_kodu'], rec['il_adi'], rec['ilce_kodu'], rec['ilce_adi'],
                 rec['toplam_nufus'], rec['erkek_nufus'], rec['kadin_nufus'],
                 rec['yas_0_14'], rec['yas_15_64'], rec['yas_65_ust'],
                 rec['muslumanlar'], rec['hiristiyanlar'], rec['diger_inanc'],
                 rec['veri_yili'])
            )
            count += 1
        await db.commit()
        print(f"✓ {count} ilçe kaydedildi.")

        # Bütünlük kontrolü
        cur = await db.execute(
            "SELECT COUNT(*) FROM demographics_district "
            "WHERE toplam_nufus != erkek_nufus + kadin_nufus "
            "   OR toplam_nufus != yas_0_14 + yas_15_64 + yas_65_ust"
        )
        bad = (await cur.fetchone())[0]
        print(f"Tutarsız kayıt: {bad}")

        # Ana şehirler kontrol
        checks = [('40', 'İstanbul', 15655924), ('7', 'Ankara', 5782285), ('41', 'İzmir', 4394694)]
        print("\nBüyük şehir toplamları:")
        for il_kodu, il_adi, expected in checks:
            cur = await db.execute(
                "SELECT COUNT(*), SUM(toplam_nufus) FROM demographics_district WHERE il_kodu=?",
                (il_kodu,)
            )
            r = await cur.fetchone()
            match = "✓" if abs(r[1] - expected) < 1000 else f"✗ beklenen:{expected:,}"
            print(f"  {il_adi} ({il_kodu}): {r[0]} ilçe, {r[1]:,} nüfus {match}")

        # İstanbul en büyük ilçeler
        cur = await db.execute(
            "SELECT ilce_adi, toplam_nufus FROM demographics_district "
            "WHERE il_kodu='40' ORDER BY toplam_nufus DESC LIMIT 5"
        )
        print("\nİstanbul en büyük 5 ilçe:")
        for r in await cur.fetchall():
            print(f"  {r[0]}: {r[1]:,}")

        # Ankara büyük ilçeler
        cur = await db.execute(
            "SELECT ilce_adi, toplam_nufus FROM demographics_district "
            "WHERE il_kodu='7' ORDER BY toplam_nufus DESC LIMIT 5"
        )
        print("\nAnkara en büyük 5 ilçe:")
        for r in await cur.fetchall():
            print(f"  {r[0]}: {r[1]:,}")


if __name__ == "__main__":
    asyncio.run(seed())
