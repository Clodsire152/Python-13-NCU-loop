# campus_map.py —— 校園地圖：區域資料、地點 → 區域對應、地圖標記彙整
#
# ⚠️ 這是「示意地圖」，不是實際比例。區域的 x、y 座標請全組依真實校園相對位置調整。
#    （地圖畫布大小：寬 1000、高 640，左上角是 (0, 0)）
#
# 【避免雜亂的設計】參考其他校園地圖 App 的做法：
#   1. 不在地圖上一筆一個圖釘，而是「一個區域一個徽章」，徽章上只寫數量
#   2. 徽章用小色點表示種類（紅＝遺失、綠＝拾獲、橘＝任務、紫＝活動），可以用圖層開關隱藏
#   3. 只有「24 小時內新刊登」與「3 小時內截止的任務」才會有閃爍效果
#   4. 滑鼠移上去才顯示細節；點下去，右邊面板才列出完整清單

from datetime import datetime, timedelta

# 每個區域：id、名稱、圖示、中心座標 x/y、寬 w、高 h、形狀、對應的地點關鍵字
ZONES = [
    {"id": "gate", "name": "正門牌樓", "emoji": "⛩️", "x": 120, "y": 560, "w": 110, "h": 50, "shape": "gate",
     "aliases": ["正門", "牌樓", "中大路"]},
    {"id": "admin", "name": "行政大樓", "emoji": "🏛️", "x": 270, "y": 455, "w": 120, "h": 64, "shape": "building",
     "aliases": ["行政大樓", "行政"]},
    {"id": "library", "name": "總圖書館", "emoji": "📚", "x": 470, "y": 360, "w": 150, "h": 84, "shape": "building",
     "aliases": ["圖書館", "總圖"]},
    {"id": "activity", "name": "學生活動中心", "emoji": "🎸", "x": 660, "y": 290, "w": 140, "h": 70, "shape": "building",
     "aliases": ["學生活動中心", "活動中心", "松苑"]},
    {"id": "lake", "name": "中大湖", "emoji": "🦆", "x": 300, "y": 230, "w": 200, "h": 110, "shape": "lake",
     "aliases": ["中大湖", "湖"]},
    {"id": "literature", "name": "文學院", "emoji": "📖", "x": 500, "y": 120, "w": 130, "h": 64, "shape": "building",
     "aliases": ["文學院", "文學"]},
    {"id": "science", "name": "科學館區", "emoji": "🔬", "x": 730, "y": 130, "w": 140, "h": 70, "shape": "building",
     "aliases": ["科學館", "科一", "科二", "科三", "科四", "地科"]},
    {"id": "engineering", "name": "工程館區", "emoji": "⚙️", "x": 800, "y": 420, "w": 150, "h": 80, "shape": "building",
     "aliases": ["工程", "工一", "工二", "工三", "工四", "工五", "教學研究綜合大樓", "國鼎"]},
    {"id": "management", "name": "管理學院", "emoji": "💼", "x": 905, "y": 270, "w": 120, "h": 64, "shape": "building",
     "aliases": ["管理學院", "管院"]},
    {"id": "sports", "name": "體育館與操場", "emoji": "🏃", "x": 130, "y": 330, "w": 150, "h": 120, "shape": "field",
     "aliases": ["體育館", "操場", "游泳池", "健身房", "運動中心", "壘球場", "球場"]},
    {"id": "dorm", "name": "宿舍區", "emoji": "🛏️", "x": 910, "y": 90, "w": 120, "h": 80, "shape": "building",
     "aliases": ["宿舍", "舍", "研舍", "ihouse"]},
    {"id": "canteen", "name": "學生餐廳", "emoji": "🍱", "x": 600, "y": 540, "w": 130, "h": 64, "shape": "building",
     "aliases": ["餐廳", "便利商店", "郵局", "超商"]},
    {"id": "backgate", "name": "後門宵夜街", "emoji": "🌙", "x": 890, "y": 575, "w": 140, "h": 50, "shape": "gate",
     "aliases": ["後門", "宵夜街", "中央路"]},
]

LAYER_NAMES = {"lost": "遺失", "found": "拾獲", "task": "任務", "event": "活動"}


def get_zone(zone_id):
    """用 id 找區域，找不到回傳 None"""
    for zone in ZONES:
        if zone["id"] == zone_id:
            return zone
    return None


def zone_name(zone_id):
    """用 id 取得區域中文名稱"""
    zone = get_zone(zone_id)
    if zone is None:
        return "未知地點"
    return zone["name"]


def location_to_zone(location):
    """把使用者填的地點文字（例如「圖書館三樓」）對應到區域 id；對不到回傳空字串"""
    if location is None:
        return ""
    best_id = ""
    best_len = 0
    for zone in ZONES:
        for alias in zone["aliases"]:
            # 選「最長」的相符別名，避免「工程」「工五」之類互相搶
            if alias in location and len(alias) > best_len:
                best_id = zone["id"]
                best_len = len(alias)
    return best_id


