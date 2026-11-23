# seed_data.py —— 產生「示範資料」（全部虛構）
# 執行方式：python seed_data.py
# 會「覆蓋」data/ 裡的資料，Demo 前跑一次就能回到乾淨的初始狀態
# 日期都以「今天」為基準計算，所以任何一天執行，配對與活動都能正常顯示

import os
from datetime import datetime, timedelta

from storage import (USERS_PATH, LOSTFOUND_PATH, TASKS_PATH, EVENTS_PATH, REPORTS_PATH, BLOCKS_PATH,
                     PROFILES_PATH, PINECONES_PATH, CHAT_DIR, save_data, save_thread, ensure_dirs)
import squirrel
from auth import make_salt, hash_password

DEMO_PASSWORD = "demo1234"   # 所有示範帳號共用的密碼


def day(offset):
    """回傳 今天 + offset 天 的日期字串"""
    return (datetime.now() + timedelta(days=offset)).strftime("%Y-%m-%d")


def hours(offset):
    """回傳 現在 + offset 小時 的時間字串"""
    return (datetime.now() + timedelta(hours=offset)).strftime("%Y-%m-%d %H:%M")


def make_user(nickname):
    """建立一個示範帳號"""
    salt = make_salt()
    return {"nickname": nickname, "salt": salt, "password_hash": hash_password(DEMO_PASSWORD, salt),
            "created_at": day(-5) + " 09:00"}


