from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from services.db_service import get_db
from services.excel_parser import parse_labels_sheet
import aiosqlite
import io

router = APIRouter()


class LabelCreate(BaseModel):
    name: str
    latitude: float
    longitude: float
    color: str = "#FF5733"
    description: Optional[str] = None
    icon_type: str = "pin"


@router.get("")
async def list_labels():
    """Tüm özel etiketleri listele."""
    async with aiosqlite.connect(get_db()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM custom_labels ORDER BY created_at DESC")
        return [dict(r) for r in await cursor.fetchall()]


@router.post("")
async def create_label(data: LabelCreate):
    """Yeni manuel etiket ekle."""
    async with aiosqlite.connect(get_db()) as db:
        cursor = await db.execute(
            """INSERT INTO custom_labels (name, latitude, longitude, color, description, icon_type, source)
               VALUES (?, ?, ?, ?, ?, ?, 'manuel')""",
            (data.name, data.latitude, data.longitude, data.color, data.description, data.icon_type)
        )
        label_id = cursor.lastrowid
        await db.commit()
    return {
        "id": label_id,
        "name": data.name,
        "latitude": data.latitude,
        "longitude": data.longitude,
        "color": data.color,
        "icon_type": data.icon_type,
        "source": "manuel"
    }


@router.post("/import-excel")
async def import_labels_from_excel(file: UploadFile = File(...)):
    """Excel dosyasından toplu etiket import et (Disaridan_Etiketler sheet'i)."""
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Sadece .xlsx veya .xls dosyaları kabul edilir.")
    content = await file.read()
    try:
        labels = parse_labels_sheet(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Excel parse hatası: {str(e)}")

    inserted = 0
    async with aiosqlite.connect(get_db()) as db:
        for label in labels:
            try:
                await db.execute(
                    """INSERT INTO custom_labels (name, latitude, longitude, color, description, icon_type, source)
                       VALUES (?, ?, ?, ?, ?, ?, 'excel_import')""",
                    (
                        label.get("etiket_adi", ""),
                        float(label["enlem"]),
                        float(label["boylam"]),
                        label.get("renk", "#FF5733"),
                        label.get("aciklama", ""),
                        label.get("ikon", "pin"),
                    )
                )
                inserted += 1
            except Exception:
                continue
        await db.commit()
    return {"message": f"{inserted} etiket başarıyla import edildi."}


@router.put("/{label_id}")
async def update_label(label_id: int, data: LabelCreate):
    """Etiketi güncelle."""
    async with aiosqlite.connect(get_db()) as db:
        cursor = await db.execute("SELECT id FROM custom_labels WHERE id = ?", (label_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Etiket bulunamadı.")
        await db.execute(
            """UPDATE custom_labels SET name=?, latitude=?, longitude=?, color=?, description=?, icon_type=?
               WHERE id=?""",
            (data.name, data.latitude, data.longitude, data.color, data.description, data.icon_type, label_id)
        )
        await db.commit()
    return {"message": "Etiket güncellendi."}


@router.delete("/{label_id}")
async def delete_label(label_id: int):
    """Etiketi sil."""
    async with aiosqlite.connect(get_db()) as db:
        await db.execute("DELETE FROM custom_labels WHERE id = ?", (label_id,))
        await db.commit()
    return {"message": f"Etiket {label_id} silindi."}
