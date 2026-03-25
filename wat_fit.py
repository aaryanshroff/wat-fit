import csv
import json
import os
import smtplib
from collections import defaultdict
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).parent
URL = "https://warrior.uwaterloo.ca/FacilityOccupancy"
CSV_PATH = BASE_DIR / "data.csv"

with open(BASE_DIR / "config.json") as f:
    config = json.load(f)
tracked = config["track_facilities"]

SHORT_NAMES = {
    "CIF Fitness Centre": "CIF",
    "PAC - 1st Floor - Free Weights": "PAC Free Wt",
    "PAC - 1st Floor - Functional": "PAC Func",
    "PAC - 2nd Floor - Cardio": "PAC Cardio",
    "PAC - 2nd Floor - Weight Machines": "PAC Wt Mach",
    "Warrior Zone": "Warrior",
}

resp = requests.get(URL)
resp.raise_for_status()
soup = BeautifulSoup(resp.text, "html.parser")

# Scrape current data
facilities = []
for card in soup.find_all("div", class_="occupancy-card"):
    name = card.find("h2").get_text(strip=True)
    canvas = card.find("canvas", class_="occupancy-chart")
    pct = round(float(canvas["data-ratio"]) * 100)
    facilities.append((name, pct))

# Append to CSV
now = datetime.now()
now_str = now.strftime("%Y-%m-%d %H:%M")
header = ["time"] + [name for name, _ in facilities]
row = [now_str] + [str(pct) for _, pct in facilities]

write_header = not CSV_PATH.exists()
with open(CSV_PATH, "a", newline="") as f:
    w = csv.writer(f)
    if write_header:
        w.writerow(header)
    w.writerow(row)

# Build predictions from historical data
# Group by (day_of_week, hour) -> facility -> list of pcts
with open(CSV_PATH, newline="") as f:
    reader = list(csv.reader(f))
col_names = reader[0][1:]
history = reader[1:]

averages = defaultdict(lambda: defaultdict(list))
for r in history:
    try:
        ts = datetime.strptime(r[0], "%Y-%m-%d %H:%M")
    except ValueError:
        continue
    key = (ts.weekday(), ts.hour)
    for i, val in enumerate(r[1:]):
        averages[key][col_names[i]].append(int(val))

# Format email
lines = ["CURRENT OCCUPANCY", ""]
for name, pct in facilities:
    if name not in tracked:
        continue
    short = SHORT_NAMES.get(name, name)
    bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
    lines.append(f"  {bar} {pct:3d}%  {short}")

# Best times for rest of today
today_dow = now.weekday()
upcoming_hours = list(range(now.hour + 1, 24))

hour_scores = []
for hour in upcoming_hours:
    key = (today_dow, hour)
    facility_avgs = {}
    for name in col_names:
        if name not in tracked:
            continue
        bucket = averages[key][name]
        if bucket:
            facility_avgs[name] = round(sum(bucket) / len(bucket))
    if facility_avgs:
        overall = round(sum(facility_avgs.values()) / len(facility_avgs))
        hour_scores.append((hour, overall, facility_avgs))

if hour_scores:
    best = sorted(hour_scores, key=lambda x: x[1])[:3]
    lines += ["", "", "BEST TIMES TO GO TODAY", ""]
    for rank, (hour, overall, per_facility) in enumerate(best, 1):
        h = hour % 12 or 12
        ampm = "AM" if hour < 12 else "PM"
        time_str = f"{h}:{00:02d} {ampm}"
        lines.append(f"  #{rank}  {time_str}  ~{overall}% avg")
        for name, avg in per_facility.items():
            short = SHORT_NAMES.get(name, name)
            lines.append(f"        {short}: {avg}%")
        lines.append("")

body = "\n".join(lines)
print(body)

gmail_user = os.environ["GMAIL_USER"]
gmail_password = os.environ["GMAIL_APP_PASSWORD"]
recipient = os.environ["RECIPIENT_EMAIL"]

msg = MIMEText(body)
msg["Subject"] = f"Gym Occupancy — {now_str}"
msg["From"] = gmail_user
msg["To"] = recipient

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
    s.login(gmail_user, gmail_password)
    s.sendmail(gmail_user, recipient, msg.as_string())

print("Email sent.")
