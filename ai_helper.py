# ai_helper.py —— AI／規則雙軌輔助與隱私守門（AI-1～AI-7）
#
# 設計原則（對應 spec 5.3）：
#   1. 人在迴圈：這裡的函式只「建議」，不自動發布、不自動送出、不自動判定
#   2. 雙軌保底：USE_AI=false 或 AI 失敗／逾時／格式錯誤 → 自動退回規則版，畫面不報錯
#   3. 標示來源：雙軌函式統一回傳 {"data": 結果, "source": "AI" 或 "規則"}
#   4. 最小資料：任何文字送進 AI 前都先經過 mask_sensitive；驗證答案「絕不」送給 AI
#   5. 不編造：地點只能出自 SAFE_SPOTS、推薦只能出自現有活動、配對只能從規則候選中排序
#   6. 輸出驗證：AI 回傳的 JSON 欄位、列舉值、id 都要檢查，不合法就當作失敗
#   7. 安全規則不外包：任務「禁止」只由規則判定，AI 只能把「通過」加嚴成「提醒」

import json
import os
import re
from datetime import datetime, timedelta

# 例外套件（spec 第 7 章允許）：requests 呼叫 API、python-dotenv 讀取 .env
try:
    import requests
except ImportError:
    requests = None
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

from lostfound import CATEGORIES, score_pair
from tasks import TASK_TYPES
from events import EVENT_CATEGORIES

# ======================================================================
# 0. 共用清單（團隊可依中大實際情況修改）
# ======================================================================

# 校內常見地點（一句話填表時用來辨識地點；請依實際校園修改）
LOCATIONS = ["總圖書館", "圖書館", "行政大樓", "松苑", "烏龜池", "工五館", "科四館", "國鼎光電大樓", "學生活動中心", "工程一館", "工程二館", "工程三館", "工程五館", "科學館",
             "文學院", "管理學院", "教學研究綜合大樓", "體育館", "操場", "游泳池", "中大湖",
             "宿舍", "餐廳", "宵夜街", "後門", "正門", "公車站", "停車場", "便利商店", "郵局", "健身房"]

# 面交安全地點白名單（AI 只能從這裡挑，不能自己編地點）
SAFE_SPOTS = ["圖書館一樓服務台前", "學生活動中心一樓大廳", "便利商店門口", "正門警衛室旁",
              "餐廳入口", "體育館一樓大廳", "各系館一樓大廳"]

# 物品詞 → 類別（長的詞放前面，才會先比對到「保溫水壺」而不是「水壺」）
OBJECT_WORDS = [
    ["學生證", "證件卡片"], ["悠遊卡", "證件卡片"], ["身分證", "證件卡片"], ["健保卡", "證件卡片"],
    ["駕照", "證件卡片"], ["信用卡", "證件卡片"], ["錢包", "證件卡片"], ["皮夾", "證件卡片"], ["卡套", "證件卡片"],
    ["藍牙耳機", "3C電子"], ["無線耳機", "3C電子"], ["耳機", "3C電子"], ["AirPods", "3C電子"],
    ["筆電", "3C電子"], ["平板", "3C電子"], ["手機", "3C電子"], ["行動電源", "3C電子"],
    ["充電器", "3C電子"], ["充電線", "3C電子"], ["隨身碟", "3C電子"], ["計算機", "3C電子"], ["滑鼠", "3C電子"],
    ["保溫水壺", "雨傘水壺"], ["保溫瓶", "雨傘水壺"], ["水壺", "雨傘水壺"], ["水瓶", "雨傘水壺"],
    ["環保杯", "雨傘水壺"], ["折疊傘", "雨傘水壺"], ["雨傘", "雨傘水壺"], ["傘", "雨傘水壺"],
    ["外套", "衣物配件"], ["帽子", "衣物配件"], ["圍巾", "衣物配件"], ["眼鏡", "衣物配件"],
    ["手錶", "衣物配件"], ["手環", "衣物配件"], ["項鍊", "衣物配件"], ["背包", "衣物配件"], ["包包", "衣物配件"],
    ["鑰匙圈", "鑰匙"], ["鑰匙", "鑰匙"], ["磁扣", "鑰匙"],
    ["課本", "書籍文具"], ["講義", "書籍文具"], ["筆記本", "書籍文具"], ["鉛筆盒", "書籍文具"],
    ["筆袋", "書籍文具"], ["原子筆", "書籍文具"], ["書", "書籍文具"],
]
COLOR_WORDS = ["黑色", "白色", "灰色", "紅色", "粉紅色", "粉色", "橘色", "黃色", "綠色", "藍色",
               "深藍色", "淺藍色", "紫色", "咖啡色", "棕色", "銀色", "金色", "透明"]

LOST_WORDS = ["掉了", "遺失", "不見", "弄丟", "丟了", "找不到", "忘在", "遺落"]
FOUND_WORDS = ["撿到", "拾獲", "發現", "有人掉", "誰的", "失主"]

