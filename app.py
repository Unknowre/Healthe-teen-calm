import os
import hmac
import hashlib
import base64
import random
from urllib.parse import parse_qs

from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv

from db import (
    init_db, upsert_user, set_mode, get_mode,
    add_diary, add_todo, list_todo, mark_todo_done,
    get_diary_stats, get_sleep_setting, set_sleep, clear_done_todos,
    get_journal_idx, set_journal_idx
)

from flex import (
    diary_prompt_flex, todo_menu_flex, todo_list_flex,
    sleep_menu_flex, journal_poster_flex, media_poster_flex, media_carousel_flex,
    tree_progress_flex
)

from ai import heal_reply
from line_api import line_reply
from scheduler import start_scheduler, sync_user

load_dotenv()
LINE_CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]

app = FastAPI()

JOURNALS = [
    ("ความเครียดของนักศึกษา: รู้ทัน-จัดการได้", [
        "ความเครียดไม่ใช่ความอ่อนแอ แต่เป็นสัญญาณว่าระบบชีวิตเริ่มตึง",
        "แยกสาเหตุให้ชัด: เรื่องเรียน/ทักษะการเรียน/สภาพแวดล้อม/ความสัมพันธ์ แล้วเลือกแก้ทีละจุด",
        "ใช้วิธีเผชิญความเครียดแบบ “แก้ปัญหา” ก่อน (ทำแผนเล็กๆ 1 ขั้นตอน) แล้วค่อยขอแรงสนับสนุน"
    ]),
    ("ภาวะซึมเศร้าในผู้หญิงขับรถส่งอาหาร: สัญญาณที่ไม่ควรมองข้าม", [
        "ถ้าเริ่มหมดแรง/หมดความสุข/นอนไม่เป็นเวลา ให้ถือว่าเป็นสัญญาณเตือน ไม่ต้องฝืนคนเดียว",
        "ลดตัวกระตุ้นที่ควบคุมได้: พักสั้นๆเป็นช่วง, กินน้ำ-อาหารให้ตรงเวลา, ตั้งขอบเขตงาน/บ้าน",
        "ถ้ามีหลายบทบาทพร้อมกัน (งาน+ภาระบ้าน+ความตึงในครอบครัว) ให้เริ่ม “ขอความช่วยเหลือ 1 เรื่อง” ก่อน"
    ]),
    ("ปรับความคิด-พฤติกรรม ลดดื้อ-ต่อต้าน (สำหรับวัยรุ่นสมาธิสั้น)", [
        "พฤติกรรมดื้อ/เถียง/ปะทะ ไม่ใช่แปลว่าเด็กไม่ดี แต่เป็นรูปแบบที่ “ฝึกใหม่” ได้",
        "ใช้สูตรสั้นๆ: หยุด-คิด-เลือก (Pause → Think → Choose) ก่อนตอบโต้ทุกครั้ง",
        "ทำข้อตกลงเล็กๆที่วัดได้ (เช่น 1 ข้อ/วัน) + ชมทันทีเมื่อทำได้ เพื่อเสริมแรงพฤติกรรมใหม่"
    ]),
    ("ชีวิตกลมกลืนแบบซาเทียร์: บ้านสงบ ใจเบาขึ้น", [
        "ความกลมกลืนในชีวิตคือการรับรู้ตัวเอง-ความรู้สึก-ความต้องการได้ชัด ไม่หลงไปกับแรงกดดัน",
        "เวลาบ้านตึง ให้เริ่มที่ “สื่อสารแบบไม่ทำร้ายกัน”: พูดความรู้สึก + ขอสิ่งที่ต้องการแบบตรงๆ",
        "การเลี้ยงดูที่ดีไม่ต้องเพอร์เฟกต์ แต่ต้อง “สม่ำเสมอ + ปลอดภัย + รับฟัง”"
    ]),
    ("กรอบ OECD สุขภาพจิต: ดูแลใจแบบทั้งระบบ", [
        "สุขภาพจิตไม่ได้จบที่การรักษา แต่รวมถึงการป้องกัน-ส่งเสริม-การเข้าถึงบริการที่เหมาะกับคนแต่ละกลุ่ม",
        "การดูแลใจที่ดีต้องมีทั้งระดับบุคคล (ทักษะชีวิต) และระดับสังคม (โรงเรียน/งาน/ชุมชน)",
        "เริ่มจากตัวเรา: เลือก 1 ปัจจัยที่ทำให้ใจดีขึ้น (นอน/สัมพันธ์/งาน/การเงิน) แล้วปรับแบบค่อยเป็นค่อยไป"
    ]),
    ("มาตรฐานความงามกับสุขภาวะ: กลับมาเห็นค่าตัวเอง", [
        "โซเชียลคือ “ไฮไลต์” ไม่ใช่ความจริงทั้งหมด—อย่าเอามาตัดสินคุณค่าตัวเอง",
        "ย้ายโฟกัสจาก “ต้องสวย” เป็น “ต้องไหว”: นอนพอ กินพอ น้ำพอ ขยับพอ",
        "ฝึกประโยคกันพัง: “ร่างกายฉันมีไว้ใช้ชีวิต ไม่ใช่มีไว้ให้คนให้คะแนน”"
    ]),
]

MEDIA_PAGE_SIZE = 10

