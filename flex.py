TREE_STAGE_IMAGES = [
    "https://res.cloudinary.com/dosglkcvm/image/upload/v1771731536/lvl11_bmoktg.png",
    "https://res.cloudinary.com/dosglkcvm/image/upload/v1771731822/lvl2_h1oi6w.png",
    "https://res.cloudinary.com/dosglkcvm/image/upload/v1771736586/lvl3_o3jrot.png",
    "https://res.cloudinary.com/dosglkcvm/image/upload/v1771736700/lvl4_al3tzn.png",
    "https://res.cloudinary.com/dosglkcvm/image/upload/v1771744150/lvl5_ciqxxt.png",
    "https://res.cloudinary.com/dosglkcvm/image/upload/v1771744276/lvl6_itvbhk.png",
    "https://res.cloudinary.com/dosglkcvm/image/upload/v1771744487/lvl7_brlszj.png",
    "https://res.cloudinary.com/dosglkcvm/image/upload/v1771744655/lvl8_u6rj1d.png",
    "https://res.cloudinary.com/dosglkcvm/image/upload/v1771745219/lvl9_n84qys.png",
    "https://res.cloudinary.com/dosglkcvm/image/upload/v1771745714/lvl10_o1jrz6.png",
]

def _tree_image_for_level(level: int) -> str | None:
    stage = ((max(1, min(100, int(level))) - 1) // 10)
    if 0 <= stage < len(TREE_STAGE_IMAGES):
        return TREE_STAGE_IMAGES[stage]
    return None

def diary_prompt_flex(level: int):
    img = _tree_image_for_level(level)
    bubble = {
        "type": "bubble",
        "size": "giga",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": "🌱 บันทึกความสุขวันนี้", "weight": "bold", "size": "lg", "wrap": True},
                {"type": "text", "text": f"ต้นไม้เลเวล {level}/100", "size": "sm", "color": "#555555", "wrap": True},
                {"type": "text", "text": "ให้คะแนนวันนี้ก่อนก็ได้ (ข้ามได้)", "size": "sm", "color": "#111111", "wrap": True},
                {
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "sm",
                    "contents": [
                        {"type": "button", "height": "sm", "style": "secondary", "action": {"type": "postback", "label": "1", "data": "score=1"}},
                        {"type": "button", "height": "sm", "style": "secondary", "action": {"type": "postback", "label": "2", "data": "score=2"}},
                        {"type": "button", "height": "sm", "style": "secondary", "action": {"type": "postback", "label": "3", "data": "score=3"}},
                        {"type": "button", "height": "sm", "style": "secondary", "action": {"type": "postback", "label": "4", "data": "score=4"}},
                        {"type": "button", "height": "sm", "style": "secondary", "action": {"type": "postback", "label": "5", "data": "score=5"}},
                    ]
                },
                {
                    "type": "button",
                    "style": "link",
                    "height": "sm",
                    "action": {"type": "postback", "label": "ข้ามคะแนน", "data": "score=0"}
                },
                {"type": "separator", "margin": "md"},
                {"type": "text", "text": "พิมพ์เล่าว่า “วันนี้มีความสุขยังไง” มาได้เลย", "wrap": True, "size": "md"},
            ]
        }
    }
    if img:
        bubble["hero"] = {
            "type": "image",
            "url": img,
            "size": "full",
            "aspectMode": "cover",
            "aspectRatio": "16:9"
        }
    return {"type": "flex", "altText": "บันทึกความสุขวันนี้", "contents": bubble}

