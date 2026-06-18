from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from services.db_service import get_db
import aiosqlite

router = APIRouter()

VALID_REGION_TYPES = {"country", "region", "subregion", "il", "ilce"}


def normalize_region_type(region_type: str | None) -> str:
    value = (region_type or "region").strip()
    if value == "il":
        return "region"
    if value == "ilce":
        return "subregion"
    return value if value in VALID_REGION_TYPES else "region"


class GroupCreate(BaseModel):
    name: str
    color: str
    region_codes: List[str] = []
    region_type: str = "region"


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None


class RegionAdd(BaseModel):
    region_type: str
    region_code: str
    region_name: str


@router.get("")
async def list_groups():
    """Tüm grupları listele."""
    async with aiosqlite.connect(get_db()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM groups ORDER BY created_at DESC")
        groups = [dict(r) for r in await cursor.fetchall()]
        for g in groups:
            cursor2 = await db.execute(
                "SELECT * FROM group_regions WHERE group_id = ?", (g["id"],)
            )
            g["regions"] = [dict(r) for r in await cursor2.fetchall()]
        return groups


@router.post("")
async def create_group(data: GroupCreate):
    """Yeni grup oluştur."""
    region_type = normalize_region_type(data.region_type)
    async with aiosqlite.connect(get_db()) as db:
        cursor = await db.execute(
            "INSERT INTO groups (name, color, region_type) VALUES (?, ?, ?)",
            (data.name, data.color, region_type)
        )
        group_id = cursor.lastrowid
        await db.commit()
    return {"id": group_id, "name": data.name, "color": data.color,
            "region_type": region_type, "regions": []}


@router.get("/{group_id}")
async def get_group(group_id: int):
    """Grup detayı + toplam nüfus hesabı."""
    async with aiosqlite.connect(get_db()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM groups WHERE id = ?", (group_id,))
        group = await cursor.fetchone()
        if not group:
            raise HTTPException(status_code=404, detail="Grup bulunamadı.")
        group = dict(group)

        cursor2 = await db.execute(
            "SELECT * FROM group_regions WHERE group_id = ?", (group_id,)
        )
        regions = [dict(r) for r in await cursor2.fetchall()]
        group["regions"] = regions

        codes = [r["region_code"] for r in regions if r.get("region_code")]
        population_total = 0.0
        density_values = []
        median_age_values = []
        stat_years = {}

        if codes:
            placeholders = ",".join("?" for _ in codes)
            cursor3 = await db.execute(
                f"""
                SELECT s.code, s.indicator, s.year, s.value
                FROM region_stats s
                JOIN (
                    SELECT code, indicator, MAX(year) AS year
                    FROM region_stats
                    WHERE code IN ({placeholders})
                    GROUP BY code, indicator
                ) latest
                  ON latest.code = s.code
                 AND latest.indicator = s.indicator
                 AND latest.year = s.year
                WHERE s.code IN ({placeholders})
                """,
                [*codes, *codes],
            )
            for row in await cursor3.fetchall():
                indicator = row["indicator"]
                value = row["value"]
                if value is None:
                    continue
                stat_years[indicator] = max(stat_years.get(indicator, row["year"]), row["year"])
                if indicator == "population":
                    population_total += float(value)
                elif indicator == "density":
                    density_values.append(float(value))
                elif indicator == "median_age":
                    median_age_values.append(float(value))

        group["total_population"] = int(population_total) if population_total else 0
        group["avg_density"] = sum(density_values) / len(density_values) if density_values else None
        group["avg_median_age"] = sum(median_age_values) / len(median_age_values) if median_age_values else None
        group["stats_years"] = stat_years
        group["stats_source"] = "region_stats"
        # Eski frontend alanlarıyla geriye uyum.
        group["total_erkek"] = 0
        group["total_kadin"] = 0
        group["total_yas_0_14"] = 0
        group["total_yas_15_64"] = 0
        group["total_yas_65_ust"] = 0
        group["total_muslumanlar"] = 0
        group["total_hiristiyanlar"] = 0
        group["total_diger_inanc"] = 0
        return group


@router.put("/{group_id}")
async def update_group(group_id: int, data: GroupUpdate):
    """Grubu güncelle."""
    async with aiosqlite.connect(get_db()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM groups WHERE id = ?", (group_id,))
        group = await cursor.fetchone()
        if not group:
            raise HTTPException(status_code=404, detail="Grup bulunamadı.")
        group = dict(group)

        new_name = data.name if data.name is not None else group["name"]
        new_color = data.color if data.color is not None else group["color"]
        await db.execute(
            "UPDATE groups SET name = ?, color = ? WHERE id = ?",
            (new_name, new_color, group_id)
        )
        await db.commit()
    return {"id": group_id, "name": new_name, "color": new_color}


@router.delete("/{group_id}")
async def delete_group(group_id: int):
    """Grubu ve bölgelerini sil."""
    async with aiosqlite.connect(get_db()) as db:
        await db.execute("DELETE FROM group_regions WHERE group_id = ?", (group_id,))
        await db.execute("DELETE FROM groups WHERE id = ?", (group_id,))
        await db.commit()
    return {"message": f"Grup {group_id} silindi."}


@router.post("/{group_id}/regions")
async def add_region_to_group(group_id: int, data: RegionAdd):
    """Gruba bölge ekle."""
    async with aiosqlite.connect(get_db()) as db:
        # Grup var mı?
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT id, region_type FROM groups WHERE id = ?", (group_id,))
        group = await cursor.fetchone()
        if not group:
            raise HTTPException(status_code=404, detail="Grup bulunamadı.")
        if normalize_region_type(group["region_type"]) != normalize_region_type(data.region_type):
            raise HTTPException(status_code=400, detail="Bu grup türüne farklı seviyede bölge eklenemez.")
        # Zaten ekli mi?
        cursor2 = await db.execute(
            "SELECT id FROM group_regions WHERE group_id = ? AND region_code = ?",
            (group_id, data.region_code)
        )
        if await cursor2.fetchone():
            raise HTTPException(status_code=400, detail="Bu bölge zaten grupta mevcut.")
        await db.execute(
            "INSERT INTO group_regions (group_id, region_type, region_code, region_name) VALUES (?, ?, ?, ?)",
            (group_id, data.region_type, data.region_code, data.region_name)
        )
        await db.commit()
    return {"message": "Bölge gruba eklendi."}


@router.delete("/{group_id}/regions/{region_code}")
async def remove_region_from_group(group_id: int, region_code: str):
    """Gruptan bölge çıkar."""
    async with aiosqlite.connect(get_db()) as db:
        await db.execute(
            "DELETE FROM group_regions WHERE group_id = ? AND region_code = ?",
            (group_id, region_code)
        )
        await db.commit()
    return {"message": "Bölge gruptan çıkarıldı."}
