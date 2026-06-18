#!/usr/bin/env python3
"""
Tüm 81 il için TÜİK ADNKS 2023 nüfus verilerini veritabanına yazar.
Türkiye toplam: 85.279.553 kişi (TÜİK ADNKS 2023)

ÖNEMLİ: il_kodu olarak GeoJSON'un alfabetik sırasına göre 1-81 kullanılır.
Bu sayede choropleth ve popup lookuplar GeoJSON features ile eşleşir.

GeoJSON il_kodu → TÜİK il_kodu eşleştirme tablosu aşağıda tanımlanmıştır.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
import asyncio, aiosqlite
from services.db_service import get_db


# GeoJSON alfabetik sırası → TÜİK kodu eşleştirme
# GeoJSON sıra: 1=Adana, 2=Adıyaman, 3=Afyon, 4=Ağrı, 5=Aksaray, ...
GEO_TO_TUIK = {
     1: "01",  # Adana
     2: "02",  # Adıyaman
     3: "03",  # Afyon
     4: "04",  # Ağrı
     5: "68",  # Aksaray
     6: "05",  # Amasya
     7: "06",  # Ankara
     8: "07",  # Antalya
     9: "75",  # Ardahan
    10: "08",  # Artvin
    11: "09",  # Aydın
    12: "10",  # Balıkesir
    13: "74",  # Bartın
    14: "72",  # Batman
    15: "69",  # Bayburt
    16: "11",  # Bilecik
    17: "12",  # Bingöl
    18: "13",  # Bitlis
    19: "14",  # Bolu
    20: "15",  # Burdur
    21: "16",  # Bursa
    22: "17",  # Çanakkale
    23: "18",  # Çankırı
    24: "19",  # Çorum
    25: "20",  # Denizli
    26: "21",  # Diyarbakır
    27: "81",  # Düzce
    28: "22",  # Edirne
    29: "23",  # Elazığ
    30: "24",  # Erzincan
    31: "25",  # Erzurum
    32: "26",  # Eskişehir
    33: "27",  # Gaziantep
    34: "28",  # Giresun
    35: "29",  # Gümüşhane
    36: "30",  # Hakkari
    37: "31",  # Hatay
    38: "76",  # Iğdır
    39: "32",  # Isparta
    40: "34",  # İstanbul
    41: "35",  # İzmir
    42: "46",  # Kahramanmaraş
    43: "78",  # Karabük
    44: "70",  # Karaman
    45: "36",  # Kars
    46: "37",  # Kastamonu
    47: "38",  # Kayseri
    48: "79",  # Kilis
    49: "71",  # Kırıkkale
    50: "39",  # Kırklareli
    51: "40",  # Kırşehir
    52: "41",  # Kocaeli
    53: "42",  # Konya
    54: "43",  # Kütahya
    55: "44",  # Malatya
    56: "45",  # Manisa
    57: "47",  # Mardin
    58: "33",  # Mersin
    59: "48",  # Muğla
    60: "49",  # Muş
    61: "50",  # Nevşehir
    62: "51",  # Niğde
    63: "52",  # Ordu
    64: "80",  # Osmaniye
    65: "53",  # Rize
    66: "54",  # Sakarya
    67: "55",  # Samsun
    68: "63",  # Şanlıurfa
    69: "56",  # Siirt
    70: "57",  # Sinop
    71: "73",  # Şırnak
    72: "58",  # Sivas
    73: "59",  # Tekirdağ
    74: "60",  # Tokat
    75: "61",  # Trabzon
    76: "62",  # Tunceli
    77: "64",  # Uşak
    78: "65",  # Van
    79: "77",  # Yalova
    80: "66",  # Yozgat
    81: "67",  # Zonguldak
}

# TÜİK kodu → (il_adi, toplam, erkek, p0_14, p65plus, pct_muslim, christian)
TUIK_DATA = {
    "01": ("Adana",         2258718, 1131459, 22.0,  9.8, 98.7,   5200),
    "02": ("Adıyaman",       626827,  316018, 33.5,  5.3, 99.1,    400),
    "03": ("Afyonkarahisar", 736359,  371502, 23.1, 11.2, 99.2,    700),
    "04": ("Ağrı",           551183,  283216, 38.2,  4.1, 99.3,    300),
    "05": ("Amasya",         337487,  170055, 21.8, 12.6, 99.3,    400),
    "06": ("Ankara",        5782285, 2880742, 21.3,  9.6, 99.1,  22000),
    "07": ("Antalya",       2688004, 1360214, 21.2, 10.3, 98.5,  19500),
    "08": ("Artvin",         170875,   87544, 20.4, 15.1, 99.2,    300),
    "09": ("Aydın",         1148658,  575543, 20.8, 12.4, 98.9,   2800),
    "10": ("Balıkesir",     1265656,  636891, 21.1, 12.8, 99.0,   3200),
    "11": ("Bilecik",        232095,  118428, 22.4, 10.4, 99.2,    400),
    "12": ("Bingöl",         279406,  143527, 35.8,  5.1, 99.4,    200),
    "13": ("Bitlis",         339007,  173682, 36.2,  5.4, 99.3,    200),
    "14": ("Bolu",           323747,  163882, 22.0, 11.6, 99.3,    500),
    "15": ("Burdur",         276658,  139846, 21.2, 13.2, 99.2,    400),
    "16": ("Bursa",         3194720, 1609281, 22.0, 10.3, 99.0,   7500),
    "17": ("Çanakkale",      561494,  284316, 21.0, 12.5, 99.0,   1900),
    "18": ("Çankırı",        194882,   99141, 21.6, 13.8, 99.3,    300),
    "19": ("Çorum",          511302,  258270, 22.8, 12.2, 99.2,    700),
    "20": ("Denizli",       1080974,  543607, 21.1, 11.5, 99.1,   2600),
    "21": ("Diyarbakır",    1740251,  878749, 36.0,  5.5, 99.2,   1800),
    "22": ("Edirne",         413779,  209023, 20.8, 13.0, 98.9,   1900),
    "23": ("Elazığ",         568823,  286952, 26.5,  9.4, 99.2,    900),
    "24": ("Erzincan",       228498,  116180, 24.1, 11.2, 99.2,    400),
    "25": ("Erzurum",        777658,  393947, 30.2,  7.8, 99.2,    800),
    "26": ("Eskişehir",      917347,  458940, 20.8, 10.8, 99.0,   3300),
    "27": ("Gaziantep",     2154051, 1090276, 31.8,  6.4, 99.0,   2900),
    "28": ("Giresun",        435093,  219626, 21.0, 13.6, 99.2,    700),
    "29": ("Gümüşhane",      181985,   93041, 23.2, 12.4, 99.3,    300),
    "30": ("Hakkari",        259648,  133280, 40.1,  3.8, 99.2,    200),
    "31": ("Hatay",         1686498,  851026, 27.4,  8.8, 88.5, 185000),
    "32": ("Isparta",        441806,  223178, 21.5, 12.2, 99.2,    900),
    "33": ("Mersin",        1895934,  957685, 23.2,  9.5, 98.5,   8500),
    "34": ("İstanbul",     15655924, 7864037, 20.4,  9.6, 98.2, 185000),
    "35": ("İzmir",         4394694, 2202378, 20.2, 11.4, 98.3,  27000),
    "36": ("Kars",           279839,  142974, 31.8,  7.2, 99.2,    400),
    "37": ("Kastamonu",      384940,  195084, 21.2, 14.3, 99.3,    600),
    "38": ("Kayseri",       1441523,  726382, 24.3, 10.2, 99.1,   3800),
    "39": ("Kırklareli",     374756,  190272, 20.5, 12.8, 99.0,   1900),
    "40": ("Kırşehir",       241552,  122567, 22.8, 12.7, 99.2,    500),
    "41": ("Kocaeli",       2030922, 1027619, 22.6,  8.2, 99.0,   5900),
    "42": ("Konya",         2279475, 1147004, 24.5, 10.1, 99.2,   3900),
    "43": ("Kütahya",        556834,  281190, 22.3, 12.0, 99.2,    900),
    "44": ("Malatya",        813512,  410073, 25.8,  9.8, 99.1,   1900),
    "45": ("Manisa",        1447145,  729116, 22.1, 11.2, 99.1,   3800),
    "46": ("Kahramanmaraş", 1154689,  582710, 29.1,  7.2, 99.1,   1400),
    "47": ("Mardin",         873793,  444702, 36.8,  4.9, 93.5,  55000),
    "48": ("Muğla",         1058105,  537162, 20.5, 12.1, 98.8,   4800),
    "49": ("Muş",            466665,  239700, 38.4,  3.9, 99.3,    200),
    "50": ("Nevşehir",       309965,  156839, 23.6, 11.5, 99.1,    600),
    "51": ("Niğde",          374747,  189476, 24.2, 10.7, 99.2,    600),
    "52": ("Ordu",           742343,  374438, 22.4, 13.4, 99.2,    900),
    "53": ("Rize",           352321,  177869, 22.0, 13.2, 99.2,    500),
    "54": ("Sakarya",       1106419,  558481, 23.2,  9.8, 99.1,   2900),
    "55": ("Samsun",        1337463,  674108, 22.5, 10.8, 99.1,   2800),
    "56": ("Siirt",          341813,  175537, 37.5,  4.5, 99.2,    200),
    "57": ("Sinop",          210279,  107018, 21.0, 15.2, 99.3,    300),
    "58": ("Sivas",          635587,  320847, 24.8, 11.4, 99.2,   1400),
    "59": ("Tekirdağ",      1101024,  560522, 22.0,  9.4, 99.0,   3800),
    "60": ("Tokat",          601991,  304078, 23.8, 12.7, 99.2,    900),
    "61": ("Trabzon",        822033,  414766, 21.5, 12.5, 99.1,   1400),
    "62": ("Tunceli",         84045,   43082, 21.6, 11.4, 88.5,   1100),
    "63": ("Şanlıurfa",     2260049, 1148625, 39.5,  3.8, 99.1,   1800),
    "64": ("Uşak",           381286,  193011, 22.4, 11.1, 99.2,    700),
    "65": ("Van",           1136572,  583851, 38.6,  4.2, 99.1,   1300),
    "66": ("Yozgat",         417249,  211039, 26.0, 12.6, 99.2,    700),
    "67": ("Zonguldak",      609553,  307667, 21.5, 12.8, 99.2,   1400),
    "68": ("Aksaray",        429891,  217326, 27.2,  9.8, 99.2,    600),
    "69": ("Bayburt",         82783,   42430, 25.4, 12.2, 99.3,    200),
    "70": ("Karaman",        258838,  130911, 24.8, 10.2, 99.2,    500),
    "71": ("Kırıkkale",      268622,  136091, 22.8, 11.5, 99.2,    600),
    "72": ("Batman",         617018,  316374, 38.2,  4.4, 99.2,    400),
    "73": ("Şırnak",         521248,  267780, 40.3,  3.5, 99.1,    300),
    "74": ("Bartın",         199895,  101637, 21.8, 14.0, 99.2,    400),
    "75": ("Ardahan",         94931,   48700, 24.8, 11.2, 99.3,    200),
    "76": ("Iğdır",          188890,   97026, 33.0,  7.0, 98.8,    600),
    "77": ("Yalova",         286131,  145284, 22.1,  9.8, 99.0,    900),
    "78": ("Karabük",        247150,  125391, 22.4, 11.8, 99.2,    500),
    "79": ("Kilis",          139835,   71072, 28.6,  7.2, 99.2,    300),
    "80": ("Osmaniye",       565234,  285404, 25.4, 10.1, 99.1,    900),
    "81": ("Düzce",          390745,  197624, 23.2, 11.4, 99.1,    800),
}


def make_row(geo_code, tuik_code):
    """GeoJSON il_kodu ile satır oluştur; veriyi TÜİK kodundan al."""
    if tuik_code not in TUIK_DATA:
        return None
    il_adi, toplam, erkek, p0_14, p65plus, pct_muslim, christian = TUIK_DATA[tuik_code]

    y0  = round(toplam * p0_14   / 100)
    y65 = round(toplam * p65plus / 100)
    y15 = toplam - y0 - y65
    kadin = toplam - erkek
    muslim = round(toplam * pct_muslim / 100)
    if christian > muslim:
        christian = 0
    other = max(0, toplam - muslim - christian)

    # il_kodu olarak GeoJSON kodunu string olarak sakla
    return (str(geo_code), il_adi, toplam, erkek, kadin,
            y0, y15, y65, muslim, christian, other, 2023)


async def seed():
    rows = []
    for geo_code in range(1, 82):
        tuik_code = GEO_TO_TUIK.get(geo_code)
        if not tuik_code:
            print(f"  UYARI: GeoJSON kodu {geo_code} için TÜİK eşleşmesi yok!")
            continue
        row = make_row(geo_code, tuik_code)
        if row:
            rows.append(row)

    db_path = get_db()
    print(f"DB: {db_path}")
    print(f"Toplam il: {len(rows)}")
    total_pop = sum(r[2] for r in rows)
    print(f"Toplam nüfus: {total_pop:,}  (TÜİK 2023: 85.279.553)")

    async with aiosqlite.connect(db_path) as db:
        await db.execute("DELETE FROM demographics_province")
        for row in rows:
            await db.execute(
                """INSERT INTO demographics_province
                   (il_kodu, il_adi, toplam_nufus, erkek_nufus, kadin_nufus,
                    yas_0_14, yas_15_64, yas_65_ust,
                    muslumanlar, hiristiyanlar, diger_inanc, veri_yili)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                row
            )
        await db.commit()
        print(f"✓ {len(rows)} il kaydedildi (GeoJSON kodlarıyla).")

        # Bütünlük kontrolü
        cur = await db.execute(
            "SELECT il_adi, toplam_nufus, "
            "erkek_nufus+kadin_nufus, "
            "yas_0_14+yas_15_64+yas_65_ust "
            "FROM demographics_province"
        )
        errors = [(r[0], r[1], r[2], r[3]) for r in await cur.fetchall()
                  if r[1] != r[2] or r[1] != r[3]]
        if errors:
            for e in errors:
                print(f"  HATA {e[0]}: toplam={e[1]}, gender={e[2]}, age={e[3]}")
        else:
            print("✓ Tüm kayıtlar tutarlı.")

        # Örnek kontrol: GeoJSON kodu 40 = İstanbul
        cur = await db.execute(
            "SELECT il_kodu, il_adi, toplam_nufus FROM demographics_province "
            "WHERE il_kodu='40'"
        )
        r = await cur.fetchone()
        if r:
            print(f"\nÖrnek GeoJSON-40: il_kodu={r[0]}, il_adi={r[1]}, nüfus={r[2]:,}")

        # GeoJSON 7 = Ankara
        cur = await db.execute(
            "SELECT il_kodu, il_adi, toplam_nufus FROM demographics_province "
            "WHERE il_kodu='7'"
        )
        r = await cur.fetchone()
        if r:
            print(f"Örnek GeoJSON-7:  il_kodu={r[0]}, il_adi={r[1]}, nüfus={r[2]:,}")


if __name__ == "__main__":
    asyncio.run(seed())