def tree_progress_flex(stats: dict):
    level = int(stats.get("level", 1))
    streak = int(stats.get("streak", 0))
    total = int(stats.get("total", 0))
    in_level = int(stats.get("in_level", 0))
    need_for_next = int(stats.get("need_for_next", 0))
    to_next = int(stats.get("to_next", 0))

    img = _tree_image_for_level(level)

    prog_text = "MAX" if level >= 100 else f"{in_level}/{need_for_next} (อีก {to_next} ครั้งเลเวลอัพ)"
    bubble = {
        "type": "bubble",
        "size": "giga",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": "💧 รดน้ำต้นไม้ +1", "weight": "bold", "size": "lg"},
                {"type": "text", "text": f"เลเวล {level}/100", "size": "xl", "weight": "bold", "wrap": True},
                {"type": "text", "text": f"ความคืบหน้า: {prog_text}", "size": "sm", "color": "#444444", "wrap": True},
                {
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "md",
                    "contents": [
                        {"type": "text", "text": f"🔥 สตรีค: {streak} วัน", "size": "sm", "wrap": True},
                        {"type": "text", "text": f"📌 รวม: {total} ครั้ง", "size": "sm", "wrap": True},
                    ]
                },
                {"type": "separator"},
                {"type": "text", "text": "อยากบันทึกอีกครั้ง พิมพ์มาได้เลย หรือกดเมนูบันทึกอีกที 🌿", "size": "sm", "wrap": True, "color": "#333333"}
            ]
        }
    }
    if img:
        bubble["hero"] = {
            "type": "image",
            "url": img,
            "size": "full",
            "aspectMode": "cover",
            "aspectRatio": "16:9"
        }
    return {"type": "flex", "altText": "ต้นไม้เติบโตขึ้นแล้ว", "contents": bubble}

def todo_menu_flex():
    return {
        "type": "flex",
        "altText": "To-do",
        "contents": {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {"type": "text", "text": "📋 To-do Planner", "weight": "bold", "size": "xl"},
                    {"type": "text", "text": "เลือกทำรายการได้เลย", "size": "sm", "color": "#555555"},
                    {"type": "button", "style": "primary", "action": {"type": "postback", "label": "เพิ่มงาน", "data": "todo=add"}},
                    {"type": "button", "style": "secondary", "action": {"type": "postback", "label": "ดูรายการ", "data": "todo=list"}},
                    {"type": "button", "style": "link", "action": {"type": "postback", "label": "ล้างงานที่เสร็จแล้ว", "data": "todo=clear_done"}}
                ]
            }
        }
    }

def todo_list_flex(todos: list[dict]):
    rows = []
    for t in todos[:10]:
        status = t.get("status", "todo")
        label = "✅ done" if status == "done" else "⬜ todo"
        rows.append({
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": [
                {"type": "text", "text": label, "size": "sm", "flex": 0},
                {"type": "text", "text": str(t.get("title", "")), "size": "sm", "wrap": True, "flex": 1},
                {"type": "button", "style": "link", "height": "sm", "action": {"type": "postback", "label": "ติ๊ก", "data": f"todo_done={t.get('id')}"}}
            ]
        })
    if not rows:
        rows = [{"type": "text", "text": "ยังไม่มีงานเลย ลองกด ‘เพิ่มงาน’ ดูนะ", "wrap": True, "size": "sm"}]

    return {
        "type": "flex",
        "altText": "รายการ To-do",
        "contents": {
            "type": "bubble",
            "body": {"type": "box", "layout": "vertical", "spacing": "md", "contents": [
                {"type": "text", "text": "📋 รายการงาน", "weight": "bold", "size": "xl"},
                *rows
            ]}
        }
    }

def sleep_menu_flex(bedtime, waketime, enabled):
    enabled = int(enabled or 0)
    status = "✅ เปิดอยู่" if enabled == 1 else "⛔ ปิดอยู่"
    bt = bedtime or "-"
    wt = waketime or "-"
    return {
        "type": "flex",
        "altText": "ตั้งค่าเตือนนอน",
        "contents": {
            "type": "bubble",
            "body": {"type": "box", "layout": "vertical", "spacing": "md", "contents": [
                {"type": "text", "text": "⏰ แจ้งเตือนการนอน", "weight": "bold", "size": "xl"},
                {"type": "text", "text": f"สถานะ: {status}", "size": "sm", "wrap": True},
                {"type": "text", "text": f"เข้านอน: {bt}", "size": "sm"},
                {"type": "text", "text": f"ตื่น: {wt}", "size": "sm"},
                {"type": "separator"},
                {"type": "button", "style": "secondary", "action": {"type": "postback", "label": "ตั้งเวลาเข้านอน", "data": "sleep=set_bed"}},
                {"type": "button", "style": "secondary", "action": {"type": "postback", "label": "ตั้งเวลาตื่น", "data": "sleep=set_wake"}},
                {"type": "button", "style": "primary", "action": {"type": "postback", "label": "เปิด/ปิด แจ้งเตือน", "data": "sleep=toggle"}},
            ]}
        }
    }

