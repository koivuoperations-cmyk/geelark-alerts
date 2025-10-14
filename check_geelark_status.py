import os
import smtplib
import json
import requests
from email.mime.text import MIMEText

# ==== LOAD CONFIGURATION FROM ENVIRONMENT ====
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", EMAIL_SENDER)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

GEELARK_API = os.getenv("GEELARK_API", "https://openapi.geelark.com/open/v1/phone/status")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
PHONE_IDS = os.getenv("PHONE_IDS")  # comma-separated list of IDs

if not all([EMAIL_SENDER, EMAIL_PASSWORD, BEARER_TOKEN, PHONE_IDS]):
    raise ValueError("Missing one or more required environment variables.")

phone_list = [pid.strip() for pid in PHONE_IDS.split(",") if pid.strip()]

# ==== CALL GEELARK API ====
response = requests.post(
    GEELARK_API,
    headers={
        "Authorization": f"Bearer {BEARER_TOKEN}",
        "Content-Type": "application/json"
    },
    json={"ids": phone_list}
)

data = response.json()
print("API response:", json.dumps(data, indent=2))

# ==== CHECK EACH PHONE ====
alerts = []
if data.get("code") == 0 and "data" in data:
    for phone in data["data"].get("successDetails", []):
        status = phone.get("status")
        if status == 3:
            alerts.append(f"⚠️ Phone {phone['id']} ({phone['serialName']}) is expired (status 3).")

    for fail in data["data"].get("failDetails", []):
        if fail.get("code") == 42001:
            alerts.append(f"❌ Phone {fail['id']} does not exist (code 42001).")

else:
    alerts.append(f"API error: {data.get('msg', 'Unknown error')}")

# ==== SEND EMAIL ALERT IF NEEDED ====
if alerts:
    body = "\n".join(alerts) + "\n\nFull API response:\n" + json.dumps(data, indent=2)
    msg = MIMEText(body)
    msg["Subject"] = "⚠️ Geelark Cloud Phone Alert"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)

    print("Alert email sent!")
else:
    print("✅ All phones are healthy.")