MEDIA_CATEGORIES = {
    "thai_chill": {
        "title": "🇹🇭 เพลงไทย Gen Z Chill",
        "items": [
            {"title": "แค่คุณ – Musketeers", "url": "https://www.youtube.com/results?search_query=แค่คุณ+musketeers", "btn_label": "เปิดลิงก์", "benefit": "ชิล ฟังสบาย"},
            {"title": "ลม – Scrubb", "url": "https://www.youtube.com/results?search_query=ลม+scrubb", "btn_label": "เปิดลิงก์", "benefit": "ชิล ๆ ฟังเพลิน"},
            {"title": "ทุกฤดู – Polycat", "url": "https://www.youtube.com/results?search_query=ทุกฤดู+polycat", "btn_label": "เปิดลิงก์", "benefit": "ละมุน ๆ"},
            {"title": "ถ้าเธอรักใครคนหนึ่ง – Ink Waruntorn", "url": "https://www.youtube.com/results?search_query=ถ้าเธอรักใครคนหนึ่ง+ink", "btn_label": "เปิดลิงก์", "benefit": "โรแมนติก"},
            {"title": "วันหนึ่งฉันเดินเข้าป่า – Max Jenmana", "url": "https://www.youtube.com/results?search_query=วันหนึ่งฉันเดินเข้าป่า+max+jenmana", "btn_label": "เปิดลิงก์", "benefit": "ฟีลดี"},
            {"title": "เรื่องที่ขอ – Lomosonic", "url": "https://www.youtube.com/results?search_query=เรื่องที่ขอ+lomasonic", "btn_label": "เปิดลิงก์", "benefit": "อิน ๆ"},
            {"title": "ดวงใจ – Palmy", "url": "https://www.youtube.com/results?search_query=ดวงใจ+palmy", "btn_label": "เปิดลิงก์", "benefit": "อบอุ่น"},
            {"title": "เธอหมุนรอบฉัน ฉันหมุนรอบเธอ – Scrubb", "url": "https://www.youtube.com/results?search_query=เธอหมุนรอบฉัน+scrubb", "btn_label": "เปิดลิงก์", "benefit": "ชิลคลาสสิก"},
            {"title": "ใกล้ – Scrubb", "url": "https://www.youtube.com/results?search_query=ใกล้+scrubb", "btn_label": "เปิดลิงก์", "benefit": "ฟังเพลิน"},
            {"title": "แอบดี – Stamp", "url": "https://www.youtube.com/results?search_query=แอบดี+stamp", "btn_label": "เปิดลิงก์", "benefit": "น่ารัก"},
            {"title": "ความคิด – Stamp", "url": "https://www.youtube.com/results?search_query=ความคิด+stamp", "btn_label": "เปิดลิงก์", "benefit": "ชิล ๆ"},
            {"title": "เพื่อนเล่น ไม่เล่นเพื่อน – Tilly Birds", "url": "https://www.youtube.com/results?search_query=เพื่อนเล่นไม่เล่นเพื่อน+tilly+birds", "btn_label": "เปิดลิงก์", "benefit": "Gen Z มาก"},
            {"title": "ถ้าเราเจอกันอีก – Tilly Birds", "url": "https://www.youtube.com/results?search_query=ถ้าเราเจอกันอีก+tilly+birds", "btn_label": "เปิดลิงก์", "benefit": "เศร้า ๆ"},
            {"title": "ทางของฝุ่น – Atom Chanakan", "url": "https://www.youtube.com/results?search_query=ทางของฝุ่น+atom", "btn_label": "เปิดลิงก์", "benefit": "อิน ๆ"},
            {"title": "ความธรรมดา – Getsunova", "url": "https://www.youtube.com/results?search_query=ความธรรมดา+getsunova", "btn_label": "เปิดลิงก์", "benefit": "ฟีลดี"},
            {"title": "ความลับ – Pause", "url": "https://www.youtube.com/results?search_query=ความลับ+pause", "btn_label": "เปิดลิงก์", "benefit": "ละมุน"},
            {"title": "ฤดูที่ฉันเหงา – Flure", "url": "https://www.youtube.com/results?search_query=ฤดูที่ฉันเหงา+flure", "btn_label": "เปิดลิงก์", "benefit": "เหงาแต่สวย"},
            {"title": "ดาว – Pause", "url": "https://www.youtube.com/results?search_query=ดาว+pause", "btn_label": "เปิดลิงก์", "benefit": "ชิล"},
            {"title": "ยิ้ม – Musketeers", "url": "https://www.youtube.com/results?search_query=ยิ้ม+musketeers", "btn_label": "เปิดลิงก์", "benefit": "ฟีลดี"},
            {"title": "คิดถึง – Silly Fools (Acoustic)", "url": "https://www.youtube.com/results?search_query=คิดถึง+silly+fools+acoustic", "btn_label": "เปิดลิงก์", "benefit": "อะคูสติก"},
            {"title": "โลกใบใหม่ – Zom Marie", "url": "https://www.youtube.com/results?search_query=โลกใบใหม่+zom+marie", "btn_label": "เปิดลิงก์", "benefit": "สดใส"},
            {"title": "นะหน้าทอง – Joong Archen (ver chill)", "url": "https://www.youtube.com/results?search_query=นะหน้าทอง+joong", "btn_label": "เปิดลิงก์", "benefit": "ชิลเวอร์"},
            {"title": "ลาลาลอย – The TOYS", "url": "https://www.youtube.com/results?search_query=ลาลาลอย+the+toys", "btn_label": "เปิดลิงก์", "benefit": "ฟีลลอย ๆ"},
            {"title": "ก่อนฤดูฝน – The TOYS", "url": "https://www.youtube.com/results?search_query=ก่อนฤดูฝน+the+toys", "btn_label": "เปิดลิงก์", "benefit": "ละมุน"},
            {"title": "อยากให้เธอลอง – Musketeers", "url": "https://www.youtube.com/results?search_query=อยากให้เธอลอง+musketeers", "btn_label": "เปิดลิงก์", "benefit": "น่ารัก"},
            {"title": "คงดี – GUNGUN", "url": "https://www.youtube.com/results?search_query=คงดี+gungun", "btn_label": "เปิดลิงก์", "benefit": "ชิล"},
            {"title": "ถ้าเธอ – Bedroom Audio", "url": "https://www.youtube.com/results?search_query=ถ้าเธอ+bedroom+audio", "btn_label": "เปิดลิงก์", "benefit": "ละมุน"},
            {"title": "อาจจะเป็นเธอ – Ink Waruntorn", "url": "https://www.youtube.com/results?search_query=อาจจะเป็นเธอ+ink", "btn_label": "เปิดลิงก์", "benefit": "อบอุ่น"},
            {"title": "ยัง – Lipta", "url": "https://www.youtube.com/results?search_query=ยัง+lipt", "btn_label": "เปิดลิงก์", "benefit": "ชิล"},
            {"title": "ฝนตกไหม – Three Man Down", "url": "https://www.youtube.com/results?search_query=ฝนตกไหม+three+man+down", "btn_label": "เปิดลิงก์", "benefit": "อิน"},
            {"title": "เลือกได้ไหม – Zom Marie", "url": "https://www.youtube.com/results?search_query=เลือกได้ไหม+zom+marie", "btn_label": "เปิดลิงก์", "benefit": "ฟีลดี"},
            {"title": "Good Morning – TATTOO COLOUR", "url": "https://www.youtube.com/results?search_query=good+morning+tattoo+colour", "btn_label": "เปิดลิงก์", "benefit": "ชิล"},
            {"title": "เพียงแค่ใจเรารักกัน – Klear", "url": "https://www.youtube.com/results?search_query=เพียงแค่ใจเรารักกัน+klear", "btn_label": "เปิดลิงก์", "benefit": "อบอุ่น"},
            {"title": "เวลาเธอยิ้ม – Polycat", "url": "https://www.youtube.com/results?search_query=เวลาเธอยิ้ม+polycat", "btn_label": "เปิดลิงก์", "benefit": "ละมุน"},
            {"title": "เธอทำให้ฉันคิดถึง – Bedroom Audio", "url": "https://www.youtube.com/results?search_query=เธอทำให้ฉันคิดถึง+bedroom+audio", "btn_label": "เปิดลิงก์", "benefit": "ชิล"},
        ],
    },
    "inter_chill": {
        "title": "🌍 เพลงสากล Gen Z Chill",
        "items": [
            {"title": "golden hour – JVKE", "url": "https://www.youtube.com/results?search_query=golden+hour+jvke", "btn_label": "เปิดลิงก์", "benefit": "ชิล ฟีลอบอุ่น"},
            {"title": "Until I Found You – Stephen Sanchez", "url": "https://www.youtube.com/results?search_query=until+i+found+you+stephen+sanchez", "btn_label": "เปิดลิงก์", "benefit": "โรแมนติก"},
            {"title": "Every Summertime – NIKI", "url": "https://www.youtube.com/results?search_query=every+summertime+niki", "btn_label": "เปิดลิงก์", "benefit": "สดใส"},
            {"title": "Best Part – Daniel Caesar", "url": "https://www.youtube.com/results?search_query=best+part+daniel+caesar", "btn_label": "เปิดลิงก์", "benefit": "ละมุน"},
            {"title": "Paris in the Rain – Lauv", "url": "https://www.youtube.com/results?search_query=paris+in+the+rain+lauv", "btn_label": "เปิดลิงก์", "benefit": "ชิล"},
            {"title": "Heather – Conan Gray", "url": "https://www.youtube.com/results?search_query=heather+conan+gray", "btn_label": "เปิดลิงก์", "benefit": "เหงา ๆ"},
            {"title": "Sunset Lover – Petit Biscuit", "url": "https://www.youtube.com/results?search_query=sunset+lover+petit+biscuit", "btn_label": "เปิดลิงก์", "benefit": "โทนซัมเมอร์"},
            {"title": "Location Unknown – HONNE", "url": "https://www.youtube.com/results?search_query=location+unknown+honne", "btn_label": "เปิดลิงก์", "benefit": "ฟังเพลิน"},
            {"title": "Pink + White – Frank Ocean", "url": "https://www.youtube.com/results?search_query=pink+and+white+frank+ocean", "btn_label": "เปิดลิงก์", "benefit": "ละมุน"},
            {"title": "Yellow – Coldplay", "url": "https://www.youtube.com/results?search_query=yellow+coldplay", "btn_label": "เปิดลิงก์", "benefit": "คลาสสิก"},
            {"title": "Let Her Go – Passenger", "url": "https://www.youtube.com/results?search_query=let+her+go+passenger", "btn_label": "เปิดลิงก์", "benefit": "เศร้า ๆ"},
            {"title": "Slow Dancing in the Dark – Joji", "url": "https://www.youtube.com/results?search_query=slow+dancing+in+the+dark+joji", "btn_label": "เปิดลิงก์", "benefit": "ดาร์กชิล"},
            {"title": "Sweater Weather – The Neighbourhood", "url": "https://www.youtube.com/results?search_query=sweater+weather+the+neighbourhood", "btn_label": "เปิดลิงก์", "benefit": "ชิล"},
            {"title": "I Like Me Better – Lauv", "url": "https://www.youtube.com/results?search_query=i+like+me+better+lauv", "btn_label": "เปิดลิงก์", "benefit": "สดใส"},
            {"title": "Ocean Eyes – Billie Eilish", "url": "https://www.youtube.com/results?search_query=ocean+eyes+billie+eilish", "btn_label": "เปิดลิงก์", "benefit": "ละมุน"},
            {"title": "Sunroof – Nicky Youre", "url": "https://www.youtube.com/results?search_query=sunroof+nicky+youre", "btn_label": "เปิดลิงก์", "benefit": "ฟีลดี"},
            {"title": "Bad Habit – Steve Lacy", "url": "https://www.youtube.com/results?search_query=bad+habit+steve+lacy", "btn_label": "เปิดลิงก์", "benefit": "ชิล"},
            {"title": "Dandelions – Ruth B", "url": "https://www.youtube.com/results?search_query=dandelions+ruth+b", "btn_label": "เปิดลิงก์", "benefit": "โรแมนติก"},
            {"title": "Lovely – Billie Eilish & Khalid", "url": "https://www.youtube.com/results?search_query=lovely+billie+eilish+khalid", "btn_label": "เปิดลิงก์", "benefit": "ช้า ๆ"},
            {"title": "Somewhere Only We Know – Keane", "url": "https://www.youtube.com/results?search_query=somewhere+only+we+know+keane", "btn_label": "เปิดลิงก์", "benefit": "คลาสสิก"},
            {"title": "All I Want – Kodaline", "url": "https://www.youtube.com/results?search_query=all+i+want+kodaline", "btn_label": "เปิดลิงก์", "benefit": "อิน"},
            {"title": "Good Days – SZA", "url": "https://www.youtube.com/results?search_query=good+days+sza", "btn_label": "เปิดลิงก์", "benefit": "ชิล"},
            {"title": "Apocalypse – Cigarettes After Sex", "url": "https://www.youtube.com/results?search_query=apocalypse+cigarettes+after+sex", "btn_label": "เปิดลิงก์", "benefit": "ดรีมมี่"},
            {"title": "Sweet – Cigarettes After Sex", "url": "https://www.youtube.com/results?search_query=sweet+cigarettes+after+sex", "btn_label": "เปิดลิงก์", "benefit": "ดรีมมี่"},
            {"title": "Here With Me – d4vd", "url": "https://www.youtube.com/results?search_query=here+with+me+d4vd", "btn_label": "เปิดลิงก์", "benefit": "ชิล"},
            {"title": "Ghost Town – Benson Boone", "url": "https://www.youtube.com/results?search_query=ghost+town+benson+boone", "btn_label": "เปิดลิงก์", "benefit": "อิน"},
            {"title": "Love Grows – Edison Lighthouse", "url": "https://www.youtube.com/results?search_query=love+grows+edison+lighthouse", "btn_label": "เปิดลิงก์", "benefit": "ฟีลดี"},
            {"title": "Double Take – Dhruv", "url": "https://www.youtube.com/results?search_query=double+take+dhruv", "btn_label": "เปิดลิงก์", "benefit": "ละมุน"},
            {"title": "Riptide – Vance Joy", "url": "https://www.youtube.com/results?search_query=riptide+vance+joy", "btn_label": "เปิดลิงก์", "benefit": "ชิล"},
            {"title": "Bloom – The Paper Kites", "url": "https://www.youtube.com/results?search_query=bloom+the+paper+kites", "btn_label": "เปิดลิงก์", "benefit": "อุ่น ๆ"},
            {"title": "Sunday Best – Surfaces", "url": "https://www.youtube.com/results?search_query=sunday+best+surfaces", "btn_label": "เปิดลิงก์", "benefit": "สดใส"},
            {"title": "Sunflower – Post Malone", "url": "https://www.youtube.com/results?search_query=sunflower+post+malone", "btn_label": "เปิดลิงก์", "benefit": "ชิล"},
            {"title": "Let Me Down Slowly – Alec Benjamin", "url": "https://www.youtube.com/results?search_query=let+me+down+slowly+alec+benjamin", "btn_label": "เปิดลิงก์", "benefit": "อิน"},
            {"title": "Falling – Harry Styles", "url": "https://www.youtube.com/results?search_query=falling+harry+styles", "btn_label": "เปิดลิงก์", "benefit": "เหงา ๆ"},
            {"title": "Ghost – Justin Bieber", "url": "https://www.youtube.com/results?search_query=ghost+justin+bieber", "btn_label": "เปิดลิงก์", "benefit": "ชิล"},
            {"title": "Circles – Post Malone", "url": "https://www.youtube.com/results?search_query=circles+post+malone", "btn_label": "เปิดลิงก์", "benefit": "ชิล"},
            {"title": "Coffee – Sylvan Esso", "url": "https://www.youtube.com/results?search_query=coffee+sylvan+esso", "btn_label": "เปิดลิงก์", "benefit": "ชิล"},
            {"title": "2002 – Anne-Marie", "url": "https://www.youtube.com/results?search_query=2002+anne+marie", "btn_label": "เปิดลิงก์", "benefit": "น่ารัก"},
            {"title": "Youth – Troye Sivan", "url": "https://www.youtube.com/results?search_query=youth+troye+sivan", "btn_label": "เปิดลิงก์", "benefit": "ชิล"},
            {"title": "Electric Love – BORNS", "url": "https://www.youtube.com/results?search_query=electric+love+borns", "btn_label": "เปิดลิงก์", "benefit": "ฟีลดี"},
            {"title": "Yellow Hearts – Ant Saunders", "url": "https://www.youtube.com/results?search_query=yellow+hearts+ant+saunders", "btn_label": "เปิดลิงก์", "benefit": "ชิล"},
            {"title": "Love Someone – Lukas Graham", "url": "https://www.youtube.com/results?search_query=love+someone+lukas+graham", "btn_label": "เปิดลิงก์", "benefit": "อบอุ่น"},
            {"title": "Train Wreck – James Arthur", "url": "https://www.youtube.com/results?search_query=train+wreck+james+arthur", "btn_label": "เปิดลิงก์", "benefit": "อิน"},
            {"title": "Hold On – Chord Overstreet", "url": "https://www.youtube.com/results?search_query=hold+on+chord+overstreet", "btn_label": "เปิดลิงก์", "benefit": "ให้กำลังใจ"},
            {"title": "Stay – The Kid LAROI & Justin Bieber", "url": "https://www.youtube.com/results?search_query=stay+the+kid+laroi", "btn_label": "เปิดลิงก์", "benefit": "ชิล"},
        ],
    },
    "kpop_chill": {
        "title": "🇰🇷 K-POP / Lo-fi / Chill",
        "items": [
            {"title": "Hurt – NewJeans", "url": "https://www.youtube.com/results?search_query=hurt+newjeans", "btn_label": "เปิดลิงก์", "benefit": "ชิล"},
            {"title": "Attention – NewJeans", "url": "https://www.youtube.com/results?search_query=attention+newjeans", "btn_label": "เปิดลิงก์", "benefit": "สดใส"},
            {"title": "Through the Night – IU", "url": "https://www.youtube.com/results?search_query=through+the+night+iu", "btn_label": "เปิดลิงก์", "benefit": "ละมุน"},
            {"title": "Love Poem – IU", "url": "https://www.youtube.com/results?search_query=love+poem+iu", "btn_label": "เปิดลิงก์", "benefit": "อบอุ่น"},
            {"title": "Only – Lee Hi", "url": "https://www.youtube.com/results?search_query=only+lee+hi", "btn_label": "เปิดลิงก์", "benefit": "ชิล"},
            {"title": "Eight – IU", "url": "https://www.youtube.com/results?search_query=eight+iu", "btn_label": "เปิดลิงก์", "benefit": "ชิล"},
            {"title": "Love Dive (chill ver) – IVE", "url": "https://www.youtube.com/results?search_query=love+dive+ive+chill", "btn_label": "เปิดลิงก์", "benefit": "ชิลเวอร์"},
            {"title": "Polaroid Love – Enhypen", "url": "https://www.youtube.com/results?search_query=polaroid+love+enhypen", "btn_label": "เปิดลิงก์", "benefit": "น่ารัก"},
            {"title": "Instagram – DEAN", "url": "https://www.youtube.com/results?search_query=instagram+dean", "btn_label": "เปิดลิงก์", "benefit": "ชิล"},
            {"title": "11:11 – Taeyeon", "url": "https://www.youtube.com/results?search_query=11:11+taeyeon", "btn_label": "เปิดลิงก์", "benefit": "ละมุน"},
            {"title": "People – Agust D", "url": "https://www.youtube.com/results?search_query=people+agust+d", "btn_label": "เปิดลิงก์", "benefit": "ชิล"},
            {"title": "Ending Scene – IU", "url": "https://www.youtube.com/results?search_query=ending+scene+iu", "btn_label": "เปิดลิงก์", "benefit": "อิน"},
            {"title": "Bambi – Baekhyun", "url": "https://www.youtube.com/results?search_query=bambi+baekhyun", "btn_label": "เปิดลิงก์", "benefit": "ละมุน"},
            {"title": "Slow Down – STAYC", "url": "https://www.youtube.com/results?search_query=slow+down+stayc", "btn_label": "เปิดลิงก์", "benefit": "ชิล"},
            {"title": "Palette – IU", "url": "https://www.youtube.com/results?search_query=palette+iu", "btn_label": "เปิดลิงก์", "benefit": "ฟีลดี"},
            {"title": "Blue – Taeyeon", "url": "https://www.youtube.com/results?search_query=blue+taeyeon", "btn_label": "เปิดลิงก์", "benefit": "ชิล"},
            {"title": "Nap of a Star – TXT", "url": "https://www.youtube.com/results?search_query=nap+of+a+star+txt", "btn_label": "เปิดลิงก์", "benefit": "ดรีมมี่"},
            {"title": "Eyes, Nose, Lips – Taeyang", "url": "https://www.youtube.com/results?search_query=eyes+nose+lips+taeyang", "btn_label": "เปิดลิงก์", "benefit": "คลาสสิก"},
            {"title": "Stay With Me – Chanyeol & Punch", "url": "https://www.youtube.com/results?search_query=stay+with+me+chanyeol+punch", "btn_label": "เปิดลิงก์", "benefit": "OST ชิล"},
            {"title": "River Flows in You – Yiruma", "url": "https://www.youtube.com/results?search_query=river+flows+in+you+yiruma", "btn_label": "เปิดลิงก์", "benefit": "เปียโนชิล"},
        ],
    },

    "weight_fullbody": {
        "title": "🏋️‍♂️ เวท: Full Body + Burn",
        "items": [
            {"title": "Pamela Reif – 10 Min Full Body Workout", "url": "https://www.youtube.com/results?search_query=pamela+reif+10+min+full+body", "btn_label": "ดูคลิป", "benefit": "Full body เผาผลาญ"},
            {"title": "Chloe Ting – 15 Min Full Body Burn", "url": "https://www.youtube.com/results?search_query=chloe+ting+15+min+full+body", "btn_label": "ดูคลิป", "benefit": "เบิร์นทั้งตัว"},
            {"title": "MadFit – 20 Min Full Body Workout", "url": "https://www.youtube.com/results?search_query=madfit+20+min+full+body", "btn_label": "ดูคลิป", "benefit": "ครบทั้งตัว"},
            {"title": "Emi Wong – 15 Min Full Body Fat Burn", "url": "https://www.youtube.com/results?search_query=emi+wong+15+min+full+body", "btn_label": "ดูคลิป", "benefit": "เผาผลาญไว"},
            {"title": "growwithjo – 20 Min Full Body Workout", "url": "https://www.youtube.com/results?search_query=growwithjo+20+min+full+body", "btn_label": "ดูคลิป", "benefit": "สนุก ทำตามง่าย"},
        ],
    },
    "weight_legs": {
        "title": "🍑 เวท: Legs + Glutes",
        "items": [
            {"title": "Pamela Reif – Booty Workout", "url": "https://www.youtube.com/results?search_query=pamela+reif+booty+workout", "btn_label": "ดูคลิป", "benefit": "เน้นก้น"},
            {"title": "Chloe Ting – Leg Day Burn", "url": "https://www.youtube.com/results?search_query=chloe+ting+leg+workout", "btn_label": "ดูคลิป", "benefit": "ขาเดย์"},
            {"title": "MadFit – 15 Min Booty Workout", "url": "https://www.youtube.com/results?search_query=madfit+booty+workout", "btn_label": "ดูคลิป", "benefit": "ก้น+ขา"},
            {"title": "Emi Wong – Thigh Slim Workout", "url": "https://www.youtube.com/results?search_query=emi+wong+thigh+workout", "btn_label": "ดูคลิป", "benefit": "เน้นต้นขา"},
            {"title": "Lilly Sabri – Leg Sculpt", "url": "https://www.youtube.com/results?search_query=lilly+sabri+leg+workout", "btn_label": "ดูคลิป", "benefit": "ปั้นขา"},
        ],
    },
    "weight_arms": {
        "title": "💪 เวท: Arms + Upper Body",
        "items": [
            {"title": "Pamela Reif – Arm Workout", "url": "https://www.youtube.com/results?search_query=pamela+reif+arm+workout", "btn_label": "ดูคลิป", "benefit": "แขนเฟิร์ม"},
            {"title": "Chloe Ting – Slim Arms Workout", "url": "https://www.youtube.com/results?search_query=chloe+ting+arm+workout", "btn_label": "ดูคลิป", "benefit": "แขนเรียว"},
            {"title": "MadFit – 10 Min Arm Workout", "url": "https://www.youtube.com/results?search_query=madfit+10+min+arms", "btn_label": "ดูคลิป", "benefit": "สั้นแต่โดน"},
            {"title": "Emi Wong – Upper Body Burn", "url": "https://www.youtube.com/results?search_query=emi+wong+upper+body", "btn_label": "ดูคลิป", "benefit": "บนล้วน"},
            {"title": "Lilly Sabri – Toned Arms", "url": "https://www.youtube.com/results?search_query=lilly+sabri+arms", "btn_label": "ดูคลิป", "benefit": "กระชับแขน"},
        ],
    },
    "weight_abs": {
        "title": "🔥 เวท: Abs + Core",
        "items": [
            {"title": "Pamela Reif – 10 Min Abs", "url": "https://www.youtube.com/results?search_query=pamela+reif+10+min+abs", "btn_label": "ดูคลิป", "benefit": "หน้าท้อง"},
            {"title": "Chloe Ting – Abs Workout", "url": "https://www.youtube.com/results?search_query=chloe+ting+abs", "btn_label": "ดูคลิป", "benefit": "หน้าท้อง"},
            {"title": "MadFit – Ab Burn", "url": "https://www.youtube.com/results?search_query=madfit+abs", "btn_label": "ดูคลิป", "benefit": "เบิร์นแกนกลาง"},
            {"title": "Emi Wong – Belly Fat Burn", "url": "https://www.youtube.com/results?search_query=emi+wong+belly+fat", "btn_label": "ดูคลิป", "benefit": "หน้าท้อง"},
            {"title": "Lilly Sabri – Core Sculpt", "url": "https://www.youtube.com/results?search_query=lilly+sabri+abs", "btn_label": "ดูคลิป", "benefit": "แกนกลาง"},
        ],
    },
    "weight_beginner": {
        "title": "🏠 เวท: Bodyweight / Beginner",
        "items": [
            {"title": "Pamela Reif – Beginner Workout", "url": "https://www.youtube.com/results?search_query=pamela+reif+beginner", "btn_label": "ดูคลิป", "benefit": "เริ่มต้น"},
            {"title": "Chloe Ting – Beginner Workout", "url": "https://www.youtube.com/results?search_query=chloe+ting+beginner", "btn_label": "ดูคลิป", "benefit": "เริ่มต้น"},
            {"title": "MadFit – Beginner Full Body", "url": "https://www.youtube.com/results?search_query=madfit+beginner", "btn_label": "ดูคลิป", "benefit": "ง่าย"},
            {"title": "Emi Wong – Easy Workout", "url": "https://www.youtube.com/results?search_query=emi+wong+beginner", "btn_label": "ดูคลิป", "benefit": "ง่าย"},
            {"title": "growwithjo – Low Impact Workout", "url": "https://www.youtube.com/results?search_query=growwithjo+low+impact", "btn_label": "ดูคลิป", "benefit": "แรงกระแทกต่ำ"},
        ],
    },
    "weight_dumbbell": {
        "title": "🏋️ เวท: Dumbbell / Home Weight",
        "items": [
            {"title": "Caroline Girvan – Dumbbell Workout", "url": "https://www.youtube.com/results?search_query=caroline+girvan+dumbbell", "btn_label": "ดูคลิป", "benefit": "ดัมเบล"},
            {"title": "Pamela Reif – Dumbbell Workout", "url": "https://www.youtube.com/results?search_query=pamela+reif+dumbbell", "btn_label": "ดูคลิป", "benefit": "ดัมเบล"},
            {"title": "MadFit – Dumbbell Arms", "url": "https://www.youtube.com/results?search_query=madfit+dumbbell+arms", "btn_label": "ดูคลิป", "benefit": "แขนดัมเบล"},
            {"title": "Emi Wong – Dumbbell Full Body", "url": "https://www.youtube.com/results?search_query=emi+wong+dumbbell", "btn_label": "ดูคลิป", "benefit": "ดัมเบลทั้งตัว"},
            {"title": "Lilly Sabri – Dumbbell Burn", "url": "https://www.youtube.com/results?search_query=lilly+sabri+dumbbell", "btn_label": "ดูคลิป", "benefit": "ดัมเบลเบิร์น"},
        ],
    },
    "weight_hiit": {
        "title": "⚡ เวท: HIIT + Strength",
        "items": [
            {"title": "Chloe Ting – HIIT Workout", "url": "https://www.youtube.com/results?search_query=chloe+ting+hiit", "btn_label": "ดูคลิป", "benefit": "HIIT"},
            {"title": "Pamela Reif – HIIT Burn", "url": "https://www.youtube.com/results?search_query=pamela+reif+hiit", "btn_label": "ดูคลิป", "benefit": "HIIT เบิร์น"},
            {"title": "MadFit – HIIT Full Body", "url": "https://www.youtube.com/results?search_query=madfit+hiit", "btn_label": "ดูคลิป", "benefit": "HIIT ทั้งตัว"},
            {"title": "Emi Wong – HIIT Workout", "url": "https://www.youtube.com/results?search_query=emi+wong+hiit", "btn_label": "ดูคลิป", "benefit": "HIIT"},
            {"title": "growwithjo – HIIT Burn", "url": "https://www.youtube.com/results?search_query=growwithjo+hiit", "btn_label": "ดูคลิป", "benefit": "HIIT สนุก"},
        ],
    },
    "weight_stretch": {
        "title": "🧘 เวท: Stretch + Recovery",
        "items": [
            {"title": "Pamela Reif – Stretch Routine", "url": "https://www.youtube.com/results?search_query=pamela+reif+stretch", "btn_label": "ดูคลิป", "benefit": "ยืดเหยียด"},
            {"title": "MadFit – Cool Down Stretch", "url": "https://www.youtube.com/results?search_query=madfit+stretch", "btn_label": "ดูคลิป", "benefit": "คูลดาวน์"},
            {"title": "Emi Wong – Stretch Routine", "url": "https://www.youtube.com/results?search_query=emi+wong+stretch", "btn_label": "ดูคลิป", "benefit": "ยืดเหยียด"},
            {"title": "Yoga With Adriene – Relax Stretch", "url": "https://www.youtube.com/results?search_query=yoga+with+adriene+stretch", "btn_label": "ดูคลิป", "benefit": "ผ่อนคลาย"},
            {"title": "Lilly Sabri – Recovery Stretch", "url": "https://www.youtube.com/results?search_query=lilly+sabri+stretch", "btn_label": "ดูคลิป", "benefit": "ฟื้นฟู"},
        ],
    },
    "weight_challenge": {
        "title": "🔥 เวท: Challenge / Program",
        "items": [
            {"title": "Chloe Ting – 2 Weeks Shred", "url": "https://www.youtube.com/results?search_query=chloe+ting+2+weeks+shred", "btn_label": "ดูคลิป", "benefit": "โปรแกรม"},
            {"title": "Pamela Reif – Workout Program", "url": "https://www.youtube.com/results?search_query=pamela+reif+program", "btn_label": "ดูคลิป", "benefit": "โปรแกรม"},
            {"title": "MadFit – 30 Days Challenge", "url": "https://www.youtube.com/results?search_query=madfit+30+day+challenge", "btn_label": "ดูคลิป", "benefit": "ชาเลนจ์"},
            {"title": "Emi Wong – 7 Days Burn", "url": "https://www.youtube.com/results?search_query=emi+wong+7+day", "btn_label": "ดูคลิป", "benefit": "7 วัน"},
            {"title": "growwithjo – Weekly Program", "url": "https://www.youtube.com/results?search_query=growwithjo+program", "btn_label": "ดูคลิป", "benefit": "รายสัปดาห์"},
        ],
    },
    "weight_bonus": {
        "title": "💯 เวท: Extra Bonus",
        "items": [
            {"title": "Fitness Marshall – Strength Dance", "url": "https://www.youtube.com/results?search_query=fitness+marshall+strength", "btn_label": "ดูคลิป", "benefit": "เต้น+แรง"},
            {"title": "Popsugar Fitness – Strength Workout", "url": "https://www.youtube.com/results?search_query=popsugar+strength", "btn_label": "ดูคลิป", "benefit": "แรง"},
            {"title": "Blogilates – Toned Workout", "url": "https://www.youtube.com/results?search_query=blogilates+toned", "btn_label": "ดูคลิป", "benefit": "กระชับ"},
            {"title": "Natacha Oceane – Home Strength", "url": "https://www.youtube.com/results?search_query=natacha+oceane+home+workout", "btn_label": "ดูคลิป", "benefit": "ที่บ้าน"},
            {"title": "Pamela Reif – Full Body Program", "url": "https://www.youtube.com/results?search_query=pamela+reif+full+body+program", "btn_label": "ดูคลิป", "benefit": "โปรแกรมทั้งตัว"},
        ],
    },

    "cardio_dance": {
        "title": "💃 คาร์ดิโอ: Dance Workout",
        "items": [
            {"title": "Fitness Marshall – Dance Cardio", "url": "https://www.youtube.com/results?search_query=fitness+marshall+dance+cardio", "btn_label": "ดูคลิป", "benefit": "เต้นสนุก"},
            {"title": "MadFit – Dance Party Workout", "url": "https://www.youtube.com/results?search_query=madfit+dance+workout", "btn_label": "ดูคลิป", "benefit": "ปาร์ตี้แดนซ์"},
            {"title": "growwithjo – Dance Cardio", "url": "https://www.youtube.com/results?search_query=growwithjo+dance+cardio", "btn_label": "ดูคลิป", "benefit": "สนุก ทำตามง่าย"},
            {"title": "Pamela Reif – Dance Workout", "url": "https://www.youtube.com/results?search_query=pamela+reif+dance", "btn_label": "ดูคลิป", "benefit": "เต้น"},
            {"title": "K-POP Dance Workout", "url": "https://www.youtube.com/results?search_query=kpop+dance+workout", "btn_label": "ดูคลิป", "benefit": "K-POP"},
        ],
    },
    "cardio_hiit": {
        "title": "🔥 คาร์ดิโอ: HIIT Cardio",
        "items": [
            {"title": "Chloe Ting – HIIT Cardio", "url": "https://www.youtube.com/results?search_query=chloe+ting+hiit+cardio", "btn_label": "ดูคลิป", "benefit": "HIIT"},
            {"title": "Pamela Reif – HIIT Cardio", "url": "https://www.youtube.com/results?search_query=pamela+reif+hiit+cardio", "btn_label": "ดูคลิป", "benefit": "HIIT"},
            {"title": "MadFit – Cardio Burn", "url": "https://www.youtube.com/results?search_query=madfit+cardio", "btn_label": "ดูคลิป", "benefit": "เบิร์น"},
            {"title": "Emi Wong – Fat Burn Cardio", "url": "https://www.youtube.com/results?search_query=emi+wong+cardio", "btn_label": "ดูคลิป", "benefit": "เผาผลาญ"},
            {"title": "growwithjo – No Jump Cardio", "url": "https://www.youtube.com/results?search_query=growwithjo+no+jump", "btn_label": "ดูคลิป", "benefit": "ไม่กระโดด"},
        ],
    },
    "cardio_lowimpact": {
        "title": "🚶 คาร์ดิโอ: Low Impact / Beginner",
        "items": [
            {"title": "growwithjo – Walk at Home", "url": "https://www.youtube.com/results?search_query=growwithjo+walk+at+home", "btn_label": "ดูคลิป", "benefit": "เดินในบ้าน"},
            {"title": "MadFit – Low Impact Cardio", "url": "https://www.youtube.com/results?search_query=madfit+low+impact", "btn_label": "ดูคลิป", "benefit": "แรงกระแทกต่ำ"},
            {"title": "Pamela Reif – Beginner Cardio", "url": "https://www.youtube.com/results?search_query=pamela+reif+beginner+cardio", "btn_label": "ดูคลิป", "benefit": "เริ่มต้น"},
            {"title": "Emi Wong – Easy Cardio", "url": "https://www.youtube.com/results?search_query=emi+wong+easy+cardio", "btn_label": "ดูคลิป", "benefit": "ง่าย"},
            {"title": "Walk Workout Gen Z", "url": "https://www.youtube.com/results?search_query=walk+workout+music", "btn_label": "ดูคลิป", "benefit": "เดินชิล"},
        ],
    },
    "cardio_intense": {
        "title": "🏃 คาร์ดิโอ: Intense Burn",
        "items": [
            {"title": "Chloe Ting – Fat Burn Cardio", "url": "https://www.youtube.com/results?search_query=chloe+ting+fat+burn", "btn_label": "ดูคลิป", "benefit": "หนัก"},
            {"title": "Pamela Reif – Cardio Burn", "url": "https://www.youtube.com/results?search_query=pamela+reif+cardio+burn", "btn_label": "ดูคลิป", "benefit": "หนัก"},
            {"title": "MadFit – Sweat Workout", "url": "https://www.youtube.com/results?search_query=madfit+sweat+workout", "btn_label": "ดูคลิป", "benefit": "เหงื่อแตก"},
            {"title": "Emi Wong – Burn 300 Cal", "url": "https://www.youtube.com/results?search_query=emi+wong+300+cal", "btn_label": "ดูคลิป", "benefit": "เบิร์น"},
            {"title": "growwithjo – Sweat Cardio", "url": "https://www.youtube.com/results?search_query=growwithjo+sweat", "btn_label": "ดูคลิป", "benefit": "เหงื่อแตก"},
        ],
    },
    "cardio_musicdance": {
        "title": "🎵 คาร์ดิโอ: Music + Dance",
        "items": [
            {"title": "TikTok Dance Workout", "url": "https://www.youtube.com/results?search_query=tiktok+dance+workout", "btn_label": "ดูคลิป", "benefit": "เต้นติ้กต้อก"},
            {"title": "KPOP HIIT Dance", "url": "https://www.youtube.com/results?search_query=kpop+hiit+dance", "btn_label": "ดูคลิป", "benefit": "K-POP"},
            {"title": "Zumba Dance Workout", "url": "https://www.youtube.com/results?search_query=zumba+workout", "btn_label": "ดูคลิป", "benefit": "ซุมบ้า"},
            {"title": "Pop Dance Workout", "url": "https://www.youtube.com/results?search_query=pop+dance+workout", "btn_label": "ดูคลิป", "benefit": "ป๊อปแดนซ์"},
            {"title": "Afro Dance Workout", "url": "https://www.youtube.com/results?search_query=afro+dance+workout", "btn_label": "ดูคลิป", "benefit": "แอฟโฟร"},
        ],
    },
    "cardio_express": {
        "title": "⚡ คาร์ดิโอ: Express 5–10 นาที",
        "items": [
            {"title": "Pamela Reif – 5 Min Cardio", "url": "https://www.youtube.com/results?search_query=pamela+reif+5+min+cardio", "btn_label": "ดูคลิป", "benefit": "สั้น"},
            {"title": "Chloe Ting – 10 Min Burn", "url": "https://www.youtube.com/results?search_query=chloe+ting+10+min+burn", "btn_label": "ดูคลิป", "benefit": "10 นาที"},
            {"title": "MadFit – 10 Min Cardio", "url": "https://www.youtube.com/results?search_query=madfit+10+min+cardio", "btn_label": "ดูคลิป", "benefit": "10 นาที"},
            {"title": "Emi Wong – Quick Burn", "url": "https://www.youtube.com/results?search_query=emi+wong+quick+workout", "btn_label": "ดูคลิป", "benefit": "เร็ว"},
            {"title": "growwithjo – Quick Cardio", "url": "https://www.youtube.com/results?search_query=growwithjo+quick+cardio", "btn_label": "ดูคลิป", "benefit": "เร็ว"},
        ],
    },
    "cardio_bonus": {
        "title": "💯 คาร์ดิโอ: Bonus Cardio",
        "items": [
            {"title": "Popsugar Fitness – Dance Cardio", "url": "https://www.youtube.com/results?search_query=popsugar+dance+cardio", "btn_label": "ดูคลิป", "benefit": "เต้น"},
            {"title": "Blogilates – Cardio Burn", "url": "https://www.youtube.com/results?search_query=blogilates+cardio", "btn_label": "ดูคลิป", "benefit": "เบิร์น"},
            {"title": "Fitness Blender – Cardio", "url": "https://www.youtube.com/results?search_query=fitness+blender+cardio", "btn_label": "ดูคลิป", "benefit": "คาร์ดิโอ"},
            {"title": "Sydney Cummings – Cardio", "url": "https://www.youtube.com/results?search_query=sydney+cummings+cardio", "btn_label": "ดูคลิป", "benefit": "คาร์ดิโอ"},
            {"title": "Natacha Oceane – Cardio", "url": "https://www.youtube.com/results?search_query=natacha+oceane+cardio", "btn_label": "ดูคลิป", "benefit": "คาร์ดิโอ"},
        ],
    },
    "cardio_challenge": {
        "title": "🎯 คาร์ดิโอ: Challenge / Program",
        "items": [
            {"title": "Chloe Ting – 2 Week Shred Cardio", "url": "https://www.youtube.com/results?search_query=chloe+ting+shred+cardio", "btn_label": "ดูคลิป", "benefit": "โปรแกรม"},
            {"title": "Pamela Reif – Weekly Cardio Plan", "url": "https://www.youtube.com/results?search_query=pamela+reif+cardio+program", "btn_label": "ดูคลิป", "benefit": "รายสัปดาห์"},
            {"title": "MadFit – 30 Days Burn", "url": "https://www.youtube.com/results?search_query=madfit+30+day+burn", "btn_label": "ดูคลิป", "benefit": "30 วัน"},
            {"title": "Emi Wong – Fat Burn Program", "url": "https://www.youtube.com/results?search_query=emi+wong+fat+burn+program", "btn_label": "ดูคลิป", "benefit": "โปรแกรม"},
            {"title": "growwithjo – Walk Challenge", "url": "https://www.youtube.com/results?search_query=growwithjo+challenge", "btn_label": "ดูคลิป", "benefit": "ชาเลนจ์"},
        ],
    },
    "cardio_superfun": {
        "title": "🔥 คาร์ดิโอ: Super Fun Gen Z",
        "items": [
            {"title": "KPOP Dance Cardio", "url": "https://www.youtube.com/results?search_query=kpop+dance+cardio+workout", "btn_label": "ดูคลิป", "benefit": "K-POP"},
            {"title": "TikTok HIIT Workout", "url": "https://www.youtube.com/results?search_query=tiktok+hiit+workout", "btn_label": "ดูคลิป", "benefit": "ติ้กต้อก"},
            {"title": "Anime Workout Cardio", "url": "https://www.youtube.com/results?search_query=anime+workout+cardio", "btn_label": "ดูคลิป", "benefit": "อนิเมะ"},
            {"title": "Game Workout Fitness", "url": "https://www.youtube.com/results?search_query=game+workout+fitness", "btn_label": "ดูคลิป", "benefit": "เกมฟีล"},
            {"title": "VR Style Workout", "url": "https://www.youtube.com/results?search_query=vr+fitness+workout", "btn_label": "ดูคลิป", "benefit": "VR"},
        ],
    },
    "cardio_funburn": {
        "title": "🎉 คาร์ดิโอ: Fun Burn",
        "items": [
            {"title": "Just Dance Workout", "url": "https://www.youtube.com/results?search_query=just+dance+workout", "btn_label": "ดูคลิป", "benefit": "Just Dance"},
            {"title": "Party Dance Cardio", "url": "https://www.youtube.com/results?search_query=party+dance+cardio", "btn_label": "ดูคลิป", "benefit": "ปาร์ตี้แดนซ์"},
        ],
    },
}

