#!/usr/bin/env python3
"""
Türkiye il/ilçe verisi için ortak yardımcılar:
  - IL_KODU_AD: il_kodu (1..81) → il adı (standart Türkçe alfabetik sıra).
    Demografi ve sınır verisi BU kodları kullanır; sıralama korunmalıdır.
  - norm():      Türkçe-duyarlı normalize (büyük/küçük İ/I dahil) — isim eşleme.
  - tr_sortkey(): Türkçe alfabetik sıralama anahtarı.
  - il_slug():   İl adından ASCII slug (ör. 'Şanlıurfa' → 'sanliurfa').
"""
import unicodedata

IL_KODU_AD = {
    1: 'Adana', 2: 'Adıyaman', 3: 'Afyonkarahisar', 4: 'Ağrı', 5: 'Aksaray',
    6: 'Amasya', 7: 'Ankara', 8: 'Antalya', 9: 'Ardahan', 10: 'Artvin',
    11: 'Aydın', 12: 'Balıkesir', 13: 'Bartın', 14: 'Batman', 15: 'Bayburt',
    16: 'Bilecik', 17: 'Bingöl', 18: 'Bitlis', 19: 'Bolu', 20: 'Burdur',
    21: 'Bursa', 22: 'Çanakkale', 23: 'Çankırı', 24: 'Çorum', 25: 'Denizli',
    26: 'Diyarbakır', 27: 'Düzce', 28: 'Edirne', 29: 'Elazığ', 30: 'Erzincan',
    31: 'Erzurum', 32: 'Eskişehir', 33: 'Gaziantep', 34: 'Giresun', 35: 'Gümüşhane',
    36: 'Hakkari', 37: 'Hatay', 38: 'Iğdır', 39: 'Isparta', 40: 'İstanbul',
    41: 'İzmir', 42: 'Kahramanmaraş', 43: 'Karabük', 44: 'Karaman', 45: 'Kars',
    46: 'Kastamonu', 47: 'Kayseri', 48: 'Kilis', 49: 'Kırıkkale', 50: 'Kırklareli',
    51: 'Kırşehir', 52: 'Kocaeli', 53: 'Konya', 54: 'Kütahya', 55: 'Malatya',
    56: 'Manisa', 57: 'Mardin', 58: 'Mersin', 59: 'Muğla', 60: 'Muş',
    61: 'Nevşehir', 62: 'Niğde', 63: 'Ordu', 64: 'Osmaniye', 65: 'Rize',
    66: 'Sakarya', 67: 'Samsun', 68: 'Şanlıurfa', 69: 'Siirt', 70: 'Sinop',
    71: 'Şırnak', 72: 'Sivas', 73: 'Tekirdağ', 74: 'Tokat', 75: 'Trabzon',
    76: 'Tunceli', 77: 'Uşak', 78: 'Van', 79: 'Yalova', 80: 'Yozgat',
    81: 'Zonguldak',
}

# İl adı (normalize) → il_kodu  (isim eşleme için)
def _build_name_index():
    return {norm(v): k for k, v in IL_KODU_AD.items()}

# Büyük harf Türkçe karakterleri doğru küçült (Python .lower() İ/I'yı bozar)
_UPPER_TR = {'İ': 'i', 'I': 'ı', 'Ş': 'ş', 'Ğ': 'ğ', 'Ü': 'ü', 'Ö': 'ö', 'Ç': 'ç'}
_FOLD = {'ı': 'i', 'i': 'i', 'ş': 's', 'ğ': 'g', 'ü': 'u', 'ö': 'o', 'ç': 'c', 'â': 'a', 'î': 'i'}
_TR_ORDER = "abcçdefgğhıijklmnoöprsştuüvyz"


def norm(s: str) -> str:
    """Türkçe-duyarlı normalize: 'AFYONKARAHİSAR', 'Afyonkarahisar', 'afyon ili'
    → 'afyonkarahisar' benzeri ASCII karşılaştırma anahtarı üretir."""
    s = (s or '').strip()
    # önce büyük Türkçe harfleri doğru küçük forma çevir
    s = ''.join(_UPPER_TR.get(c, c) for c in s).lower()
    # il/ilçe son ekleri
    for suf in (' ili', ' i̇li', ' merkez ilçesi', ' ilçesi'):
        if s.endswith(suf):
            s = s[:-len(suf)]
    # ASCII'ye katla
    s = ''.join(_FOLD.get(c, c) for c in s)
    # kalan birleşik işaretleri (combining dot vb.) at
    s = ''.join(c for c in unicodedata.normalize('NFD', s)
                if unicodedata.category(c) != 'Mn')
    return s.strip()


def tr_sortkey(s: str):
    s = (s or '').lower()
    return [_TR_ORDER.index(c) if c in _TR_ORDER else 99 for c in s]


def il_slug(name: str) -> str:
    """İl adından nufusu.com tarzı ASCII slug: 'Şanlıurfa' → 'sanliurfa'."""
    s = norm(name)
    return ''.join(c if c.isalnum() else '-' for c in s).strip('-')


