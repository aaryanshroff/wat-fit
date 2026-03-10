import os
import smtplib
from email.mime.text import MIMEText

import requests
from bs4 import BeautifulSoup

URL = "https://warrior.uwaterloo.ca/FacilityOccupancy"

resp = requests.get(URL)
resp.raise_for_status()

soup = BeautifulSoup(resp.text, "html.parser")

lines = []
for card in soup.find_all("div", class_="occupancy-card"):
    name = card.find("h2").get_text(strip=True)
    canvas = card.find("canvas", class_="occupancy-chart")
    count = int(canvas["data-occupancy"])
    remaining = int(canvas["data-remaining"])
    max_occ = count + remaining
    pct = round(float(canvas["data-ratio"]) * 100)
    lines.append(f"{name}: {count}/{max_occ} ({pct}%)")

body = "\n".join(lines)
print(body)

gmail_user = os.environ["GMAIL_USER"]
gmail_password = os.environ["GMAIL_APP_PASSWORD"]
recipient = os.environ["RECIPIENT_EMAIL"]

msg = MIMEText(body)
msg["Subject"] = "UWaterloo Gym Occupancy"
msg["From"] = gmail_user
msg["To"] = recipient

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
    s.login(gmail_user, gmail_password)
    s.sendmail(gmail_user, recipient, msg.as_string())

print("Email sent.")