TASK_TYPE_WORDS = [
    ["揪人", ["揪", "一起", "缺人", "湊", "團購", "組隊"]],
    ["代跑腿", ["跑腿", "寄", "領包裹", "繳", "送到", "送去", "拿去"]],
    ["代拿代購", ["帶", "買", "代購", "代拿", "幫拿", "外帶"]],
]

EVENT_CATEGORY_WORDS = [
    ["學術講座", ["講座", "演講", "研討", "分享會", "工作坊"]],
    ["藝文表演", ["表演", "音樂會", "展覽", "成發", "演唱", "戲劇", "電影"]],
    ["運動競賽", ["比賽", "盃", "球賽", "路跑", "運動", "競賽"]],
    ["志工服務", ["志工", "服務", "淨灘", "募"]],
    ["社團招生", ["社團", "新生", "招生", "體驗", "社課", "迎新"]],
]

# 任務規範：「禁止」由規則直接擋下，不交給 AI 判斷
TASK_BANNED = [
    ["學術不誠信", ["代考", "替考", "槍手", "代寫作業", "代寫報告", "寫作業", "代寫", "代簽", "代點名", "代打卡", "代簽到", "幫簽到", "幫點名"]],
    ["違禁品", ["香菸", "菸", "電子煙", "酒", "啤酒", "處方藥", "安眠藥", "大麻"]],
    ["索取帳號密碼或個資", ["帳號密碼", "借帳號", "密碼", "驗證碼", "身分證", "提款卡", "存摺", "人頭"]],
]
TASK_WARNING = [
    ["金錢風險：請不要先匯款或先付錢", ["匯款", "轉帳", "先付", "訂金", "押金", "預付"]],
    ["時間風險：深夜交接請特別注意安全", ["深夜", "半夜", "凌晨", "11點後", "十二點"]],
    ["地點風險：請約在校內公共場所", ["校外", "房間", "家裡", "住處", "私下"]],
    ["藥品相關：請只代買合法的成藥，處方藥請本人領取", ["藥"]],
]

# 私訊防詐關鍵字（送出前提醒，由使用者決定）
SCAM_WORDS = [
    ["要求匯款或先付錢", ["匯款", "轉帳", "先付", "訂金", "押金", "運費", "ATM", "超商代碼", "遊戲點數"]],
    ["索取驗證碼或密碼", ["驗證碼", "簡訊碼", "密碼", "OTP"]],
    ["引導到站外聯絡", ["加賴", "加LINE", "LINE ID", "line id", "加我line", "IG私訊", "私下聯絡"]],
    ["包含外部連結", ["http://", "https://", "bit.ly", "reurl"]],
]

# 驗證問題模板（AI-5 規則版）
VERIFY_TEMPLATES = {
    "證件卡片": ["卡片上的姓名第一個字是什麼？", "卡套或卡片背面有什麼特徵？"],
    "3C電子": ["外殼或保護殼是什麼顏色、有什麼圖案？", "螢幕或機身有哪些刮痕或貼紙？"],
    "雨傘水壺": ["上面有什麼貼紙或圖案？", "有哪些明顯的刮痕、凹痕或掛繩？"],
    "衣物配件": ["口袋裡或內側有什麼東西或標記？", "尺寸或品牌標籤是什麼？"],
    "鑰匙": ["鑰匙圈上掛了什麼吊飾？", "總共有幾把鑰匙？"],
    "書籍文具": ["內頁有沒有寫名字或筆記？寫在哪裡？", "封面或內頁有什麼特別的痕跡？"],
    "其他": ["物品上有什麼只有你知道的特徵？", "裡面或背面有什麼東西？"],
}

WEEKDAY_WORDS = ["一", "二", "三", "四", "五", "六", "日"]


# ======================================================================
# 1. 呼叫語言模型（唯一出口）
# ======================================================================

def is_ai_enabled():
    """USE_AI=true 且有金鑰時回傳 True"""
    use_ai = os.getenv("USE_AI", "false").strip().lower() == "true"
    key = os.getenv("AI_API_KEY", "").strip()
    return use_ai and key != "" and requests is not None


def call_llm(system_prompt, user_text):
    """呼叫語言模型並回傳文字；USE_AI 關閉、無金鑰、逾時、錯誤一律回傳 None。呼叫前必須已遮蔽個資"""
    if not is_ai_enabled():
        return None

    provider = os.getenv("AI_PROVIDER", "github").strip().lower()
    key = os.getenv("AI_API_KEY", "").strip()
    timeout = 5
    try:
        timeout = float(os.getenv("AI_TIMEOUT", "5"))
    except ValueError:
        timeout = 5

    body = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": mask_sensitive(user_text)},   # 保險：再遮蔽一次
        ],
        "temperature": 0.2,
    }

    if provider == "azure":
        # Azure OpenAI：AI_ENDPOINT 填完整網址（含 deployments/部署名稱/chat/completions?api-version=...）
        url = os.getenv("AI_ENDPOINT", "").strip()
        headers = {"api-key": key, "Content-Type": "application/json"}
    else:
        # GitHub Models（預設）：免費、用 GitHub 帳號的 Personal Access Token
        url = os.getenv("AI_ENDPOINT", "").strip()
        if url == "":
            url = "https://models.github.ai/inference/chat/completions"
        headers = {
            "Authorization": "Bearer " + key,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        }
        body["model"] = os.getenv("AI_MODEL", "openai/gpt-4.1-mini").strip()

    if url == "":
        return None
    try:
        response = requests.post(url, headers=headers, json=body, timeout=timeout)
        if response.status_code != 200:
            print("[AI] 呼叫失敗，狀態碼：", response.status_code, response.text[:200])
            return None
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as error:   # 任何錯誤（逾時、斷網、格式不同）都退回規則版
        print("[AI] 呼叫發生錯誤，改用規則版：", error)
        return None


