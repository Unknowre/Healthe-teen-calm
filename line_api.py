import os
import requests
from dotenv import load_dotenv

load_dotenv()

LINE_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]

def line_reply(reply_token: str, messages: list[dict]):
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {"Authorization": f"Bearer {LINE_ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"replyToken": reply_token, "messages": messages}
    r = requests.post(url, headers=headers, json=payload, timeout=15)
    r.raise_for_status()

def line_push(user_id: str, messages: list[dict]):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Authorization": f"Bearer {LINE_ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"to": user_id, "messages": messages}
    r = requests.post(url, headers=headers, json=payload, timeout=15)
    r.raise_for_status()