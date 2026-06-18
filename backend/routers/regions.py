from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from services.db_service import get_db
import aiosqlite
import json
import os

router = APIRouter()

BOUNDARY_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "boundaries", "nuts")
)
INDEX_PATH = os.path.join(BOUNDARY_DIR, "index.json")


def _parse_countries(countries: str | None) -> list[str]:
    if not countries:
        return []
    return [c.strip().upper() for c in countries.split(",") if c.strip()]


def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _empty_feature_collection() -> dict:
    return {"type": "FeatureCollection", "features": []}


def _known_countries() -> list[str]:
    if not os.path.exists(INDEX_PATH):
        return []
    index = _load_json(INDEX_PATH)
    return sorted(index.keys())


def _filter_features(features: list[dict], parent: str | None = None) -> list[dict]:
    if not parent:
        return features
    parent = parent.upper()
    return [
        f for f in features
        if str((f.get("properties") or {}).get("parent", "")).upper() == parent
    ]


@router.get("/index")
async def get_regions_index():
    """Ülke bbox/seviye indeksini döndürür."""
    if not os.path.exists(INDEX_PATH):
        return {}
    return JSONResponse(content=_load_json(INDEX_PATH))


@router.get("/boundaries")
async def get_region_boundaries(
    level: int = Query(..., ge=0, le=4),
    countries: str | None = Query(None),
    parent: str | None = Query(None),
):
    """İstenen seviye ve ülkeler için birleşik GeoJSON döndürür."""
    requested = _parse_countries(countries)
    features = []

    if level == 0:
        path = os.path.join(BOUNDARY_DIR, "L0", "ALL.geojson")
        if not os.path.exists(path):
            return _empty_feature_collection()
        data = _load_json(path)
        if requested:
            requested_set = set(requested)
            features = [
                f for f in data.get("features", [])
                if (f.get("properties") or {}).get("country") in requested_set
                or (f.get("properties") or {}).get("code") in requested_set
            ]
        else:
            features = data.get("features", [])
        return JSONResponse(content={"type": "FeatureCollection", "features": _filter_features(features, parent)})

    country_list = requested or _known_countries()
    for country in country_list:
        if country == "TR" and level > 0:
            continue
        path = os.path.join(BOUNDARY_DIR, f"L{level}", f"{country}.geojson")
        if not os.path.exists(path):
            continue
        data = _load_json(path)
        features.extend(_filter_features(data.get("features", []), parent))

    return JSONResponse(content={"type": "FeatureCollection", "features": features})


@router.get("/list")
async def list_regions(
    level: int = Query(..., ge=0, le=4),
    country: str | None = None,
    parent: str | None = None,
):
    """Select kontrolü için hafif bölge listesi döndürür."""
    clauses = ["level = ?"]
    params: list = [level]
    if country:
        clauses.append("country = ?")
        params.append(country.upper())
    if parent:
        clauses.append("parent = ?")
        params.append(parent.upper())

    async with aiosqlite.connect(get_db()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            f"""
            SELECT code, country, level, parent, name_en, name_tr, source
            FROM regions
            WHERE {' AND '.join(clauses)}
            ORDER BY COALESCE(name_tr, name_en, code)
            """,
            params,
        )
        return [dict(r) for r in await cursor.fetchall()]


@router.get("/stats")
async def get_region_stats(
    indicator: str,
    level: int = Query(..., ge=0, le=4),
    year: int | None = None,
    countries: str | None = None,
    parent: str | None = None,
):
    """Bölge kodu → gösterge değeri sözlüğü döndürür."""
    country_list = _parse_countries(countries)
    params: list = [indicator, level]
    country_sql = ""
    if country_list:
        placeholders = ",".join("?" for _ in country_list)
        country_sql = f" AND r.country IN ({placeholders})"
        params.extend(country_list)
    parent_sql = ""
    if parent:
        parent_sql = " AND r.parent = ?"
        params.append(parent.upper())

    async with aiosqlite.connect(get_db()) as db:
        if year is not None:
            cursor = await db.execute(
                f"""
                SELECT s.code, s.value
                FROM region_stats s
                JOIN regions r ON r.code = s.code
                WHERE s.indicator = ? AND r.level = ?{country_sql}{parent_sql} AND s.year = ?
                """,
                [*params, year],
            )
        else:
            cursor = await db.execute(
                f"""
                SELECT s.code, s.value
                FROM region_stats s
                JOIN regions r ON r.code = s.code
                JOIN (
                    SELECT code, indicator, MAX(year) AS year
                    FROM region_stats
                    WHERE indicator = ?
                    GROUP BY code, indicator
                ) latest
                  ON latest.code = s.code
                 AND latest.indicator = s.indicator
                 AND latest.year = s.year
                WHERE s.indicator = ? AND r.level = ?{country_sql}{parent_sql}
                """,
                [indicator, *params],
            )
        rows = await cursor.fetchall()
    return {code: value for code, value in rows}


@router.get("/{code}")
async def get_region_detail(code: str):
    """Bölge metadatası, üst bölgesi ve mevcut tüm göstergeleri."""
    normalized = code.upper()
    async with aiosqlite.connect(get_db()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM regions WHERE code = ?", (normalized,))
        region = await cursor.fetchone()
        if not region:
            raise HTTPException(status_code=404, detail=f"'{code}' için bölge bulunamadı.")

        region_dict = dict(region)
        parent = None
        if region_dict.get("parent"):
            cursor = await db.execute("SELECT * FROM regions WHERE code = ?", (region_dict["parent"],))
            parent_row = await cursor.fetchone()
            parent = dict(parent_row) if parent_row else None

        cursor = await db.execute(
            """
            SELECT rs.indicator, rs.year, rs.value
            FROM region_stats rs
            JOIN (
                SELECT indicator, MAX(year) AS year
                FROM region_stats
                WHERE code = ?
                GROUP BY indicator
            ) latest
              ON latest.indicator = rs.indicator
             AND latest.year = rs.year
            WHERE rs.code = ?
            ORDER BY rs.indicator
            """,
            (normalized, normalized),
        )
        stats = {
            r["indicator"]: {"year": r["year"], "value": r["value"]}
            for r in await cursor.fetchall()
        }

    return {"region": region_dict, "parent": parent, "stats": stats}