NAME_TO_CODE = _build_name_index()

# Eurostat/GISCO 2024 NUTS3 kodları. Türkiye'de NUTS3 = il düzeyi.
# Bu tablo GISCO NUTS_RG_01M_2024_4326_LEVL_3.geojson içindeki TR feature'ları
# NAME_LATN ile IL_KODU_AD normalizasyonu üzerinden üretilmiştir.
IL_KODU_TO_NUTS3 = {
    1: "TR621",  # Adana
    2: "TRC12",  # Adıyaman
    3: "TR332",  # Afyonkarahisar
    4: "TRA21",  # Ağrı
    5: "TR712",  # Aksaray
    6: "TR834",  # Amasya
    7: "TR510",  # Ankara
    8: "TR611",  # Antalya
    9: "TRA24",  # Ardahan
    10: "TR905",  # Artvin
    11: "TR321",  # Aydın
    12: "TR221",  # Balıkesir
    13: "TR813",  # Bartın
    14: "TRC32",  # Batman
    15: "TRA13",  # Bayburt
    16: "TR413",  # Bilecik
    17: "TRB13",  # Bingöl
    18: "TRB23",  # Bitlis
    19: "TR424",  # Bolu
    20: "TR613",  # Burdur
    21: "TR411",  # Bursa
    22: "TR222",  # Çanakkale
    23: "TR822",  # Çankırı
    24: "TR833",  # Çorum
    25: "TR322",  # Denizli
    26: "TRC22",  # Diyarbakır
    27: "TR423",  # Düzce
    28: "TR212",  # Edirne
    29: "TRB12",  # Elazığ
    30: "TRA12",  # Erzincan
    31: "TRA11",  # Erzurum
    32: "TR412",  # Eskişehir
    33: "TRC11",  # Gaziantep
    34: "TR903",  # Giresun
    35: "TR906",  # Gümüşhane
    36: "TRB24",  # Hakkari
    37: "TR631",  # Hatay
    38: "TRA23",  # Iğdır
    39: "TR612",  # Isparta
    40: "TR100",  # İstanbul
    41: "TR310",  # İzmir
    42: "TR632",  # Kahramanmaraş
    43: "TR812",  # Karabük
    44: "TR522",  # Karaman
    45: "TRA22",  # Kars
    46: "TR821",  # Kastamonu
    47: "TR721",  # Kayseri
    48: "TRC13",  # Kilis
    49: "TR711",  # Kırıkkale
    50: "TR213",  # Kırklareli
    51: "TR715",  # Kırşehir
    52: "TR421",  # Kocaeli
    53: "TR521",  # Konya
    54: "TR333",  # Kütahya
    55: "TRB11",  # Malatya
    56: "TR331",  # Manisa
    57: "TRC31",  # Mardin
    58: "TR622",  # Mersin
    59: "TR323",  # Muğla
    60: "TRB22",  # Muş
    61: "TR714",  # Nevşehir
    62: "TR713",  # Niğde
    63: "TR902",  # Ordu
    64: "TR633",  # Osmaniye
    65: "TR904",  # Rize
    66: "TR422",  # Sakarya
    67: "TR831",  # Samsun
    68: "TRC21",  # Şanlıurfa
    69: "TRC34",  # Siirt
    70: "TR823",  # Sinop
    71: "TRC33",  # Şırnak
    72: "TR722",  # Sivas
    73: "TR211",  # Tekirdağ
    74: "TR832",  # Tokat
    75: "TR901",  # Trabzon
    76: "TRB14",  # Tunceli
    77: "TR334",  # Uşak
    78: "TRB21",  # Van
    79: "TR425",  # Yalova
    80: "TR723",  # Yozgat
    81: "TR811",  # Zonguldak
}

NUTS3_TO_IL_KODU = {v: k for k, v in IL_KODU_TO_NUTS3.items()}


def il_nuts_code(il_kodu) -> str | None:
    """İl kodunu (1..81) Türkiye NUTS3 koduna çevirir."""
    try:
        return IL_KODU_TO_NUTS3.get(int(str(il_kodu).strip()))
    except (TypeError, ValueError):
        return None


def ilce_lau_code(ilce_kodu, il_kodu=None) -> str | None:
    """Mevcut '34.5' tarzı ilçe kodunu TR'ye özel LAU koduna çevirir.

    Format: '{NUTS3}.{il içi sıra}' (ör. 'TR100.1').
    """
    raw = str(ilce_kodu or "").strip()
    province_part = str(il_kodu or "").strip()
    local_part = raw
    if "." in raw:
        province_part, local_part = raw.split(".", 1)
    nuts3 = il_nuts_code(province_part)
    if not nuts3:
        return None
    local_part = "".join(c for c in local_part if c.isalnum() or c in ("-", "_"))
    return f"{nuts3}.{local_part}" if local_part else None
