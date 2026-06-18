import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "db", "app.db")


def get_db() -> str:
    return DB_PATH


async def init_db():
    """Veritabanı tablolarını oluştur (yoksa)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                color       TEXT NOT NULL,
                region_type TEXT NOT NULL DEFAULT 'il',
                created_at  DATETIME DEFAULT (datetime('now'))
            )
        """)

        # Migration: mevcut DB'lerde region_type kolonu yoksa ekle
        cursor = await db.execute("PRAGMA table_info(groups)")
        cols = [row[1] for row in await cursor.fetchall()]
        if "region_type" not in cols:
            await db.execute("ALTER TABLE groups ADD COLUMN region_type TEXT NOT NULL DEFAULT 'il'")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS group_regions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id    INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
                region_type TEXT NOT NULL,
                region_code TEXT NOT NULL,
                region_name TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS custom_labels (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                latitude    REAL NOT NULL,
                longitude   REAL NOT NULL,
                color       TEXT NOT NULL DEFAULT '#FF5733',
                description TEXT,
                icon_type   TEXT DEFAULT 'pin',
                source      TEXT DEFAULT 'manuel',
                created_at  DATETIME DEFAULT (datetime('now'))
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS regions (
                code    TEXT PRIMARY KEY,
                country TEXT NOT NULL,
                level   INTEGER NOT NULL,
                parent  TEXT,
                name_en TEXT,
                name_tr TEXT,
                source  TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS region_stats (
                code      TEXT NOT NULL,
                indicator TEXT NOT NULL,
                year      INTEGER NOT NULL,
                value     REAL,
                PRIMARY KEY (code, indicator, year),
                FOREIGN KEY (code) REFERENCES regions(code) ON DELETE CASCADE
            )
        """)

        await db.execute("CREATE INDEX IF NOT EXISTS idx_regions_country_level ON regions(country, level)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_regions_parent ON regions(parent)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_region_stats_indicator_year ON region_stats(indicator, year)")

        # Demografi: gerçek TÜİK verisi (toplam/cinsiyet + medyan yaş/yoğunluk).
        # Yaş grubu kolonları ileride resmi TÜİK Excel ile doldurulmak üzere
        # nullable bırakılmıştır. Din kolonları KALDIRILMIŞTIR (TÜİK yayımlamıyor).
        await db.execute("""
            CREATE TABLE IF NOT EXISTS demographics_province (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                il_kodu          TEXT NOT NULL UNIQUE,
                il_adi           TEXT NOT NULL,
                toplam_nufus     INTEGER DEFAULT 0,
                erkek_nufus      INTEGER DEFAULT 0,
                kadin_nufus      INTEGER DEFAULT 0,
                yas_0_14         INTEGER,
                yas_15_64        INTEGER,
                yas_65_ust       INTEGER,
                medyan_yas       REAL,
                nufus_yogunluk   REAL,
                nufus_artis_hizi REAL,
                veri_yili        INTEGER DEFAULT 2025
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS demographics_district (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                il_kodu          TEXT NOT NULL,
                il_adi           TEXT,
                ilce_kodu        TEXT NOT NULL UNIQUE,
                ilce_adi         TEXT NOT NULL,
                toplam_nufus     INTEGER DEFAULT 0,
                erkek_nufus      INTEGER DEFAULT 0,
                kadin_nufus      INTEGER DEFAULT 0,
                yas_0_14         INTEGER,
                yas_15_64        INTEGER,
                yas_65_ust       INTEGER,
                medyan_yas       REAL,
                nufus_yogunluk   REAL,
                veri_yili        INTEGER DEFAULT 2025
            )
        """)

        # Migration: eski DB'lere yeni kolonları ekle (din kolonları dokunulmaz,
        # kullanılmaz). Yeni metrik kolonları yoksa ALTER ile eklenir.
        for table, col, typ in [
            ("demographics_province", "medyan_yas", "REAL"),
            ("demographics_province", "nufus_yogunluk", "REAL"),
            ("demographics_province", "nufus_artis_hizi", "REAL"),
            ("demographics_district", "medyan_yas", "REAL"),
            ("demographics_district", "nufus_yogunluk", "REAL"),
        ]:
            cur = await db.execute(f"PRAGMA table_info({table})")
            existing = [r[1] for r in await cur.fetchall()]
            if col not in existing:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")

        await db.commit()