def ask_json(system_prompt, user_text):
    """呼叫 AI 並把回答解析成 dict；失敗回傳 None"""
    text = call_llm(system_prompt + "\n只輸出一個 JSON 物件，不要加任何說明文字或 ``` 符號。", user_text)
    if text is None:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    if isinstance(data, dict):
        return data
    return None


def wrap(data, source):
    """雙軌函式統一回傳格式"""
    return {"data": data, "source": source}


# ======================================================================
# 2. AI-3 隱私守門員（以規則為主）
# ======================================================================

SENSITIVE_PATTERNS = [
    ["Email", r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"],
    ["身分證", r"(?<![A-Za-z0-9])[A-Za-z][12]\d{8}(?!\d)"],
    ["手機", r"(?<!\d)(?:\+?886[\- ]?9|09)\d{2}[\- ]?\d{3}[\- ]?\d{3}(?!\d)"],
    ["學號", r"(?<!\d)1\d{8}(?!\d)"],
]


def detect_sensitive(text):
    """找出學號、手機、Email、身分證字號，回傳 [{"type": 類型, "value": 內容}, ...]"""
    found = []
    for pair in SENSITIVE_PATTERNS:
        matches = re.findall(pair[1], text)
        for value in matches:
            found.append({"type": pair[0], "value": value})
    return found


def mask_sensitive(text):
    """把敏感內容換成同長度的 ＊"""
    if text is None:
        return ""
    for pair in SENSITIVE_PATTERNS:
        matches = re.findall(pair[1], text)
        for value in matches:
            text = text.replace(value, "＊" * len(value))
    return text


def detect_scam_risk(text):
    """私訊防詐：回傳風險原因清單（空清單代表沒發現）"""
    reasons = []
    lower = text.lower()
    for pair in SCAM_WORDS:
        for word in pair[1]:
            if word.lower() in lower:
                reasons.append(pair[0])
                break
    return reasons


# ======================================================================
# 3. 規則版的小工具：日期、時間、地點、物品
# ======================================================================

def parse_date_word(text, prefer_past):
    """從文字找日期詞（今天／昨天／明天／週五／11/18…），回傳 'YYYY-MM-DD' 或空字串"""
    today = datetime.now()
    word_days = [["大前天", -3], ["前天", -2], ["昨天", -1], ["昨晚", -1], ["今天", 0], ["今早", 0],
                 ["今晚", 0], ["剛剛", 0], ["剛才", 0], ["大後天", 3], ["後天", 2], ["明天", 1], ["明早", 1]]
    for pair in word_days:
        if pair[0] in text:
            return (today + timedelta(days=pair[1])).strftime("%Y-%m-%d")

    # 「11/18」或「11月18日」
    m = re.search(r"(\d{1,2})\s*[/月]\s*(\d{1,2})", text)
    if m:
        month = int(m.group(1))
        day = int(m.group(2))
        if 1 <= month <= 12 and 1 <= day <= 31:
            try:
                return datetime(today.year, month, day).strftime("%Y-%m-%d")
            except ValueError:
                return ""

    # 「週五／星期五／禮拜五」
    for i in range(7):
        w = WEEKDAY_WORDS[i]
        if ("週" + w) in text or ("星期" + w) in text or ("禮拜" + w) in text or ("周" + w) in text:
            diff = i - today.weekday()
            if prefer_past:
                if diff > 0:
                    diff = diff - 7
            else:
                if diff < 0:
                    diff = diff + 7
            return (today + timedelta(days=diff)).strftime("%Y-%m-%d")
    return ""


def parse_time_word(text):
    """從文字找時間（下午3點、15:00、中午…），回傳 'HH:MM' 或空字串"""
    m = re.search(r"(\d{1,2})\s*[:：點]\s*(\d{2})?", text)
    if m:
        hour = int(m.group(1))
        minute = 0
        if m.group(2):
            minute = int(m.group(2))
        if ("下午" in text or "晚上" in text) and hour < 12:
            hour = hour + 12
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return str(hour).zfill(2) + ":" + str(minute).zfill(2)
    if "早上" in text or "上午" in text:
        return "10:00"
    if "中午" in text:
        return "12:00"
    if "下午" in text:
        return "15:00"
    if "傍晚" in text:
        return "17:30"
    if "晚上" in text:
        return "19:00"
    return ""


def find_location(text):
    """從文字找出第一個符合的校內地點"""
    for place in LOCATIONS:
        if place in text:
            return place
    return ""


def find_object(text):
    """找物品詞，回傳 [物品詞, 類別]；找不到回傳 ["", "其他"]"""
    for pair in OBJECT_WORDS:
        if pair[0].lower() in text.lower():
            return pair
    return ["", "其他"]


def find_color(text):
    """找顏色詞"""
    for color in COLOR_WORDS:
        if color in text:
            return color
    return ""


# ======================================================================
# 4. AI-1 一句話發布
# ======================================================================

def rule_parse_item(text):
    """規則版：一句話 → 失物表單欄位"""
    kind = ""
    for w in FOUND_WORDS:
        if w in text:
            kind = "拾獲"
    for w in LOST_WORDS:
        if w in text:
            kind = "遺失"
    obj = find_object(text)
    color = find_color(text)
    name = color + obj[0]
    keywords = []
    if color != "":
        keywords.append(color)
    if obj[0] != "":
        keywords.append(obj[0])
        # 「保溫水壺」也加上「水壺」，配對時比較容易對到
        for pair in OBJECT_WORDS:
            if pair[0] != obj[0] and pair[0] in obj[0] and len(pair[0]) >= 2 and pair[0] not in keywords:
                keywords.append(pair[0])
    return {
        "kind": kind,
        "name": name,
        "category": obj[1],
        "location": find_location(text),
        "date": parse_date_word(text, True),
        "description": mask_sensitive(text),
        "keywords": keywords[:5],
    }


def rule_parse_task(text):
    """規則版：一句話 → 任務表單欄位"""
    task_type = "日常求助"
    for pair in TASK_TYPE_WORDS:
        for w in pair[1]:
            if w in text:
                task_type = pair[0]
                break
        if task_type != "日常求助":
            break
    date = parse_date_word(text, False)
    time = parse_time_word(text)
    deadline = ""
    if date != "" and time != "":
        deadline = date + " " + time
    elif date != "":
        deadline = date + " 18:00"
    elif time != "":
        deadline = datetime.now().strftime("%Y-%m-%d") + " " + time

    reward = ""
    m = re.search(r"(請你[^，。,.!！]*|請喝[^，。,.!！]*|酬勞[^，。,.!！]*|\d+\s*元)", text)
    if m:
        reward = m.group(1)

    title = text.strip()
    for sep in ["，", ",", "。"]:
        if sep in title:
            title = title.split(sep)[0]
    title = title[:20]

    keywords = [task_type]
    obj = find_object(text)
    if obj[0] != "":
        keywords.append(obj[0])
    for food in ["飲料", "午餐", "晚餐", "早餐", "便當", "咖啡", "包裹"]:
        if food in text and food not in keywords:
            keywords.append(food)
    return {
        "type": task_type,
        "title": title,
        "description": mask_sensitive(text),
        "location": find_location(text),
        "deadline": deadline,
        "reward": reward,
        "keywords": keywords[:5],
    }


def rule_parse_event(text):
    """規則版：一句話 → 活動表單欄位"""
    category = "其他"
    for pair in EVENT_CATEGORY_WORDS:
        for w in pair[1]:
            if w in text:
                category = pair[0]
                break
        if category != "其他":
            break
    date = parse_date_word(text, False)
    time = parse_time_word(text)
    if time == "":
        time = "19:00"
    start = ""
    end = ""
    if date != "":
        start = date + " " + time
        end_hour = int(time[:2]) + 2
        if end_hour > 23:
            end_hour = 23
        end = date + " " + str(end_hour).zfill(2) + time[2:]
    org = ""
    # 先拿掉日期時間詞，再找「○○社／○○系學會」，避免把「週五晚上」也當成社名
    cleaned = re.sub(r"(下|這|本)?(週|周|星期|禮拜)[一二三四五六日天]|大後天|今天|明天|後天|早上|上午|中午|下午|傍晚|晚上", " ", text)
    m = re.search(r"([\u4e00-\u9fffA-Za-z]{1,8}?(系學會|學會|社))", cleaned)
    if m:
        org = m.group(1)
        # 「在活動中心有攝影社」→ 只留最後一個「有／在／的…」後面的部分 →「攝影社」
        for filler in ["有", "在", "的", "是", "辦", "舉"]:
            if filler in org[:-1]:
                org = org[org.rfind(filler, 0, len(org) - 1) + 1:]
    tags = []
    for pair in EVENT_CATEGORY_WORDS:
        for w in pair[1]:
            if w in text and w not in tags:
                tags.append(w)
    if org.endswith("社") and len(org) > 1:
        tags.append(org[:-1])   # 「攝影社」→ 標籤「攝影」
    return {
        "title": text.strip()[:30],
        "org": org,
        "category": category,
        "place": find_location(text),
        "start": start,
        "end": end,
        "description": mask_sensitive(text),
        "tags": tags[:5],
    }


REQUIRED_FIELDS = {
    "item": ["kind", "name", "category", "location", "date"],
    "task": ["type", "title", "location", "deadline"],
    "event": ["title", "category", "place", "start"],
}
FIELD_NAMES = {"kind": "遺失或拾獲", "name": "物品名稱", "category": "類別", "location": "地點",
               "date": "日期", "type": "任務類型", "title": "標題", "deadline": "截止時間",
               "place": "活動地點", "start": "開始時間"}


def find_missing(fields, form_type):
    """列出還沒填的必要欄位（中文名稱）"""
    missing = []
    for key in REQUIRED_FIELDS[form_type]:
        if fields.get(key, "") in ("", None, []):
            missing.append(FIELD_NAMES[key])
    return missing


def valid_date(text, with_time):
    """檢查日期字串格式是否正確"""
    fmt = "%Y-%m-%d"
    if with_time:
        fmt = "%Y-%m-%d %H:%M"
    try:
        datetime.strptime(text, fmt)
        return True
    except (ValueError, TypeError):
        return False


def merge_ai_fields(rule_fields, ai_fields, form_type):
    """把 AI 給的欄位合併進規則結果；每個欄位都檢查合法才採用"""
    result = dict(rule_fields)
    for key in rule_fields:
        if key not in ai_fields:
            continue
        value = ai_fields[key]
        if key in ("keywords", "tags"):
            if isinstance(value, list):
                clean = []
                for v in value:
                    if isinstance(v, str) and v.strip() != "" and len(v) <= 10:
                        clean.append(v.strip())
                if len(clean) > 0:
                    result[key] = clean[:5]
            continue
        if not isinstance(value, str) or value.strip() == "":
            continue
        value = value.strip()
        # 列舉值檢查
        if key == "kind" and value not in ("遺失", "拾獲"):
            continue
        if key == "category" and form_type == "item" and value not in CATEGORIES:
            continue
        if key == "category" and form_type == "event" and value not in EVENT_CATEGORIES:
            continue
        if key == "type" and value not in TASK_TYPES:
            continue
        if key == "date" and not valid_date(value, False):
            continue
        if key in ("deadline", "start", "end") and not valid_date(value, True):
            continue
        if key == "description":
            continue   # 描述保留使用者原話（已遮蔽），不讓 AI 改寫
        result[key] = mask_sensitive(value)
    return result


def parse_form_text(text, form_type):
    """AI-1：一句話 → 表單欄位（另含 missing 缺漏欄位清單）"""
    text = mask_sensitive(text)
    if form_type == "item":
        fields = rule_parse_item(text)
    elif form_type == "task":
        fields = rule_parse_task(text)
    else:
        fields = rule_parse_event(text)

    source = "規則"
    today = datetime.now().strftime("%Y-%m-%d（星期") + WEEKDAY_WORDS[datetime.now().weekday()] + "）"
    if form_type == "item":
        schema = ('{"kind": "遺失或拾獲", "name": "物品名稱（含顏色）", "category": "' + "／".join(CATEGORIES)
                  + ' 擇一", "location": "地點", "date": "YYYY-MM-DD", "keywords": ["最多5個關鍵字"]}')
    elif form_type == "task":
        schema = ('{"type": "' + "／".join(TASK_TYPES) + ' 擇一", "title": "20字內標題", "location": "地點", '
                  '"deadline": "YYYY-MM-DD HH:MM", "reward": "酬勞文字，沒提到就空字串", "keywords": ["最多5個"]}')
    else:
        schema = ('{"title": "活動名稱", "org": "主辦單位", "category": "' + "／".join(EVENT_CATEGORIES)
                  + ' 擇一", "place": "地點", "start": "YYYY-MM-DD HH:MM", "end": "YYYY-MM-DD HH:MM", "tags": ["最多5個"]}')
    prompt = ("你是校園平台的表單助手。今天是 " + today + "。請把使用者的一句話轉成表單欄位，格式：" + schema
              + "。只能使用句子裡提供的資訊，句子沒提到的欄位填空字串，不要猜測或編造。")
    ai_fields = ask_json(prompt, text)
    if ai_fields is not None:
        fields = merge_ai_fields(fields, ai_fields, form_type)
        source = "AI"

    fields["missing"] = find_missing(fields, form_type)
    return wrap(fields, source)


def suggest_tags(text, kind):
    """AI-1：從文字建議最多 5 個標籤"""
    text = mask_sensitive(text)
    tags = []
    obj = find_object(text)
    if obj[0] != "":
        tags.append(obj[0])
    color = find_color(text)
    if color != "":
        tags.append(color)
    place = find_location(text)
    if place != "":
        tags.append(place)
    for pair in EVENT_CATEGORY_WORDS:
        for w in pair[1]:
            if w in text and w not in tags:
                tags.append(w)
    source = "規則"
    ai = ask_json("請從這段校園平台的文字中挑出最多 5 個短標籤（每個 2–6 字），格式：{\"tags\": [\"...\"]}。只能用文字裡出現的概念。", text)
    if ai is not None and isinstance(ai.get("tags"), list):
        clean = []
        for t in ai["tags"]:
            if isinstance(t, str) and 1 <= len(t.strip()) <= 8:
                clean.append(t.strip())
        if len(clean) > 0:
            tags = clean
            source = "AI"
    return wrap(tags[:5], source)


# ======================================================================
# 5. AI-2 智慧配對：規則算候選分數 → AI 在候選中「重新排序」並寫理由
# ======================================================================

def public_item_text(item):
    """只取失物的公開欄位（絕不包含 verify_answers）"""
    return ("id=" + str(item["id"]) + "｜" + item["kind"] + "｜" + item["name"] + "｜類別:" + item["category"]
            + "｜地點:" + item["location"] + "｜日期:" + item["date"] + "｜描述:" + mask_sensitive(item["description"]))


def rule_match_reason(item_a, item_b):
    """規則版理由：把計分明細翻成一句白話"""
    result = score_pair(item_a, item_b)
    parts = []
    if item_a["category"] == item_b["category"]:
        parts.append("同屬「" + item_a["category"] + "」")
    if item_a["location"] != "" and item_a["location"] == item_b["location"]:
        parts.append("都在" + item_a["location"])
    if result["gap"] <= 3:
        if result["gap"] == 0:
            parts.append("同一天")
        else:
            parts.append("日期只差 " + str(result["gap"]) + " 天")
    if len(result["shared"]) > 0:
        parts.append("都提到「" + "、".join(result["shared"]) + "」")
    if len(parts) == 0:
        return "部分特徵相近，建議私訊確認。"
    return "，".join(parts) + "，可能是同一件物品。"


def make_match_reason(item_a, item_b):
    """AI-2：為一組配對寫一句白話理由"""
    reason = rule_match_reason(item_a, item_b)
    prompt = "你是失物招領助手。用一句 40 字內的繁體中文，說明這兩筆刊登為什麼可能是同一件物品。只能根據提供的資訊，不要編造。格式：{\"reason\": \"...\"}"
    ai = ask_json(prompt, "A：" + public_item_text(item_a) + "\nB：" + public_item_text(item_b))
    if ai is not None and isinstance(ai.get("reason"), str) and 0 < len(ai["reason"]) <= 80:
        return wrap(ai["reason"], "AI")
    return wrap(reason, "規則")


def rerank_matches(item, candidates):
    """AI-2：AI 只能在規則候選中重新排序＋寫理由；id 不在候選中就整個作廢退回規則版"""
    rule_result = []
    for c in candidates:
        rule_result.append({"item": c["item"], "score": c["score"], "detail": c.get("detail", []),
                            "reason": rule_match_reason(item, c["item"])})
    if len(candidates) == 0:
        return wrap(rule_result, "規則")

    lines = ""
    for c in candidates:
        lines = lines + public_item_text(c["item"]) + "｜規則分數:" + str(c["score"]) + "\n"
    prompt = ("你是失物招領助手。下面是一筆刊登和幾個規則算出的候選。請依「描述語意」判斷哪些最可能是同一件物品，"
              "由最可能到最不可能排序，並為每筆寫一句 40 字內的理由。只能使用候選中的 id，不能新增。"
              "格式：{\"ranking\": [{\"id\": 數字, \"reason\": \"...\"}]}")
    ai = ask_json(prompt, "刊登：" + public_item_text(item) + "\n候選：\n" + lines)
    if ai is None or not isinstance(ai.get("ranking"), list):
        return wrap(rule_result, "規則")

    # 驗證：每個 id 都要在候選中、不能重複
    lookup = {}
    for r in rule_result:
        lookup[r["item"]["id"]] = r
    new_order = []
    used = []
    for entry in ai["ranking"]:
        if not isinstance(entry, dict):
            return wrap(rule_result, "規則")
        entry_id = entry.get("id")
        if entry_id not in lookup or entry_id in used:
            return wrap(rule_result, "規則")
        used.append(entry_id)
        one = dict(lookup[entry_id])
        reason = entry.get("reason")
        if isinstance(reason, str) and 0 < len(reason) <= 80:
            one["reason"] = reason
        new_order.append(one)
    # AI 漏掉的候選補在最後，不讓任何規則候選消失
    for r in rule_result:
        if r["item"]["id"] not in used:
            new_order.append(r)
    return wrap(new_order, "AI")


# ======================================================================
# 6. AI-5 認領驗證問題
# ======================================================================

def make_verify_questions(item):
    """AI-5：產生 2 個「只有失主答得出」的問題（只讀公開欄位）"""
    questions = VERIFY_TEMPLATES.get(item.get("category", "其他"), VERIFY_TEMPLATES["其他"])
    prompt = ("你是失物招領助手。拾獲者撿到下面的物品，請設計 2 個「只有真正失主才答得出」的驗證問題，"
              "問題不能從公開描述直接看出答案，每題 25 字內。格式：{\"questions\": [\"...\", \"...\"]}")
    text = "物品：" + item.get("name", "") + "｜類別：" + item.get("category", "") + "｜公開描述：" + mask_sensitive(item.get("description", ""))
    ai = ask_json(prompt, text)
    if ai is not None and isinstance(ai.get("questions"), list) and len(ai["questions"]) >= 2:
        q1 = ai["questions"][0]
        q2 = ai["questions"][1]
        if isinstance(q1, str) and isinstance(q2, str) and 0 < len(q1) <= 50 and 0 < len(q2) <= 50:
            return wrap([q1, q2], "AI")
    return wrap(list(questions), "規則")


# ======================================================================
# 7. AI-6 任務規範檢查（禁止由規則決定，AI 只能加嚴）
# ======================================================================

def rule_check_task(text):
    """規則版：回傳 {"level", "reasons"}"""
    level = "通過"
    reasons = []
    for pair in TASK_BANNED:
        for w in pair[1]:
            if w in text:
                level = "禁止"
                reasons.append("涉及" + pair[0] + "（「" + w + "」）")
                break
    if level == "禁止":
        return {"level": level, "reasons": reasons}
    for pair in TASK_WARNING:
        for w in pair[1]:
            if w in text:
                level = "提醒"
                reasons.append(pair[0])
                break
    if len(detect_sensitive(text)) > 0:
        level = "提醒"
        reasons.append("內容含有學號、手機等個資，發布時會自動遮蔽")
    return {"level": level, "reasons": reasons}


def check_task_rules(title, description):
    """AI-6：任務發布前的規範檢查"""
    text = title + " " + description
    result = rule_check_task(text)
    if result["level"] == "禁止":
        return wrap(result, "規則")   # 規則擋下的內容，AI 不能放行，所以根本不問 AI

    prompt = ("你是校園互助平台的審查助手。檢查這個任務是否有學術不誠信、違禁品、索取個資、詐騙、"
              "人身安全的疑慮。格式：{\"level\": \"通過\" 或 \"提醒\", \"reasons\": [\"每條 30 字內\"]}")
    ai = ask_json(prompt, mask_sensitive(text))
    if ai is None or ai.get("level") not in ("通過", "提醒", "禁止"):
        return wrap(result, "規則")
    # AI 只能加嚴：可以把「通過」升為「提醒」，但不能把「提醒」降為「通過」；「禁止」只由規則判定
    if ai["level"] in ("提醒", "禁止"):
        result["level"] = "提醒"
        if isinstance(ai.get("reasons"), list):
            for r in ai["reasons"]:
                if isinstance(r, str) and 0 < len(r) <= 60 and r not in result["reasons"]:
                    result["reasons"].append("AI 提醒：" + r)
    return wrap(result, "AI")


# ======================================================================
# 8. AI-7 活動推薦（只能從現有清單挑）
# ======================================================================

def rule_recommend(events, interest_text):
    """規則版：興趣文字和活動標籤／標題的重疊計分"""
    scored = []
    for event in events:
        score = 0
        hit = []
        for tag in event["tags"]:
            if tag != "" and tag in interest_text:
                score = score + 2
                hit.append(tag)
        for pair in EVENT_CATEGORY_WORDS:
            if pair[0] == event["category"]:
                for w in pair[1]:
                    if w in interest_text:
                        score = score + 1
                        break
        if "朋友" in interest_text or "認識" in interest_text:
            if event["category"] in ("社團招生", "運動競賽", "志工服務"):
                score = score + 1
                hit.append("適合認識新朋友")
        if score > 0:
            reason = "和你的興趣類別相近"
            if len(hit) > 0:
                reason = "符合你的興趣：" + "、".join(hit)
            scored.append({"event": event, "reason": reason, "score": score})
    scored = sorted(scored, key=get_rec_score, reverse=True)
    result = []
    for s in scored[:3]:
        result.append({"event": s["event"], "reason": s["reason"]})
    return result


def get_rec_score(entry):
    """排序用：取出推薦分數"""
    return entry["score"]


def recommend_events(events, interest_text):
    """AI-7：依興趣推薦最多 3 個活動，且一定來自 events"""
    interest_text = mask_sensitive(interest_text)
    rule_result = rule_recommend(events, interest_text)
    if len(events) == 0:
        return wrap([], "規則")
    lines = ""
    lookup = {}
    for e in events:
        lookup[e["id"]] = e
        lines = (lines + "id=" + str(e["id"]) + "｜" + e["title"] + "｜" + e["category"] + "｜標籤:"
                 + "、".join(e["tags"]) + "｜" + e["description"][:60] + "\n")
    prompt = ("你是校園活動推薦助手。只能從下面清單中挑最多 3 個最符合使用者興趣的活動，每個附 30 字內理由。"
              "不能推薦清單外的活動。格式：{\"picks\": [{\"id\": 數字, \"reason\": \"...\"}]}\n活動清單：\n" + lines)
    ai = ask_json(prompt, "使用者興趣：" + interest_text)
    if ai is None or not isinstance(ai.get("picks"), list):
        return wrap(rule_result, "規則")
    result = []
    for p in ai["picks"][:3]:
        if not isinstance(p, dict) or p.get("id") not in lookup:
            return wrap(rule_result, "規則")   # 出現不存在的 id → 視為捏造，整個退回
        reason = "符合你的興趣"
        if isinstance(p.get("reason"), str):
            reason = p["reason"]
        result.append({"event": lookup[p["id"]], "reason": reason[:60]})
    return wrap(result, "AI")


# ======================================================================
# 9. AI-4 面交／交接安全助手
# ======================================================================

def rule_spots(target):
    """規則版：依物品／任務所在地點排序白名單"""
    location = target.get("location", "")
    spots = []
    if "圖書館" in location:
        spots.append("圖書館一樓服務台前")
    if "活動中心" in location:
        spots.append("學生活動中心一樓大廳")
    if "體育館" in location or "操場" in location:
        spots.append("體育館一樓大廳")
    if "館" in location or "學院" in location:
        spots.append("各系館一樓大廳")
    for s in SAFE_SPOTS:
        if s not in spots:
            spots.append(s)
    return spots[:3]


def rule_slots():
    """規則版：建議未來兩天白天的時段"""
    now = datetime.now()
    slots = []
    for add in [1, 2]:
        day = (now + timedelta(days=add)).strftime("%Y-%m-%d")
        slots.append(day + " 12:10")
        slots.append(day + " 17:20")
    return slots[:3]


def suggest_meetup(target_type, target, thread):
    """AI-4：建議面交地點（只能出自 SAFE_SPOTS）、時段與安全提醒"""
    tips = "請約在人多的公共場所、白天時段；不要先付錢，也不要提供帳號密碼或驗證碼。"
    if target.get("category") == "證件卡片":
        tips = "證件類物品冒領風險較高，建議直接交給校內既有的失物招領管道（如總務處或警衛室，以學校公告為準）。" + tips
    if thread is not None and thread.get("verified") == "未驗證":
        tips = "認領驗證尚未通過，建議先確認驗證問題再面交。" + tips
    data = {"spots": rule_spots(target), "slots": rule_slots(), "tips": tips}

    prompt = ("你是校園面交安全助手。從白名單中挑 3 個最適合的面交地點，並寫一句 40 字內安全提醒。"
              "白名單：" + "、".join(SAFE_SPOTS) + "。格式：{\"spots\": [\"...\"], \"tip\": \"...\"}")
    if target_type == "item":
        desc = "物品：" + target.get("name", "") + "，類別：" + target.get("category", "") + "，地點：" + target.get("location", "")
    else:
        desc = "任務：" + target.get("title", "") + "，地點：" + target.get("location", "")
    ai = ask_json(prompt, desc)
    if ai is None or not isinstance(ai.get("spots"), list):
        return wrap(data, "規則")
    for s in ai["spots"]:
        if s not in SAFE_SPOTS:
            return wrap(data, "規則")   # 出現白名單以外的地點 → 不採用
    if len(ai["spots"]) == 0:
        return wrap(data, "規則")
    data["spots"] = ai["spots"][:3]
    if isinstance(ai.get("tip"), str) and 0 < len(ai["tip"]) <= 80:
        data["tips"] = ai["tip"] + " " + tips
    return wrap(data, "AI")


def quick_replies(thread, me):
    """AI-4：產生 3 則 20 字內的回覆草稿（只送最近 6 則、已遮蔽的訊息）"""
    if thread["meetup"] is None:
        replies = ["請問方便約哪裡交接？", "可以描述一下特徵嗎？", "謝謝你，辛苦了！"]
    elif thread["meetup"]["status"] == "待確認":
        replies = ["這個時間地點可以！", "可以改晚一點嗎？", "我可能會晚 5 分鐘"]
    else:
        replies = ["我到了，在門口", "謝謝你的幫忙！", "我穿黑色外套"]

    recent = thread["messages"][-6:]
    lines = ""
    for m in recent:
        if m["kind"] == "user":
            who = "對方"
            if m["sender"] == me:
                who = "我"
            lines = lines + who + "：" + mask_sensitive(m["text"]) + "\n"
    if lines == "":
        return wrap(replies, "規則")
    prompt = ("你是聊天回覆助手。依對話內容，替「我」寫 3 則禮貌、20 字內的繁體中文回覆草稿，"
              "不可包含任何聯絡方式或金錢要求。格式：{\"replies\": [\"...\", \"...\", \"...\"]}")
    ai = ask_json(prompt, lines)
    if ai is None or not isinstance(ai.get("replies"), list) or len(ai["replies"]) < 3:
        return wrap(replies, "規則")
    clean = []
    for r in ai["replies"][:3]:
        if not isinstance(r, str) or len(r) == 0 or len(r) > 20:
            return wrap(replies, "規則")
        if len(detect_scam_risk(r)) > 0 or len(detect_sensitive(r)) > 0:
            return wrap(replies, "規則")
        clean.append(r)
    return wrap(clean, "AI")
