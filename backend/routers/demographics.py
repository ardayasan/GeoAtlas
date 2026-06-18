from fastapi import APIRouter, HTTPException, Depends
from services.db_service import get_db
import aiosqlite

router = APIRouter()


@router.get("/province/{province_code}")
async def get_province_demographics(province_code: str):
    """İl bazında demografik veriler (nüfus, yaş, inanç)."""
    async with aiosqlite.connect(get_db()) as db:
        db.row_factory = aiosqlite.Row
        # Compare as integers to handle both '1' and '01' formats
        cursor = await db.execute(
            "SELECT * FROM demographics_province WHERE CAST(il_kodu AS INTEGER) = CAST(? AS INTEGER)",
            (province_code,)
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"'{province_code}' için demografik veri bulunamadı. Excel yükleyiniz."
            )
        return dict(row)


@router.get("/province")
async def get_all_province_demographics():
    """Tüm illerin demografik verilerini döner."""
    async with aiosqlite.connect(get_db()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM demographics_province ORDER BY il_adi")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


@router.get("/district/{district_code:path}")
async def get_district_demographics(district_code: str):
    """İlçe bazında demografik veriler.
    ilce_kodu formatı: '1.1', '34.5' vb. (GeoJSON ile eşleşir).
    """
    async with aiosqlite.connect(get_db()) as db:
        db.row_factory = aiosqlite.Row
        # Exact match first (handles '1.1' format from GeoJSON)
        cursor = await db.execute(
            "SELECT * FROM demographics_district WHERE ilce_kodu = ?",
            (district_code,)
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"'{district_code}' için demografik veri bulunamadı."
            )
        return dict(row)


@router.get("/district")
async def get_all_district_demographics():
    """Tüm ilçelerin demografik verilerini döner."""
    async with aiosqlite.connect(get_db()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM demographics_district ORDER BY ilce_adi")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


@router.delete("/clear")
async def clear_demographics():
    """Tüm demografik verileri siler (yeni Excel yüklemek için)."""
    async with aiosqlite.connect(get_db()) as db:
        await db.execute("DELETE FROM demographics_province")
        await db.execute("DELETE FROM demographics_district")
        await db.commit()
    return {"message": "Demografik veriler temizlendi."}
