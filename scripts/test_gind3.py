import requests
url = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/demo_r_gind3"
params = {"time": "2023", "format": "JSON"}
response = requests.get(url, params=params)
if response.ok:
    data = response.json()
    indicators = data["dimension"]["indic_de"]["category"]["label"]
    for code, label in indicators.items():
        print(f"{code}: {label}")
else:
    print("Failed")