MEDIA_GROUPS = {
    "root": [
        ("thai_chill", "🇹🇭 เพลงไทย"),
        ("inter_chill", "🌍 เพลงสากล"),
        ("kpop_chill", "🇰🇷 K-POP"),
        ("weight", "🏋️ เวท"),
        ("cardio", "🏃 คาร์ดิโอ"),
    ],
    "weight": [
        ("weight_fullbody", "🔥 Full Body"),
        ("weight_legs", "🍑 Legs/Glutes"),
        ("weight_arms", "💪 Arms/Upper"),
        ("weight_abs", "🧠 Abs/Core"),
        ("weight_beginner", "🏠 Beginner"),
        ("weight_dumbbell", "🏋️ Dumbbell"),
        ("weight_hiit", "⚡ HIIT+Strength"),
        ("weight_stretch", "🧘 Stretch"),
        ("weight_challenge", "🎯 Program"),
        ("weight_bonus", "💯 Bonus"),
    ],
    "cardio": [
        ("cardio_dance", "💃 Dance"),
        ("cardio_hiit", "🔥 HIIT"),
        ("cardio_lowimpact", "🚶 Low Impact"),
        ("cardio_intense", "🏃 Intense"),
        ("cardio_musicdance", "🎵 Music+Dance"),
        ("cardio_express", "⚡ 5–10 นาที"),
        ("cardio_bonus", "💯 Bonus"),
        ("cardio_challenge", "🎯 Program"),
        ("cardio_superfun", "🔥 Gen Z Fun"),
        ("cardio_funburn", "🎉 Fun Burn"),
    ],
}


