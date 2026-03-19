import os
import requests


def send_whatsapp_msg(to_number: str, text: str) -> None:
    phone_id = os.getenv("PHONE_ID")
    token = os.getenv("WHATSAPP_TOKEN")
    if not phone_id or not token:
        raise RuntimeError("PHONE_ID or WHATSAPP_TOKEN not set")

    url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "text": {"body": text},
    }
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    response.raise_for_status()
