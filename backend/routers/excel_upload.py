from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from services.excel_parser import (
    parse_province_sheet, parse_district_sheet,
    parse_region_stats_sheet, parse_labels_sheet,
)
from services.db_service import get_db
import aiosqlite
import io
import os
import sys

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", "..",
                             "data", "excel", "template_nufus.xlsx")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
from tr_util import NAME_TO_CODE, norm  # noqa: E402
from fetch_tuik import build_district_index, match_district  # noqa: E402

router = APIRouter()


@router.get("/template")
async def download_template():
    if not os.path.exists(TEMPLATE_PATH):
        raise HTTPException(status_code=404, detail="Şablon bulunamadı.")
    return FileResponse(
        TEMPLATE_PATH, filename="geoatlas_sablonu.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _i(v):
    v = (str(v).strip() if v is not None else "")
    if v in ("", "None"):
        return None
    try:
        return int(float(v.replace(".", "").replace(",", ".") if v.count(".") > 1 else v.replace(",", ".")))
    except ValueError:
        return None


def _f(v):
    v = (str(v).strip() if v is not None else "")
    if v in ("", "None"):
        return None
    try:
        return float(v.replace(",", "."))
    except ValueError:
        return None


def _resolve_il(rec):
    code = (rec.get("il_kodu") or "").strip()
    if code.isdigit():
        return str(int(code))
    return None if not rec.get("il_adi") else (
        str(NAME_TO_CODE[norm(rec["il_adi"])]) if norm(rec["il_adi"]) in NAME_TO_CODE else None
    )


@router.post("/upload")
async def upload_excel(
    file: UploadFile = File(...),
    scope: str = Query("turkey", regex="^(turkey|europe|labels)$"),
):
    """Excel dosyasını yükle. scope: turkey | europe | labels"""
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Sadece .xlsx veya .xls dosyaları kabul edilir.")

    content = await file.read()
    buf = io.BytesIO(content)

    if scope == "europe":
        return await _upload_europe(buf)
    if scope == "labels":
        return await _upload_labels(buf)
    return await _upload_turkey(buf)


# ── Türkiye ──────────────────────────────────────────────────────────────────

async def _upload_turkey(buf: io.BytesIO):
    result = {"provinces": 0, "districts": 0, "unmatched": [], "errors": []}

    try:
        provinces = parse_province_sheet(buf)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"'Nufus_Il' sheet parse hatası: {str(e)}")

    buf.seek(0)
    try:
        districts = parse_district_sheet(buf)
    except Exception as e:
        districts = []
        result["errors"].append(f"'Nufus_Ilce' sheet okunamadı: {str(e)}")

    dist_idx, dist_central = build_district_index()

    async with aiosqlite.connect(get_db()) as db:
        for p in provinces:
            il_kodu = _resolve_il(p)
            if not il_kodu:
                result["unmatched"].append(f"İl: {p.get('il_adi', '?')}")
                continue
            try:
                await db.execute("""
                    INSERT INTO demographics_province
                      (il_kodu, il_adi, toplam_nufus, erkek_nufus, kadin_nufus,
                       yas_0_14, yas_15_64, yas_65_ust,
                       medyan_yas, nufus_yogunluk, nufus_artis_hizi, veri_yili)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(il_kodu) DO UPDATE SET
                       il_adi=excluded.il_adi, toplam_nufus=excluded.toplam_nufus,
                       erkek_nufus=excluded.erkek_nufus, kadin_nufus=excluded.kadin_nufus,
                       yas_0_14=excluded.yas_0_14, yas_15_64=excluded.yas_15_64,
                       yas_65_ust=excluded.yas_65_ust, medyan_yas=excluded.medyan_yas,
                       nufus_yogunluk=excluded.nufus_yogunluk,
                       nufus_artis_hizi=excluded.nufus_artis_hizi, veri_yili=excluded.veri_yili
                """, (
                    il_kodu, p.get("il_adi", ""), _i(p.get("toplam_nufus")),
                    _i(p.get("erkek_nufus")), _i(p.get("kadin_nufus")),
                    _i(p.get("yas_0_14")), _i(p.get("yas_15_64")), _i(p.get("yas_65_ust")),
                    _f(p.get("medyan_yas")), _f(p.get("nufus_yogunluk")),
                    _f(p.get("nufus_artis_hizi")), _i(p.get("veri_yili")) or 2025,
                ))
                result["provinces"] += 1
            except Exception as e:
                result["errors"].append(f"İl {p.get('il_adi', '?')}: {str(e)}")

        for d in districts:
            il_kodu = _resolve_il(d)
            if not il_kodu:
                result["unmatched"].append(f"İlçe (il bulunamadı): {d.get('il_adi','?')}/{d.get('ilce_adi','?')}")
                continue
            ilce_kodu = (d.get("ilce_kodu") or "").strip()
            if not ilce_kodu:
                hit = match_district(int(il_kodu), d.get("ilce_adi", ""), dist_idx, dist_central)
                if not hit:
                    result["unmatched"].append(f"İlçe: {d.get('il_adi','?')}/{d.get('ilce_adi','?')}")
                    continue
                ilce_kodu, ilce_adi = hit
            else:
                ilce_adi = d.get("ilce_adi", "")
            try:
                await db.execute("""
                    INSERT INTO demographics_district
                      (il_kodu, il_adi, ilce_kodu, ilce_adi, toplam_nufus,
                       erkek_nufus, kadin_nufus, yas_0_14, yas_15_64, yas_65_ust,
                       medyan_yas, nufus_yogunluk, veri_yili)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(ilce_kodu) DO UPDATE SET
                       il_kodu=excluded.il_kodu, il_adi=excluded.il_adi,
                       ilce_adi=excluded.ilce_adi, toplam_nufus=excluded.toplam_nufus,
                       erkek_nufus=excluded.erkek_nufus, kadin_nufus=excluded.kadin_nufus,
                       yas_0_14=excluded.yas_0_14, yas_15_64=excluded.yas_15_64,
                       yas_65_ust=excluded.yas_65_ust, medyan_yas=excluded.medyan_yas,
                       nufus_yogunluk=excluded.nufus_yogunluk, veri_yili=excluded.veri_yili
                """, (
                    il_kodu, d.get("il_adi", ""), ilce_kodu, ilce_adi,
                    _i(d.get("toplam_nufus")), _i(d.get("erkek_nufus")), _i(d.get("kadin_nufus")),
                    _i(d.get("yas_0_14")), _i(d.get("yas_15_64")), _i(d.get("yas_65_ust")),
                    _f(d.get("medyan_yas")), _f(d.get("nufus_yogunluk")),
                    _i(d.get("veri_yili")) or 2025,
                ))
                result["districts"] += 1
            except Exception as e:
                result["errors"].append(f"İlçe {d.get('ilce_adi','?')}: {str(e)}")

        await db.commit()

    return {
        "scope": "turkey",
        "provinces_imported": result["provinces"],
        "districts_imported": result["districts"],
        "unmatched": result["unmatched"][:50],
        "errors": result["errors"][:20],
    }


