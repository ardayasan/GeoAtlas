#!/usr/bin/env python3
"""
Eurostat JSON-stat göstergelerini indirip kod,value CSV'lerine yazar.

Varsayılan çıktı:
  data/demographics/eurostat_population_2023.csv
  data/demographics/eurostat_density_2023.csv
  data/demographics/eurostat_median_age_2023.csv
"""
from __future__ import annotations

import argparse
import csv
import os

import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_DIR = os.path.join(ROOT, "data", "demographics")
API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}"

INDICATORS = {
    "population": {
        "dataset": "demo_r_pjangrp3",
        "params": {"sex": "T", "age": "TOTAL"},
    },
    "population_m": {
        "dataset": "demo_r_pjangrp3",
        "params": {"sex": "M", "age": "TOTAL"},
    },
    "population_f": {
        "dataset": "demo_r_pjangrp3",
        "params": {"sex": "F", "age": "TOTAL"},
    },
    "growth_rate": {
        "dataset": "demo_r_gind3",
        "params": {"indic_de": "GROWRT"},
    },
    "density": {
        "dataset": "demo_r_d3dens",
        "params": {},
    },
    "median_age": {
        "dataset": "demo_r_pjanind3",
        "params": {"indic_de": "MEDAGEPOP"},
    },
}


def flat_index(indices: list[int], sizes: list[int]) -> int:
    value = 0
    for idx, size in zip(indices, sizes):
        value = value * size + idx
    return value


def value_at(values, idx: int):
    if isinstance(values, list):
        if idx >= len(values):
            return None
        return values[idx]
    return values.get(str(idx)) if isinstance(values, dict) else None


def parse_jsonstat(data: dict) -> dict[str, float]:
    dim_order = data.get("id") or list(data.get("dimension", {}).keys())
    sizes = data.get("size") or [
        len(data["dimension"][dim]["category"]["index"])
        for dim in dim_order
    ]
    geo_pos = dim_order.index("geo")
    geo_index = data["dimension"]["geo"]["category"]["index"]
    values = data.get("value", {})

    result = {}
    for code, geo_idx in geo_index.items():
        if len(code) < 2 or len(code) > 5:
            continue
        indices = [0] * len(dim_order)
        indices[geo_pos] = geo_idx
        idx = flat_index(indices, sizes)
        val = value_at(values, idx)
        if val is not None:
            result[code] = float(val)
    return result


def fetch_indicator(indicator: str, year: int) -> dict[str, float]:
    spec = INDICATORS[indicator]
    params = {**spec["params"], "time": str(year), "format": "JSON"}
    url = API.format(dataset=spec["dataset"])
    print(f"Eurostat indiriliyor: {indicator} {year}")
    response = requests.get(url, params=params, timeout=180)
    response.raise_for_status()
    return parse_jsonstat(response.json())


def write_csv(indicator: str, year: int, values: dict[str, float]) -> str:
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"eurostat_{indicator}_{year}.csv")
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["code", "value"])
        writer.writeheader()
        for code, value in sorted(values.items()):
            writer.writerow({"code": code, "value": value})
    print(f"✓ {path}: {len(values)} satır")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2023)
    parser.add_argument(
        "--indicator",
        choices=sorted(INDICATORS),
        action="append",
        help="Tekrarlanabilir. Verilmezse tüm göstergeler çekilir.",
    )
    args = parser.parse_args()

    indicators = args.indicator or sorted(INDICATORS)
    for indicator in indicators:
        values = fetch_indicator(indicator, args.year)
        write_csv(indicator, args.year, values)


if __name__ == "__main__":
    main()
