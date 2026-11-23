# storage.py —— 倉庫：負責讀寫 JSON 檔、產生編號、取得現在時間
# 所有模組都透過這個檔案存取資料，不要在別的地方直接 open() 資料檔

import json
import os
from datetime import datetime

# 專案資料夾的位置（不管從哪裡執行 streamlit，都能找到 data/）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CHAT_DIR = os.path.join(DATA_DIR, "chats")   # 私訊：每個討論串一個檔案

USERS_PATH = os.path.join(DATA_DIR, "users.json")
LOSTFOUND_PATH = os.path.join(DATA_DIR, "lostfound.json")
TASKS_PATH = os.path.join(DATA_DIR, "tasks.json")
EVENTS_PATH = os.path.join(DATA_DIR, "events.json")
REPORTS_PATH = os.path.join(DATA_DIR, "reports.json")
BLOCKS_PATH = os.path.join(DATA_DIR, "blocks.json")
PROFILES_PATH = os.path.join(DATA_DIR, "profiles.json")     # 松鼠外觀與地圖位置
PINECONES_PATH = os.path.join(DATA_DIR, "pinecones.json")   # 松果紀錄


def ensure_dirs():
    """確保 data/ 與 data/chats/ 資料夾存在"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    if not os.path.exists(CHAT_DIR):
        os.makedirs(CHAT_DIR)


def load_data(path):
    """讀取 JSON 檔並回傳 list；檔案不存在或壞掉時回傳 []"""
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(data, list):
        return data
    return []


def save_data(path, data):
    """把 list 寫回 JSON 檔（先寫暫存檔再改名，避免寫到一半當機把檔案弄壞）"""
    ensure_dirs()
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(temp_path, path)


def get_next_id(items):
    """回傳 最大 id + 1；清單是空的就回傳 1"""
    max_id = 0
    for item in items:
        if item.get("id", 0) > max_id:
            max_id = item["id"]
    return max_id + 1


def now_text():
    """回傳現在時間字串，例如 '2026-11-20 14:30'"""
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def today_text():
    """回傳今天日期字串，例如 '2026-11-20'"""
    return datetime.now().strftime("%Y-%m-%d")


def find_by_id(items, item_id):
    """在 list 中找到 id 相符的那一筆 dict，找不到回傳 None"""
    for item in items:
        if item.get("id") == item_id:
            return item
    return None


def replace_by_id(items, new_item):
    """把 list 中 id 相同的那筆換成 new_item，回傳新的 list"""
    result = []
    for item in items:
        if item.get("id") == new_item.get("id"):
            result.append(new_item)
        else:
            result.append(item)
    return result


# ---------- 私訊：每個討論串一個檔案（降低兩人同時寫入互相覆蓋的機會） ----------

def thread_path(thread_id):
    """回傳某個討論串檔案的路徑，例如 data/chats/thread_3.json"""
    return os.path.join(CHAT_DIR, "thread_" + str(thread_id) + ".json")


def load_thread(thread_id):
    """讀取單一討論串（dict），不存在回傳 None"""
    path = thread_path(thread_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def save_thread(thread):
    """寫入單一討論串（dict）"""
    ensure_dirs()
    path = thread_path(thread["id"])
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(thread, f, ensure_ascii=False, indent=2)
    os.replace(temp_path, path)


def load_all_threads():
    """讀取 data/chats/ 裡所有討論串，回傳 list"""
    ensure_dirs()
    threads = []
    for name in os.listdir(CHAT_DIR):
        if name.startswith("thread_") and name.endswith(".json"):
            path = os.path.join(CHAT_DIR, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    threads.append(json.load(f))
            except (json.JSONDecodeError, OSError):
                pass
    return threads