def verify_line_signature(body: bytes, signature: str):
    mac = hmac.new(LINE_CHANNEL_SECRET.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def parse_hhmm(text: str) -> str | None:
    t = text.strip()
    if len(t) != 5 or t[2] != ":":
        return None
    hh = t[:2]
    mm = t[3:]
    if not (hh.isdigit() and mm.isdigit()):
        return None
    h = int(hh)
    m = int(mm)
    if h < 0 or h > 23 or m < 0 or m > 59:
        return None
    return f"{h:02d}:{m:02d}"


def journal_show_by_idx(reply_token: str, user_id: str, idx: int):
    idx = max(0, min(idx, len(JOURNALS) - 1))
    title, bullets = JOURNALS[idx]
    line_reply(reply_token, [journal_poster_flex(title, bullets)])


def parse_postback_data(data: str) -> dict:
    qs = parse_qs(data, keep_blank_values=True)
    out = {}
    for k, v in qs.items():
        out[k] = v[0] if v else ""
    return out


def quickreply_from_pairs(pairs: list[tuple[str, str]]):
    items = []
    for data, label in pairs[:13]:
        items.append({"type": "action", "action": {"type": "postback", "label": label, "data": data}})
    return {"items": items}


def show_media_root_menu(reply_token: str):
    pairs = []
    for cat_or_group, label in MEDIA_GROUPS["root"]:
        if cat_or_group in ("weight", "cardio"):
            pairs.append((f"action=media_group&group={cat_or_group}", label))
        else:
            pairs.append((f"action=media_cat&cat={cat_or_group}&page=0", label))

    line_reply(reply_token, [{
        "type": "text",
        "text": "เลือกหัวข้อที่อยากฟัง/ดูได้เลย 🎧",
        "quickReply": quickreply_from_pairs(pairs)
    }])


def show_media_group_menu(reply_token: str, group: str):
    if group not in MEDIA_GROUPS:
        show_media_root_menu(reply_token)
        return

    pairs = []
    for cat_id, label in MEDIA_GROUPS[group]:
        pairs.append((f"action=media_cat&cat={cat_id}&page=0", label))
    pairs.append(("action=media", "🔙 กลับเมนู"))

    line_reply(reply_token, [{
        "type": "text",
        "text": f"เลือกหมวดย่อย ({group}) ได้เลย 👇",
        "quickReply": quickreply_from_pairs(pairs)
    }])


def show_media_category(reply_token: str, cat: str, page: int):
    if cat not in MEDIA_CATEGORIES:
        show_media_root_menu(reply_token)
        return

    title = MEDIA_CATEGORIES[cat]["title"]
    items = MEDIA_CATEGORIES[cat]["items"]

    total_pages = max(1, (len(items) + MEDIA_PAGE_SIZE - 1) // MEDIA_PAGE_SIZE)
    page = max(0, min(int(page), total_pages - 1))

    start = page * MEDIA_PAGE_SIZE
    end = start + MEDIA_PAGE_SIZE
    page_items = items[start:end]

    footer_buttons = []

    if total_pages > 1 and page < total_pages - 1:
        footer_buttons.append({
            "type": "button",
            "style": "primary",
            "height": "sm",
            "action": {
                "type": "postback",
                "label": "ถัดไป",
                "data": f"action=media_cat&cat={cat}&page={page+1}"
            }
        })
    elif total_pages > 1:
        footer_buttons.append({
            "type": "button",
            "style": "primary",
            "height": "sm",
            "action": {
                "type": "postback",
                "label": "เริ่มใหม่",
                "data": f"action=media_cat&cat={cat}&page=0"
            }
        })

    rand_page = 0 if total_pages <= 1 else random.randint(0, total_pages - 1)
    footer_buttons.append({
        "type": "button",
        "style": "secondary",
        "height": "sm",
        "action": {
            "type": "postback",
            "label": "สุ่ม",
            "data": f"action=media_cat&cat={cat}&page={rand_page}"
        }
    })

    header = media_poster_flex(
        f"{title} (หน้า {page + 1}/{total_pages})",
        ["กดดู/ฟังได้เลย", "กดถัดไปเพื่อดูรายการเพิ่ม", "กดกลับเมนูเพื่อเลือกหัวข้ออื่น"],
        footer_buttons
    )

    nav_pairs = []
    if total_pages > 1 and page > 0:
        nav_pairs.append((f"action=media_cat&cat={cat}&page={page-1}", "⬅️ ก่อนหน้า"))
    if total_pages > 1 and page < total_pages - 1:
        nav_pairs.append((f"action=media_cat&cat={cat}&page={page+1}", "ถัดไป ➡️"))

    back_group = None
    for g, cats in MEDIA_GROUPS.items():
        if g in ("root",):
            continue
        for c_id, _ in cats:
            if c_id == cat:
                back_group = g
                break
        if back_group:
            break

    if back_group:
        nav_pairs.append((f"action=media_group&group={back_group}", "🔙 หมวดย่อย"))
    nav_pairs.append(("action=media", "🏠 เมนูหลัก"))

    line_reply(reply_token, [
        header,
        media_carousel_flex(page_items),
        {"type": "text", "text": "เลื่อนดูรายการ แล้วกดปุ่มได้เลย 👇", "quickReply": quickreply_from_pairs(nav_pairs)}
    ])


@app.on_event("startup")
def on_startup():
    init_db()
    start_scheduler()


@app.get("/webhook")
def webhook_get():
    return {"ok": True, "note": "This endpoint accepts POST from LINE. GET is just a health check."}


@app.post("/webhook")
async def webhook(req: Request):
    body = await req.body()
    signature = req.headers.get("x-line-signature")
    if not signature or not verify_line_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = await req.json()
    events = data.get("events", [])

    for ev in events:
        user_id = ev.get("source", {}).get("userId")
        if not user_id:
            continue
        upsert_user(user_id)

        if ev["type"] == "postback":
            reply_token = ev["replyToken"]
            post_data = ev["postback"]["data"]
            pb = parse_postback_data(post_data)

            if post_data == "action=menu":
                line_reply(reply_token, [{"type": "text", "text": "กด Rich Menu ด้านล่างเพื่อเลือกฟังก์ชันนะ 😊"}])

            elif post_data == "action=diary":
                stats = get_diary_stats(user_id)
                set_mode(user_id, "diary_wait_text")
                line_reply(reply_token, [diary_prompt_flex(stats["level"])])

            elif post_data.startswith("score="):
                score = int(post_data.split("=")[1])
                set_mode(user_id, f"diary_wait_text_score:{score}")
                if score == 0:
                    line_reply(reply_token, [{"type": "text", "text": "โอเค ข้ามคะแนนได้เลย ✨\nพิมพ์เล่า ‘ความสุขวันนี้’ มาได้เลย"}])
                else:
                    line_reply(reply_token, [{"type": "text", "text": f"รับคะแนน {score}/5 แล้ว ✨\nพิมพ์เล่า ‘ความสุขวันนี้’ มาได้เลย"}])

            elif post_data == "action=todo":
                set_mode(user_id, None)
                line_reply(reply_token, [todo_menu_flex()])

            elif post_data == "todo=add":
                set_mode(user_id, "todo_wait_add")
                line_reply(reply_token, [{"type": "text", "text": "พิมพ์งานที่อยากเพิ่มได้เลย (1 บรรทัด = 1 งาน)\nตัวอย่าง: อ่านหนังสือ 30 นาที"}])

            elif post_data == "todo=list":
                set_mode(user_id, None)
                todos = list_todo(user_id)
                line_reply(reply_token, [todo_list_flex(todos)])

            elif post_data == "todo=clear_done":
                clear_done_todos(user_id)
                set_mode(user_id, None)
                line_reply(reply_token, [{"type": "text", "text": "ล้างงานที่เสร็จแล้วเรียบร้อย 🧹"}])

            elif post_data.startswith("todo_done="):
                todo_id = int(post_data.split("=")[1])
                mark_todo_done(user_id, todo_id)
                todos = list_todo(user_id)
                line_reply(reply_token, [{"type": "text", "text": "ติ๊กเสร็จแล้ว ✅ เก่งมาก"}, todo_list_flex(todos)])

            elif post_data == "action=heal":
                set_mode(user_id, "heal")
                line_reply(reply_token, [{
                    "type": "text",
                    "text": "ที่พักฮีลใจ 🤍\nพิมพ์มาได้เลย เราจะรับฟังนะ\nถ้ารู้สึกไม่ปลอดภัย โทร 1323 ได้ทันที"
                }])

            elif post_data == "action=sleep":
                s = get_sleep_setting(user_id)
                set_mode(user_id, None)
                line_reply(reply_token, [sleep_menu_flex(s["bedtime"], s["waketime"], s["enabled"])])

            elif post_data == "sleep=set_bed":
                set_mode(user_id, "sleep_wait_bed")
                line_reply(reply_token, [{"type": "text", "text": "พิมพ์เวลาเข้านอนรูปแบบ HH:MM เช่น 23:00"}])

            elif post_data == "sleep=set_wake":
                set_mode(user_id, "sleep_wait_wake")
                line_reply(reply_token, [{"type": "text", "text": "พิมพ์เวลาตื่นรูปแบบ HH:MM เช่น 07:00"}])

            elif post_data == "sleep=toggle":
                s = get_sleep_setting(user_id)
                new_enabled = 0 if int(s["enabled"]) == 1 else 1
                set_sleep(user_id, s["bedtime"], s["waketime"], new_enabled)
                sync_user(user_id)
                s2 = get_sleep_setting(user_id)
                line_reply(reply_token, [sleep_menu_flex(s2["bedtime"], s2["waketime"], s2["enabled"])])

            elif post_data == "action=journal":
                set_mode(user_id, None)
                idx = get_journal_idx(user_id)
                journal_show_by_idx(reply_token, user_id, idx)

            elif post_data == "journal=next":
                set_mode(user_id, None)
                idx = get_journal_idx(user_id)
                idx = (idx + 1) % len(JOURNALS)
                set_journal_idx(user_id, idx)
                journal_show_by_idx(reply_token, user_id, idx)

            elif post_data == "journal=random":
                set_mode(user_id, None)
                idx = random.randint(0, len(JOURNALS) - 1)
                set_journal_idx(user_id, idx)
                journal_show_by_idx(reply_token, user_id, idx)

            elif post_data == "action=media":
                set_mode(user_id, None)
                show_media_root_menu(reply_token)

            elif pb.get("action") == "media_group":
                set_mode(user_id, None)
                group = pb.get("group", "root")
                show_media_group_menu(reply_token, group)

            elif pb.get("action") == "media_cat":
                set_mode(user_id, None)
                cat = pb.get("cat", "")
                try:
                    page = int(pb.get("page", "0"))
                except:
                    page = 0
                show_media_category(reply_token, cat, page)

        elif ev["type"] == "message" and ev["message"]["type"] == "text":
            reply_token = ev["replyToken"]
            text = ev["message"]["text"].strip()
            mode = get_mode(user_id)

            if mode == "todo_wait_add":
                add_todo(user_id, text)
                set_mode(user_id, None)
                todos = list_todo(user_id)
                line_reply(reply_token, [{"type": "text", "text": "เพิ่มงานแล้ว ✅"}, todo_list_flex(todos)])

            elif mode and mode.startswith("diary_wait_text_score:"):
                score = int(mode.split(":")[1])
                score_val = None if score == 0 else score
                add_diary(user_id, text, score_val)
                set_mode(user_id, None)
                stats = get_diary_stats(user_id)
                line_reply(reply_token, [tree_progress_flex(stats)])

            elif mode == "diary_wait_text":
                add_diary(user_id, text, None)
                set_mode(user_id, None)
                stats = get_diary_stats(user_id)
                line_reply(reply_token, [tree_progress_flex(stats)])

            elif mode == "heal":
                ai_text = heal_reply(text)
                line_reply(reply_token, [{"type": "text", "text": ai_text}])

            elif mode == "sleep_wait_bed":
                hhmm = parse_hhmm(text)
                if not hhmm:
                    line_reply(reply_token, [{"type": "text", "text": "รูปแบบเวลาไม่ถูกนะ ต้องเป็น HH:MM เช่น 23:00"}])
                else:
                    s = get_sleep_setting(user_id)
                    set_sleep(user_id, hhmm, s["waketime"], 1)
                    sync_user(user_id)
                    set_mode(user_id, None)
                    s2 = get_sleep_setting(user_id)
                    line_reply(reply_token, [{"type": "text", "text": f"ตั้งเวลาเข้านอนเป็น {hhmm} แล้ว ✅ (เปิดแจ้งเตือนให้แล้ว)"}, sleep_menu_flex(s2["bedtime"], s2["waketime"], s2["enabled"])])

            elif mode == "sleep_wait_wake":
                hhmm = parse_hhmm(text)
                if not hhmm:
                    line_reply(reply_token, [{"type": "text", "text": "รูปแบบเวลาไม่ถูกนะ ต้องเป็น HH:MM เช่น 07:00"}])
                else:
                    s = get_sleep_setting(user_id)
                    set_sleep(user_id, s["bedtime"], hhmm, 1)
                    sync_user(user_id)
                    set_mode(user_id, None)
                    s2 = get_sleep_setting(user_id)
                    line_reply(reply_token, [{"type": "text", "text": f"ตั้งเวลาตื่นเป็น {hhmm} แล้ว ✅ (เปิดแจ้งเตือนให้แล้ว)"}, sleep_menu_flex(s2["bedtime"], s2["waketime"], s2["enabled"])])

            else:
                line_reply(reply_token, [{"type": "text", "text": "กด Rich Menu ด้านล่างเพื่อเลือกฟังก์ชันนะ 😊"}])

    return {"ok": True}