def journal_poster_flex(title: str, bullets: list[str]):
    safe_bullets = bullets[:4] if bullets else []
    bullet_nodes = []
    for b in safe_bullets:
        bullet_nodes.append({
            "type": "box",
            "layout": "baseline",
            "spacing": "sm",
            "contents": [
                {"type": "text", "text": "•", "flex": 0, "size": "sm", "color": "#2E7D32"},
                {"type": "text", "text": b, "wrap": True, "flex": 1, "size": "sm", "color": "#222222"}
            ]
        })

    return {
        "type": "flex",
        "altText": f"วารสาร: {title}",
        "contents": {
            "type": "bubble",
            "size": "giga",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {"type": "text", "text": "📰 วารสารให้ความรู้", "weight": "bold", "size": "sm", "color": "#1B5E20"},
                    {"type": "text", "text": title, "weight": "bold", "size": "xl", "wrap": True, "color": "#111111"},
                    {"type": "box", "layout": "vertical", "spacing": "sm", "contents": bullet_nodes},
                    {"type": "separator", "margin": "md"},
                    {"type": "text", "text": "📞 สายด่วนสุขภาพจิต 1323 (24 ชม.)", "size": "sm", "color": "#D32F2F", "weight": "bold", "wrap": True},
                    {"type": "text", "text": "🚑 ฉุกเฉินโทร 1669", "size": "sm", "color": "#D32F2F", "weight": "bold", "wrap": True}
                ]
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "contents": [
                    {"type": "button", "style": "primary", "height": "sm", "action": {"type": "postback", "label": "ถัดไป", "data": "journal=next"}},
                    {"type": "button", "style": "secondary", "height": "sm", "action": {"type": "postback", "label": "สุ่ม", "data": "journal=random"}},
                ]
            }
        }
    }

def media_poster_flex(title: str, bullets: list[str], footer_buttons: list[dict]):
    safe_bullets = bullets[:4] if bullets else []
    bullet_nodes = []
    for b in safe_bullets:
        bullet_nodes.append({
            "type": "box",
            "layout": "baseline",
            "spacing": "sm",
            "contents": [
                {"type": "text", "text": "•", "flex": 0, "size": "sm", "color": "#1E88E5"},
                {"type": "text", "text": b, "wrap": True, "flex": 1, "size": "sm", "color": "#222222"}
            ]
        })

    bubble = {
        "type": "bubble",
        "size": "giga",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": "🎧 เพลย์ลิสต์แนะนำ", "weight": "bold", "size": "sm", "color": "#0D47A1"},
                {"type": "text", "text": title, "weight": "bold", "size": "xl", "wrap": True, "color": "#111111"},
                {"type": "box", "layout": "vertical", "spacing": "sm", "contents": bullet_nodes},
                {"type": "separator", "margin": "md"},
                {"type": "text", "text": "📞 สายด่วนสุขภาพจิต 1323 (24 ชม.)", "size": "sm", "color": "#D32F2F", "weight": "bold", "wrap": True},
                {"type": "text", "text": "🚑 ฉุกเฉินโทร 1669", "size": "sm", "color": "#D32F2F", "weight": "bold", "wrap": True}
            ]
        }
    }

    if footer_buttons:
        bubble["footer"] = {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": footer_buttons[:2]
        }

    return {"type": "flex", "altText": f"รายการ: {title}", "contents": bubble}

def media_carousel_flex(items: list[dict]):
    bubbles = []
    for it in items[:10]:
        bubbles.append({
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {"type": "text", "text": it.get("title", ""), "weight": "bold", "size": "lg", "wrap": True},
                    {"type": "text", "text": it.get("benefit", ""), "size": "sm", "wrap": True, "color": "#444444"},
                    {"type": "button", "style": "primary", "action": {"type": "uri", "label": it.get("btn_label", "เปิดลิงก์"), "uri": it.get("url", "")}}
                ]
            }
        })
    return {"type": "flex", "altText": "เพลง/ออกกำลังกาย", "contents": {"type": "carousel", "contents": bubbles}}