def main():
    """重設所有示範資料"""
    ensure_dirs()
    # 清掉舊的私訊檔
    for name in os.listdir(CHAT_DIR):
        if name.endswith(".json"):
            os.remove(os.path.join(CHAT_DIR, name))

    users = []
    for name in ["小宇", "小晴", "小安", "小凱", "阿明", "小美"]:
        users.append(make_user(name))
    save_data(USERS_PATH, users)

    items = [
        {"id": 1, "kind": "遺失", "name": "黑色保溫水壺", "category": "雨傘水壺", "location": "圖書館",
         "date": day(-1), "description": "昨天下午在圖書館三樓自習區掉的，約 500ml。",
         "keywords": ["黑色", "保溫水壺", "水壺"], "owner": "小宇",
         "verify_questions": [], "verify_answers": [], "status": "尋找中", "created_at": day(-1) + " 18:20"},
        {"id": 2, "kind": "拾獲", "name": "黑色保溫水壺", "category": "雨傘水壺", "location": "圖書館",
         "date": day(-1), "description": "黑色、約 500ml，瓶身有貼紙。已交給圖書館一樓櫃台旁保管中。",
         "keywords": ["黑色", "水壺", "貼紙"], "owner": "小晴",
         "verify_questions": ["瓶身貼紙是什麼圖案？", "瓶蓋或瓶身有哪些刮痕或凹痕？"],
         "verify_answers": ["貓咪", "瓶蓋有一道刮痕"], "status": "尋找中", "created_at": day(-1) + " 20:10"},
        {"id": 3, "kind": "拾獲", "name": "藍色折疊傘", "category": "雨傘水壺", "location": "工程一館",
         "date": day(-3), "description": "放在工程一館一樓傘架很久沒人拿。",
         "keywords": ["藍色", "折疊傘", "傘"], "owner": "小凱",
         "verify_questions": ["傘柄是什麼顏色？", "傘套上有什麼特徵？"], "verify_answers": ["白色", "有破洞"],
         "status": "尋找中", "created_at": day(-3) + " 12:00"},
        {"id": 4, "kind": "遺失", "name": "白色無線耳機", "category": "3C電子", "location": "學生活動中心",
         "date": day(-2), "description": "白色充電盒，盒子上有一點刮痕。",
         "keywords": ["白色", "無線耳機", "耳機"], "owner": "小安",
         "verify_questions": [], "verify_answers": [], "status": "尋找中", "created_at": day(-2) + " 21:00"},
        {"id": 5, "kind": "拾獲", "name": "學生證", "category": "證件卡片", "location": "餐廳",
         "date": day(0), "description": "在餐廳桌上撿到，已拍照記錄，建議失主到總務處認領。",
         "keywords": ["學生證"], "owner": "小凱",
         "verify_questions": ["證件上的姓名第一個字？", "卡套是什麼顏色？"], "verify_answers": ["王", "透明"],
         "status": "尋找中", "created_at": hours(-2)},
        {"id": 6, "kind": "遺失", "name": "綠色雨傘", "category": "雨傘水壺", "location": "文學院",
         "date": day(-2), "description": "長柄傘，傘柄有一個松果吊飾。", "keywords": ["綠色", "雨傘", "傘"], "owner": "阿明",
         "verify_questions": [], "verify_answers": [], "status": "尋找中", "created_at": day(-2) + " 17:00"},
        {"id": 7, "kind": "拾獲", "name": "灰色計算機", "category": "3C電子", "location": "科學館",
         "date": day(-1), "description": "工程用計算機，在科學館二樓教室撿到。", "keywords": ["灰色", "計算機"], "owner": "小美",
         "verify_questions": ["背面貼了什麼？", "外盒是什麼顏色？"], "verify_answers": ["名字貼紙", "黑色"],
         "status": "尋找中", "created_at": day(-1) + " 11:00"},
        {"id": 8, "kind": "遺失", "name": "銀色鑰匙圈", "category": "鑰匙", "location": "宵夜街",
         "date": day(-4), "description": "三把鑰匙＋一個小熊吊飾。", "keywords": ["銀色", "鑰匙圈", "鑰匙"], "owner": "小凱",
         "verify_questions": [], "verify_answers": [], "status": "已尋回", "created_at": day(-4) + " 23:10"},
    ]
    save_data(LOSTFOUND_PATH, items)

    tasks = [
        {"id": 1, "type": "代拿代購", "title": "幫忙帶一杯飲料到圖書館", "description": "下午有課走不開，想請順路的同學幫忙帶一杯無糖綠茶。",
         "location": "圖書館", "deadline": day(1) + " 15:00", "reward": "請喝一杯飲料（雙方自行約定，平台不經手金流）",
         "slots": 1, "helpers": [], "keywords": ["代拿", "飲料"], "owner": "小安", "status": "招募中",
         "created_at": day(0) + " 10:00"},
        {"id": 2, "type": "揪人", "title": "週末羽球缺 2 人", "description": "程度不拘，場地已借好。",
         "location": "體育館", "deadline": day(3) + " 14:00", "reward": "",
         "slots": 2, "helpers": ["小宇"], "keywords": ["揪人", "羽球"], "owner": "小凱", "status": "招募中",
         "created_at": day(0) + " 11:00"},
        {"id": 3, "type": "代跑腿", "title": "幫領宿舍包裹", "description": "今天傍晚到，我在實驗室走不開。",
         "location": "宿舍", "deadline": hours(2), "reward": "請吃宵夜", "slots": 1, "helpers": [],
         "keywords": ["代跑腿", "包裹"], "owner": "小晴", "status": "招募中", "created_at": hours(-3)},
        {"id": 4, "type": "揪人", "title": "期末讀書會揪 3 人", "description": "一起讀統計學，互相出題。",
         "location": "管理學院", "deadline": day(2) + " 19:00", "reward": "", "slots": 3, "helpers": [],
         "keywords": ["揪人", "讀書會"], "owner": "阿明", "status": "招募中", "created_at": day(0) + " 08:00"},
        {"id": 5, "type": "日常求助", "title": "借一條 Type-C 充電線", "description": "手機快沒電，用 10 分鐘就還。",
         "location": "總圖書館", "deadline": hours(1), "reward": "請你一顆糖", "slots": 1, "helpers": [],
         "keywords": ["充電線"], "owner": "小美", "status": "招募中", "created_at": hours(-1)},
        {"id": 6, "type": "代拿代購", "title": "幫買宵夜鹹酥雞", "description": "已完成的示範任務。",
         "location": "宵夜街", "deadline": day(-1) + " 22:00", "reward": "分你一半", "slots": 1, "helpers": ["小宇"],
         "keywords": ["宵夜"], "owner": "小安", "status": "已完成", "created_at": day(-1) + " 20:00"},
    ]
    save_data(TASKS_PATH, tasks)

    events = [
        {"id": 1, "title": "（虛構）攝影社新生體驗", "org": "（虛構）示範攝影社", "category": "社團招生", "place": "學生活動中心",
         "start": day(4) + " 18:30", "end": day(4) + " 20:00", "description": "認識器材與拍攝基礎，歡迎新手，可以認識同好。",
         "tags": ["攝影", "新生", "社團"], "link": "", "owner": "小晴", "interested": ["小宇"], "created_at": day(-2) + " 09:00"},
        {"id": 2, "title": "（虛構）AI 入門工作坊", "org": "（虛構）示範資工系學會", "category": "學術講座", "place": "工程五館",
         "start": day(6) + " 14:00", "end": day(6) + " 16:00", "description": "用 Python 呼叫語言模型 API，帶筆電。",
         "tags": ["AI", "程式", "Python", "工作坊"], "link": "", "owner": "小安", "interested": [], "created_at": day(-1) + " 10:00"},
        {"id": 3, "title": "（虛構）中大湖淨湖志工", "org": "（虛構）示範服務社", "category": "志工服務", "place": "中大湖",
         "start": day(9) + " 09:00", "end": day(9) + " 12:00", "description": "一起整理湖邊環境，提供手套與早餐。",
         "tags": ["志工", "環境", "戶外"], "link": "", "owner": "小凱", "interested": [], "created_at": day(-1) + " 15:00"},
        {"id": 4, "title": "（虛構）系際籃球賽", "org": "（虛構）示範體育會", "category": "運動競賽", "place": "體育館",
         "start": day(-3) + " 18:00", "end": day(-3) + " 21:00", "description": "已結束的活動（用來測試「只看未結束」）。",
         "tags": ["籃球", "運動"], "link": "", "owner": "小凱", "interested": [], "created_at": day(-10) + " 15:00"},
    ]
    save_data(EVENTS_PATH, events)

    # 一個示範私訊：小宇 ↔ 小晴（水壺）
    thread = {
        "id": 1, "target_type": "item", "target_id": 2, "target_title": "黑色保溫水壺",
        "owner": "小晴", "peer": "小宇", "claim_answers": ["貓咪圖案", "瓶蓋有一道刮痕"], "verified": "未驗證",
        "meetup": None,
        "messages": [
            {"id": 1, "sender": "小宇", "text": "你好，這個水壺可能是我的，驗證問題我已經回答了。", "kind": "user",
             "created_at": day(0) + " 08:01"},
        ],
        "created_at": day(0) + " 08:00", "updated_at": day(0) + " 08:01",
    }
    save_thread(thread)

    # 每隻松鼠的造型與位置（last_seen 設成現在，Demo 時看起來都在線上）
    # 每個人：名字、毛色、擁有的衣服、穿搭、所在區域
    looks = [
        ["小宇", "栗棕", ["ncu_tee"], {"body": "ncu_tee"}, "gate"],
        ["小晴", "灰松", ["flower", "coffee"], {"head": "flower", "hand": "coffee"}, "library"],
        ["小安", "奶茶", ["bow"], {"face": "glasses", "head": "bow"}, "activity"],
        ["小凱", "巧克力", ["ncu_cap", "ncu_jersey"], {"head": "ncu_cap", "body": "ncu_jersey"}, "sports"],
        ["阿明", "橘紅", ["headphones", "guitar"], {"head": "headphones", "back": "guitar"}, "literature"],
        ["小美", "雪白", ["duck_hat", "book"], {"head": "duck_hat", "hand": "book"}, "library"],
    ]
    profiles = []
    for look in looks:
        p = squirrel.default_profile(look[0])
        p["fur"] = look[1]
        if look[1] not in p["owned_furs"]:
            p["owned_furs"].append(look[1])
        for item_id in look[2]:
            if item_id not in p["owned"]:
                p["owned"].append(item_id)
        for slot in look[3]:
            p["outfit"][slot] = look[3][slot]
        p["zone"] = look[4]
        p["visited_all"] = [look[4]]
        profiles.append(p)
    save_data(PROFILES_PATH, profiles)

    # 松果示範紀錄（讓 Demo 時可以直接逛商店買東西）
    ledger = []
    squirrel.add_pinecones(ledger, "小宇", 10, "完成任務", "task:6:小宇")
    squirrel.add_pinecones(ledger, "小宇", 150, "示範贈送", "seed:gift:小宇")
    squirrel.add_pinecones(ledger, "小宇", -100, "商店購買", "buy:小宇:ncu_tee")
    squirrel.add_pinecones(ledger, "小晴", 20, "物歸原主", "seed:return:1")
    squirrel.add_pinecones(ledger, "小晴", 10, "完成任務", "seed:task:1")
    squirrel.add_pinecones(ledger, "小晴", 120, "每週任務", "seed:weekly:1")
    squirrel.add_pinecones(ledger, "小凱", 260, "每週任務", "seed:weekly:2")
    squirrel.add_pinecones(ledger, "小美", 90, "每日簽到", "seed:checkin:1")
    squirrel.add_pinecones(ledger, "阿明", 45, "金松果", "seed:treasure:1")
    save_data(PINECONES_PATH, ledger)

    save_data(REPORTS_PATH, [])
    save_data(BLOCKS_PATH, [])
    print("✅ 示範資料已重設。示範帳號：小宇／小晴／小安／小凱／阿明／小美，密碼都是", DEMO_PASSWORD)


if __name__ == "__main__":
    main()
