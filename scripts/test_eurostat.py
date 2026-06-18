import requests
import json

url = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/demo_r_gind3"
params = {"indic_de": "GROW", "time": "2023", "format": "JSON"}
response = requests.get(url, params=params)
if response.ok:
    data = response.json()
    print("Success. Value count:", len(data.get("value", {})))
else:
    print("Error:", response.status_code, response.text)

url2 = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/demo_r_pjangrp3"
params2 = {"sex": "F", "age": "TOTAL", "time": "2023", "format": "JSON"}
response2 = requests.get(url2, params2)
if response2.ok:
    data2 = response2.json()
    print("Success Female Pop. Value count:", len(data2.get("value", {})))

