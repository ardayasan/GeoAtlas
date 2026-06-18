from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
import json
import os

router = APIRouter()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "poi")
BOUNDARIES_INDEX = os.path.join(os.path.dirname(__file__), "..", "..", "data", "boundaries", "nuts", "index.json")

POI_CATEGORIES = {
    "mosques": {
        "label": "Cami / Mescid",
        "legacy_file": "mosques_turkey.geojson",
        "source": "OpenStreetMap / Overpass",
    },
    "churches": {
        "label": "Kilise / Katedral",
        "legacy_file": "churches_turkey.geojson",
        "source": "OpenStreetMap / Overpass",
    },
    "worship_other": {
        "label": "Diğer İbadethaneler",
        "legacy_file": "worship_other_turkey.geojson",
        "source": "OpenStreetMap / Overpass",
    },
    "schools": {
        "label": "İlk / Orta / Lise",
        "legacy_file": "schools_turkey.geojson",
        "source": "OpenStreetMap / Overpass",
    },
    "universities": {
        "label": "Üniversite / MYO",
        "legacy_file": "universities_turkey.geojson",
        "source": "OpenStreetMap / Overpass",
    },
    "kindergartens": {
        "label": "Anaokulu / Kreş",
        "legacy_file": "kindergartens_turkey.geojson",
        "source": "OpenStreetMap / Overpass",
    },
}


def normalize_country(country: str | None) -> str:
    return (country or "TR").strip().upper()


def supported_countries() -> dict:
    if not os.path.exists(BOUNDARIES_INDEX):
        return {"TR": {"name_tr": "Türkiye", "name_en": "Türkiye"}}
    with open(BOUNDARIES_INDEX, "r", encoding="utf-8") as f:
        return json.load(f)


def poi_file_candidates(category: str, country: str) -> list[str]:
    cfg = POI_CATEGORIES[category]
    country_lower = country.lower()
    candidates = [
        os.path.join(DATA_DIR, "europe", country, f"{category}.geojson"),
        os.path.join(DATA_DIR, f"{category}_{country_lower}.geojson"),
    ]
    if country == "TR":
        candidates.append(os.path.join(DATA_DIR, cfg["legacy_file"]))
    return candidates


def resolve_poi_file(category: str, country: str) -> str | None:
    for path in poi_file_candidates(category, country):
        if os.path.exists(path):
            return path
    return None


def load_geojson(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_poi(category: str, country: str):
    if category not in POI_CATEGORIES:
        raise HTTPException(status_code=404, detail="Geçersiz POI kategorisi.")

    country = normalize_country(country)
    path = resolve_poi_file(category, country)
    if not path:
        label = POI_CATEGORIES[category]["label"]
        raise HTTPException(
            status_code=404,
            detail=(
                f"{country} için {label} POI verisi yok. "
                "Bu kategori destekleniyor; veri dosyası henüz hazırlanmadı."
            ),
        )
    return load_geojson(path)


def category_status(category: str, country: str, include_count: bool = True) -> dict:
    path = resolve_poi_file(category, country)
    cfg = POI_CATEGORIES[category]
    if not path:
        return {
            "available": False,
            "count": 0,
            "label": cfg["label"],
            "source": cfg["source"],
            "file": None,
        }
    count = None
    if include_count:
        data = load_geojson(path)
        count = len(data.get("features", []))
    return {
        "available": True,
        "count": count,
        "label": cfg["label"],
        "source": cfg["source"],
        "file": os.path.relpath(path, DATA_DIR),
    }


@router.get("/catalog")
async def get_poi_catalog():
    """Desteklenen ülkeleri ve POI veri durumunu döner."""
    countries = supported_countries()
    result = {}
    for code, meta in sorted(countries.items()):
        country = normalize_country(code)
        result[country] = {
            "name": meta.get("name_tr") or meta.get("name_en") or country,
            "bbox": meta.get("bbox"),
            "levels": meta.get("levels", []),
            "categories": {
                key: category_status(key, country, include_count=True)
                for key in POI_CATEGORIES
            },
        }
    return {
        "source": "OpenStreetMap / Overpass",
        "categories": {key: {"label": cfg["label"]} for key, cfg in POI_CATEGORIES.items()},
        "countries": result,
    }


@router.get("/summary")
async def get_poi_summary(country: str = Query("TR", min_length=2, max_length=3)):
    """Seçili ülke için her POI kategorisinin mevcut olup olmadığını ve kayıt sayısını döner."""
    normalized = normalize_country(country)
    return {
        "country": normalized,
        "source": "OpenStreetMap / Overpass",
        "categories": {
            key: category_status(key, normalized)
            for key in POI_CATEGORIES
        },
    }


@router.get("/{category}")
async def get_poi_by_category(
    category: str,
    country: str = Query("TR", min_length=2, max_length=3),
):
    """Seçili ülke ve kategori için GeoJSON POI verisi."""
    data = load_poi(category, country)
    return JSONResponse(content=data)
