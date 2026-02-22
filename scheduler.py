import os
import requests
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from db import get_sleep_setting, get_sleep_settings

load_dotenv()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
if not LINE_CHANNEL_ACCESS_TOKEN:
    raise RuntimeError("Missing LINE_CHANNEL_ACCESS_TOKEN in .env")

scheduler = BackgroundScheduler(timezone="Asia/Bangkok")

def _line_push(user_id: str, messages: list[dict]):
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"to": user_id, "messages": messages}
    r = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers=headers,
        json=payload,
        timeout=20
    )
    if r.status_code >= 400:
        raise RuntimeError(f"LINE push failed: {r.status_code} {r.text}")

def _job_id(kind: str, user_id: str) -> str:
    return f"sleep:{kind}:{user_id}"

def _remove_job(job_id: str):
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass

def _push_bedtime(user_id: str):
    _line_push(user_id, [{
        "type": "text",
        "text": "🌙 ถึงเวลาเตรียมตัวนอนแล้วนะ 🤍\n"
                "ลองวางมือถือ 5 นาที หายใจลึกๆ 3 รอบ แล้วค่อยเข้านอน\n"
                "ถ้าเครียดมาก โทร 1323 ได้เลย"
    }])

def _push_waketime(user_id: str):
    _line_push(user_id, [{
        "type": "text",
        "text": "☀️ ได้เวลาตื่นแล้วนะ 🤍\n"
                "ดื่มน้ำ 1 แก้ว + ยืดตัวเบาๆ 30 วิ\n"
                "วันนี้ขอให้ใจเบาลงนิดนึงนะ"
    }])

def _schedule_one(user_id: str):
    s = get_sleep_setting(user_id)
    enabled = int(s.get("enabled", 0) or 0)

    bed_id = _job_id("bed", user_id)
    wake_id = _job_id("wake", user_id)

    _remove_job(bed_id)
    _remove_job(wake_id)

    if enabled != 1:
        return

    bedtime = s.get("bedtime")
    waketime = s.get("waketime")

    if bedtime:
        hh, mm = bedtime.split(":")
        scheduler.add_job(
            _push_bedtime,
            CronTrigger(hour=int(hh), minute=int(mm)),
            id=bed_id,
            args=[user_id],
            replace_existing=True,
            misfire_grace_time=300
        )

    if waketime:
        hh, mm = waketime.split(":")
        scheduler.add_job(
            _push_waketime,
            CronTrigger(hour=int(hh), minute=int(mm)),
            id=wake_id,
            args=[user_id],
            replace_existing=True,
            misfire_grace_time=300
        )

def start_scheduler():
    if not scheduler.running:
        scheduler.start()

    # โหลดทุก user ที่เปิด enabled=1 แล้วตั้ง job ให้
    for row in get_sleep_settings():
        try:
            _schedule_one(row["user_id"])
        except Exception:
            pass

def sync_user(user_id: str):
    # เรียกหลัง set_sleep ทุกครั้ง เพื่ออัปเดตทันที
    _schedule_one(user_id)