import os
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def create_rich_menu():
    url = "https://api.line.me/v2/bot/richmenu"
    body = {
        "size": {"width": 2500, "height": 1686},
        "selected": True,
        "name": "Healthe teen calm",
        "chatBarText": "เมนู",
        "areas": [
            # แถวบน 3 ช่อง (A,B,C)
            {"bounds": {"x": 0, "y": 0, "width": 833, "height": 843},
             "action": {"type": "postback", "data": "action=diary", "displayText": "บันทึกวันนี้"}},
            {"bounds": {"x": 833, "y": 0, "width": 833, "height": 843},
             "action": {"type": "postback", "data": "action=todo", "displayText": "Planner"}},
            {"bounds": {"x": 1666, "y": 0, "width": 834, "height": 843},
             "action": {"type": "postback", "data": "action=heal", "displayText": "ที่พักฮีลใจ"}},

            # แถวล่าง 3 ช่อง (D,E,F)
            {"bounds": {"x": 0, "y": 843, "width": 833, "height": 843},
             "action": {"type": "postback", "data": "action=sleep", "displayText": "แจ้งเตือนการนอน"}},
            {"bounds": {"x": 833, "y": 843, "width": 833, "height": 843},
             "action": {"type": "postback", "data": "action=journal", "displayText": "วารสาร"}},
            {"bounds": {"x": 1666, "y": 843, "width": 834, "height": 843},
             "action": {"type": "postback", "data": "action=media", "displayText": "เพลง/ออกกำลัง"}},
        ]
    }

    r = requests.post(url, headers=HEADERS, json=body, timeout=30)
    r.raise_for_status()
    richmenu_id = r.json()["richMenuId"]
    print("Created rich menu:", richmenu_id)
    return richmenu_id

def upload_image(richmenu_id: str, image_path: str):
    url = f"https://api-data.line.me/v2/bot/richmenu/{richmenu_id}/content"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "image/png"
    }
    with open(image_path, "rb") as f:
        r = requests.post(url, headers=headers, data=f, timeout=60)
    r.raise_for_status()
    print("Uploaded image.")

def set_default(richmenu_id: str):
    url = f"https://api.line.me/v2/bot/user/all/richmenu/{richmenu_id}"
    r = requests.post(url, headers={"Authorization": f"Bearer {TOKEN}"}, timeout=30)
    r.raise_for_status()
    print("Set default rich menu.")

if __name__ == "__main__":
    # 1) สร้าง rich menu
    rid = create_rich_menu()

    # 2) อัปโหลดรูป PNG จาก Canva
    # ใส่ path ไฟล์รูปของเธอ (ต้องเป็น PNG ขนาด 2500x1686)
    upload_image(rid, "MOODDiary.png")

    # 3) ตั้งเป็น default ให้ทุกคน
    set_default(rid)