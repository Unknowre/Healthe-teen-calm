import os
import requests
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# ดึงฟังก์ชันจัดการ Database มาใช้
from db import get_sleep_setting, get_sleep_settings

load_dotenv()

# ตรวจสอบ Token สำหรับส่งข้อความ Push
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
if not LINE_CHANNEL_ACCESS_TOKEN:
    print("⚠️ Warning: Missing LINE_CHANNEL_ACCESS_TOKEN in .env")

# ตั้งค่า Scheduler โดยใช้ Timezone กรุงเทพฯ
scheduler = BackgroundScheduler(timezone="Asia/Bangkok")

def _line_push(user_id: str, messages: list[dict]):
    """ฟังก์ชันสำหรับส่งข้อความแจ้งเตือนหาผู้ใช้โดยตรง"""
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"to": user_id, "messages": messages}
    try:
        r = requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers=headers,
            json=payload,
            timeout=20
        )
        if r.status_code >= 400:
            print(f"❌ LINE push failed: {r.status_code} {r.text}")
    except Exception as e:
        print(f"❌ Error sending push: {e}")

def _job_id(kind: str, user_id: str) -> str:
    """สร้าง ID สำหรับงานตั้งเวลา"""
    return f"sleep:{kind}:{user_id}"

def _remove_job(job_id: str):
    """ลบงานเดิมออกก่อนตั้งใหม่"""
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass

def _push_bedtime(user_id: str):
    """ข้อความแจ้งเตือนเข้านอน"""
    _line_push(user_id, [{
        "type": "text",
        "text": "🌙 จะเข้านอนแล้วนะ 🤍 อย่าลืมวางมือถือแล้วพักผ่อนนะ วันนี้เธอเก่งมากแล้ว"
    }])

def _push_waketime(user_id: str):
    """ข้อความแจ้งเตือนตื่นนอน"""
    _line_push(user_id, [{
        "type": "text",
        "text": "☀️ ต้องตื่นแล้วนะ 🤍 ขอให้เป็นวันที่ดีและใจเบาสำหรับเธอนะ"
    }])

def _schedule_one(user_id: str):
    """ตั้งค่าเวลาแจ้งเตือนรายบุคคลลงในหน่วยความจำ"""
    s = get_sleep_setting(user_id)
    enabled = int(s.get("enabled", 0) or 0)

    bed_id = _job_id("bed", user_id)
    wake_id = _job_id("wake", user_id)

    # ลบงานเก่าออกก่อนเสมอเพื่อป้องกันการซ้ำซ้อน
    _remove_job(bed_id)
    _remove_job(wake_id)

    # ถ้าผู้ใช้ปิดการแจ้งเตือน ไม่ต้องตั้ง Job
    if enabled != 1:
        return

    bedtime = s.get("bedtime")
    waketime = s.get("waketime")

    # ตั้งเวลาเข้านอน
    if bedtime and ":" in bedtime:
        hh, mm = bedtime.split(":")
        scheduler.add_job(
            _push_bedtime,
            CronTrigger(hour=int(hh), minute=int(mm)),
            id=bed_id,
            args=[user_id],
            replace_existing=True,
            misfire_grace_time=300
        )

    # ตั้งเวลาตื่น
    if waketime and ":" in waketime:
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
    """เริ่มการทำงานของระบบตั้งเวลา และโหลดข้อมูลจาก DB ทั้งหมด"""
    if not scheduler.running:
        scheduler.start()
        print("🚀 Scheduler started!")
        
        # ดึงข้อมูลทุกคนที่เปิดใช้งานจาก Database มาตั้ง Job ใหม่
        try:
            all_users = get_sleep_settings()
            for s in all_users:
                _schedule_one(s["user_id"])
            print(f"✅ Synced {len(all_users)} users' schedules from Database.")
        except Exception as e:
            print(f"❌ Error during initial sync: {e}")

def sync_user(user_id: str):
    """เรียกใช้ฟังก์ชันนี้ทันทีหลังจากผู้ใช้แก้ไขเวลาในแชท"""
    _schedule_one(user_id)