# ── Avrupa ───────────────────────────────────────────────────────────────────

async def _upload_europe(buf: io.BytesIO):
    try:
        records = parse_region_stats_sheet(buf)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"'Region_Stats' sheet parse hatası: {str(e)}")

    imported = 0
    errors = []

    async with aiosqlite.connect(get_db()) as db:
        for r in records:
            try:
                await db.execute("""
                    INSERT INTO region_stats (code, indicator, year, value)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(code, indicator, year) DO UPDATE SET value=excluded.value
                """, (r["code"], r["indicator"], r["year"], r["value"]))
                imported += 1
            except Exception as e:
                errors.append(f"{r['code']}/{r['indicator']}: {str(e)}")
        await db.commit()

    unique_codes = len({r["code"] for r in records})
    return {
        "scope": "europe",
        "regions_imported": unique_codes,
        "stats_imported": imported,
        "errors": errors[:20],
    }


# ── Etiketler ────────────────────────────────────────────────────────────────

async def _upload_labels(buf: io.BytesIO):
    try:
        records = parse_labels_sheet(buf)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"'Disaridan_Etiketler' sheet parse hatası: {str(e)}")

    imported = 0
    errors = []

    async with aiosqlite.connect(get_db()) as db:
        for r in records:
            try:
                await db.execute("""
                    INSERT INTO custom_labels (name, latitude, longitude, color, description, icon_type, source)
                    VALUES (?, ?, ?, ?, ?, ?, 'excel')
                """, (
                    r.get("etiket_adi", "Etiket"),
                    float(r["enlem"]), float(r["boylam"]),
                    r.get("renk", "#FF5733"),
                    r.get("aciklama"),
                    r.get("ikon", "pin"),
                ))
                imported += 1
            except Exception as e:
                errors.append(f"{r.get('etiket_adi','?')}: {str(e)}")
        await db.commit()

    return {
        "scope": "labels",
        "labels_imported": imported,
        "errors": errors[:20],
    }
