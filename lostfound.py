# lostfound.py —— 失物招領邏輯（M1）：建立刊登、搜尋、配對計分、標記已尋回
#
# 【配對評分表】（依助教建議寫清楚，評審問「分數怎麼算」時可以直接指這裡）
#   前提：一筆是「遺失」、一筆是「拾獲」，且兩筆都還是「尋找中」，否則不配對
#   類別相同         +3
#   地點相同         +2
#   日期相差 ≤1 天   +2；相差 2–3 天 +1；相差超過 7 天直接不配對
#   關鍵字重疊       每個 +1，最多 +3
#   門檻：總分 ≥ 4 才列為候選
#
# 【手算案例】小宇遺失「黑色保溫水壺」（雨傘水壺／圖書館／11-18／黑色、水壺、保溫）
#            小晴拾獲「黑色保溫水壺」（雨傘水壺／圖書館／11-18／黑色、水壺、貼紙）
#   類別相同 +3、地點相同 +2、同一天 +2、
#   關鍵字「黑色」「保溫水壺」「水壺」都出現在對方的名稱或關鍵字中 +3（上限）→ 總分 10

from datetime import datetime

from storage import now_text

CATEGORIES = ["證件卡片", "3C電子", "雨傘水壺", "衣物配件", "鑰匙", "書籍文具", "其他"]
KINDS = ["遺失", "拾獲"]
STATUSES = ["尋找中", "已尋回"]

# 計分規則集中在這裡，要調整只改這幾個數字
SCORE_CATEGORY = 3
SCORE_LOCATION = 2
SCORE_DATE_CLOSE = 2      # 相差 0–1 天
SCORE_DATE_NEAR = 1       # 相差 2–3 天
SCORE_KEYWORD = 1
MAX_KEYWORD_SCORE = 3
MAX_DAY_GAP = 7
MATCH_THRESHOLD = 4


def create_item(kind, name, category, location, date, description, keywords, owner,
                verify_questions, verify_answers):
    """建立一筆新的失物刊登（dict，尚未存檔；id 由呼叫端用 get_next_id 補上）"""
    if kind != "拾獲":
        verify_questions = []
        verify_answers = []
    return {
        "id": 0,
        "kind": kind,
        "name": name.strip(),
        "category": category,
        "location": location.strip(),
        "date": date,
        "description": description.strip(),
        "keywords": keywords,
        "owner": owner,
        "verify_questions": verify_questions,
        "verify_answers": verify_answers,
        "status": "尋找中",
        "created_at": now_text(),
    }


def search_items(items, kind, category, keyword, status):
    """依種類、類別、關鍵字、狀態篩選；"全部" 或空字串代表不篩選；新的排前面"""
    result = []
    keyword = keyword.strip()
    for item in items:
        if kind not in ("", "全部") and item["kind"] != kind:
            continue
        if category not in ("", "全部") and item["category"] != category:
            continue
        if status not in ("", "全部") and item["status"] != status:
            continue
        if keyword != "":
            text = item["name"] + item["description"] + item["location"] + " ".join(item["keywords"])
            if keyword not in text:
                continue
        result.append(item)
    return sort_by_created(result)


def get_created_at(item):
    """排序用：取出建立時間"""
    return item.get("created_at", "")


def sort_by_created(items):
    """依建立時間新到舊排序"""
    return sorted(items, key=get_created_at, reverse=True)


def mark_resolved(item, nickname):
    """只有刊登者能把狀態改成「已尋回」；成功回傳 True（唯一改狀態的函式）"""
    if item["owner"] != nickname:
        return False
    item["status"] = "已尋回"
    return True


def mark_returned(item, thread, nickname):
    """拾獲物品：認領者在私訊中按「我已拿回」→ 物品改成已尋回。
    條件：這個討論串是這件物品的、按的人是認領者、而且拾獲者已判定驗證「通過」"""
    if item["kind"] != "拾獲" or item["status"] != "尋找中":
        return False
    if thread["target_type"] != "item" or thread["target_id"] != item["id"]:
        return False
    if nickname != thread["peer"] or thread["verified"] != "通過":
        return False
    item["status"] = "已尋回"
    return True


def day_gap(date_a, date_b):
    """計算兩個 'YYYY-MM-DD' 相差幾天；格式錯誤回傳 999"""
    try:
        a = datetime.strptime(date_a, "%Y-%m-%d")
        b = datetime.strptime(date_b, "%Y-%m-%d")
    except ValueError:
        return 999
    return abs((a - b).days)


def score_pair(item_a, item_b):
    """依配對評分表計算兩筆刊登的分數，並回傳每一項的得分明細"""
    detail = []
    score = 0

    if item_a["category"] == item_b["category"]:
        score = score + SCORE_CATEGORY
        detail.append("類別相同 +" + str(SCORE_CATEGORY))

    if item_a["location"] != "" and item_a["location"] == item_b["location"]:
        score = score + SCORE_LOCATION
        detail.append("地點相同 +" + str(SCORE_LOCATION))

    gap = day_gap(item_a["date"], item_b["date"])
    if gap <= 1:
        score = score + SCORE_DATE_CLOSE
        detail.append("日期相差 " + str(gap) + " 天 +" + str(SCORE_DATE_CLOSE))
    elif gap <= 3:
        score = score + SCORE_DATE_NEAR
        detail.append("日期相差 " + str(gap) + " 天 +" + str(SCORE_DATE_NEAR))

    shared = []
    text_b = item_b["name"] + " ".join(item_b["keywords"])
    for word in item_a["keywords"]:
        if word != "" and word in text_b and word not in shared:
            shared.append(word)
    keyword_score = len(shared) * SCORE_KEYWORD
    if keyword_score > MAX_KEYWORD_SCORE:
        keyword_score = MAX_KEYWORD_SCORE
    if keyword_score > 0:
        score = score + keyword_score
        detail.append("關鍵字重疊（" + "、".join(shared) + "）+" + str(keyword_score))

    return {"score": score, "detail": detail, "shared": shared, "gap": gap}


def get_score(match):
    """排序用：取出配對分數"""
    return match["score"]


def find_matches(item, items, limit=3):
    """找出與 item 相反種類、都在尋找中、分數 ≥ 門檻的候選，由高到低最多 limit 筆"""
    if item["status"] != "尋找中":
        return []
    candidates = []
    for other in items:
        if other["id"] == item["id"]:
            continue
        if other["kind"] == item["kind"]:
            continue
        if other["status"] != "尋找中":
            continue
        if other["owner"] == item["owner"]:
            continue
        result = score_pair(item, other)
        if result["gap"] > MAX_DAY_GAP:
            continue
        if result["score"] >= MATCH_THRESHOLD:
            candidates.append({"item": other, "score": result["score"], "detail": result["detail"]})
    candidates = sorted(candidates, key=get_score, reverse=True)
    return candidates[:limit]
