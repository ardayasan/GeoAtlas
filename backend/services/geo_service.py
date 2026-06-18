import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "boundaries")


def get_province_name_by_code(code: str) -> str:
    """İl kodundan il adını döner."""
    path = os.path.join(DATA_DIR, "turkey_provinces.geojson")
    if not os.path.exists(path):
        return code
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        if str(props.get("il_kodu", "")) == str(code) or \
           str(props.get("GID_1", "")).split(".")[-1] == str(code):
            return props.get("NAME_1", props.get("il_adi", code))
    return code


def simplify_geojson(geojson: dict, tolerance: float = 0.01) -> dict:
    """
    GeoJSON geometrisini basit bir yaklaşımla sadeleştirir.
    Büyük dosyalar için mapshaper veya shapely kullanılabilir.
    """
    try:
        from shapely.geometry import shape, mapping
        from shapely.ops import unary_union
        features = []
        for feature in geojson.get("features", []):
            geom = shape(feature["geometry"])
            simplified = geom.simplify(tolerance, preserve_topology=True)
            feature["geometry"] = mapping(simplified)
            features.append(feature)
        geojson["features"] = features
    except ImportError:
        pass  # shapely yoksa orijinali döndür
    return geojson
