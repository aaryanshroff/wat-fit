import requests
from bs4 import BeautifulSoup

URL = "https://warrior.uwaterloo.ca/FacilityOccupancy"

resp = requests.get(URL)
resp.raise_for_status()

soup = BeautifulSoup(resp.text, "html.parser")

for card in soup.find_all("div", class_="occupancy-card"):
    name = card.find("h2").get_text(strip=True)
    canvas = card.find("canvas", class_="occupancy-chart")
    count = int(canvas["data-occupancy"])
    remaining = int(canvas["data-remaining"])
    max_occ = count + remaining
    pct = round(float(canvas["data-ratio"]) * 100)
    print(f"{name}: {count}/{max_occ} ({pct}%)")