def parse_time(text):
    """把 'YYYY-MM-DD HH:MM' 轉成 datetime；失敗回傳 None"""
    try:
        return datetime.strptime(text, "%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return None


def is_new(created_at, now):
    """24 小時內建立的就算「新」"""
    t = parse_time(created_at)
    if t is None:
        return False
    return now - t <= timedelta(hours=24)


def is_urgent(deadline, now):
    """3 小時內就要截止的任務算「急」"""
    t = parse_time(deadline)
    if t is None:
        return False
    return now <= t <= now + timedelta(hours=3)


def empty_zone_info(zone):
    """建立一個區域在地圖上的初始資料"""
    return {
        "id": zone["id"], "name": zone["name"], "emoji": zone["emoji"],
        "x": zone["x"], "y": zone["y"], "w": zone["w"], "h": zone["h"], "shape": zone["shape"],
        "counts": {"lost": 0, "found": 0, "task": 0, "event": 0},
        "new": False, "urgent": False,
        "titles": [],
    }


def add_title(info, layer, text):
    """在提示框裡最多放 4 個標題"""
    if len(info["titles"]) < 4:
        info["titles"].append({"type": layer, "text": text[:16]})


def build_zone_infos(items, tasks, events, now=None):
    """把失物、任務、活動彙整成「每個區域一筆」的地圖資料（只算還在進行中的）"""
    if now is None:
        now = datetime.now()
    infos = {}
    for zone in ZONES:
        infos[zone["id"]] = empty_zone_info(zone)

    for item in items:
        if item["status"] != "尋找中":
            continue
        zid = location_to_zone(item["location"])
        if zid == "":
            continue
        layer = "lost"
        if item["kind"] == "拾獲":
            layer = "found"
        infos[zid]["counts"][layer] = infos[zid]["counts"][layer] + 1
        add_title(infos[zid], layer, item["name"])
        if is_new(item["created_at"], now):
            infos[zid]["new"] = True

    for task in tasks:
        if task["status"] != "招募中":
            continue
        zid = location_to_zone(task["location"])
        if zid == "":
            continue
        infos[zid]["counts"]["task"] = infos[zid]["counts"]["task"] + 1
        add_title(infos[zid], "task", task["title"])
        if is_urgent(task["deadline"], now):
            infos[zid]["urgent"] = True

    now_text = now.strftime("%Y-%m-%d %H:%M")
    for event in events:
        if event["end"] < now_text:
            continue
        zid = location_to_zone(event["place"])
        if zid == "":
            continue
        infos[zid]["counts"]["event"] = infos[zid]["counts"]["event"] + 1
        add_title(infos[zid], "event", event["title"].replace("（虛構）", ""))
        if is_new(event["created_at"], now):
            infos[zid]["new"] = True

    result = []
    for zone in ZONES:
        result.append(infos[zone["id"]])
    return result


def unmapped_count(items, tasks, events):
    """算出有幾筆資料的地點對不到任何區域（提醒使用者寫清楚地點）"""
    count = 0
    for item in items:
        if item["status"] == "尋找中" and location_to_zone(item["location"]) == "":
            count = count + 1
    for task in tasks:
        if task["status"] == "招募中" and location_to_zone(task["location"]) == "":
            count = count + 1
    for event in events:
        if location_to_zone(event["place"]) == "":
            count = count + 1
    return count


def search_zones(items, tasks, events, keyword):
    """地圖搜尋：回傳「有符合關鍵字資料」的區域 id 清單"""
    keyword = keyword.strip()
    if keyword == "":
        return []
    found = []
    for item in items:
        text = item["name"] + item["description"] + " ".join(item["keywords"])
        if item["status"] == "尋找中" and keyword in text:
            zid = location_to_zone(item["location"])
            if zid != "" and zid not in found:
                found.append(zid)
    for task in tasks:
        text = task["title"] + task["description"] + " ".join(task["keywords"])
        if task["status"] == "招募中" and keyword in text:
            zid = location_to_zone(task["location"])
            if zid != "" and zid not in found:
                found.append(zid)
    for event in events:
        text = event["title"] + event["description"] + " ".join(event["tags"])
        if keyword in text:
            zid = location_to_zone(event["place"])
            if zid != "" and zid not in found:
                found.append(zid)
    return found


def items_in_zone(records, zone_id, field):
    """從清單中挑出位在某個區域的資料（field 是地點欄位名稱：location 或 place）"""
    result = []
    for r in records:
        if location_to_zone(r[field]) == zone_id:
            result.append(r)
    return result


def build_map_args(items, tasks, events, profiles, me_name, selected, highlight, now=None):
    """組出要傳給地圖元件的全部資料（區域徽章、我的松鼠、其他松鼠）"""
    import squirrel   # 放在函式裡匯入，避免兩個檔案互相匯入
    if now is None:
        now = datetime.now()
    me_info = None
    others = []
    for p in profiles:
        p = squirrel.normalize_profile(p)
        svg = squirrel.profile_svg(p, 64)
        if p["nickname"] == me_name:
            me_info = {"name": p["nickname"], "zone": p.get("zone", "gate"), "svg": svg}
        elif p.get("visible", True):
            others.append({"name": p["nickname"], "zone": p.get("zone", "gate"), "svg": svg,
                           "online": squirrel.is_online(p, now)})
    if me_name != "" and me_info is None:
        d = squirrel.default_profile(me_name)
        me_info = {"name": me_name, "zone": d["zone"], "svg": squirrel.profile_svg(d, 64)}
    return {
        "zones": build_zone_infos(items, tasks, events, now),
        "me": me_info,
        "others": others,
        "selected": selected,
        "highlight": highlight,
    }
