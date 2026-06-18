from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import json
import os

router = APIRouter()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "boundaries")


def load_geojson(filename: str):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail=f"{filename} bulunamadı. Lütfen önce 'scripts/download_boundaries.py' çalıştırın."
        )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/provinces")
async def get_provinces():
    """Tüm 81 il sınırını GeoJSON olarak döner."""
    data = load_geojson("turkey_provinces.geojson")
    return JSONResponse(content=data)


@router.get("/districts")
async def get_districts():
    """Tüm ilçe sınırlarını GeoJSON olarak döner."""
    data = load_geojson("turkey_districts.geojson")
    return JSONResponse(content=data)


@router.get("/districts/{province_code}")
async def get_districts_by_province(province_code: str):
    """Belirli bir ilin ilçe sınırlarını döner."""
    data = load_geojson("turkey_districts.geojson")
    features = [
        f for f in data.get("features", [])
        if str(f.get("properties", {}).get("GID_1", "")).endswith(f"_{province_code}") or
           str(f.get("properties", {}).get("province_code", "")) == province_code or
           str(f.get("properties", {}).get("il_kodu", "")) == province_code
    ]
    if not features:
        raise HTTPException(status_code=404, detail=f"'{province_code}' kodu için ilçe bulunamadı.")
    return JSONResponse(content={"type": "FeatureCollection", "features": features})


@router.get("/neighborhoods")
async def get_neighborhoods():
    """Mahalle sınırlarını döner (opsiyonel, büyük dosya)."""
    data = load_geojson("turkey_neighborhoods.geojson")
    return JSONResponse(content=data)
