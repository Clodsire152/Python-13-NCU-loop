# campus_map.py —— 校園地圖：區域資料、地點 → 區域對應、地圖標記彙整
#
# 區域位置依 ncu_map_labeled_v3.png 的標記估算後，換算至 1000×640 畫布；
# 地圖仍是示意圖，並非測量比例。原圖未標出的宿舍與後門位置以畫布邊緣表示。
#
# 【避免雜亂的設計】參考其他校園地圖 App 的做法：
#   1. 不在地圖上一筆一個圖釘，而是「一個區域一個徽章」，徽章上只寫數量
#   2. 徽章用小色點表示種類（紅＝遺失、綠＝拾獲、橘＝任務、紫＝活動），可以用圖層開關隱藏
#   3. 只有「24 小時內新刊登」與「3 小時內截止的任務」才會有閃爍效果
#   4. 滑鼠移上去才顯示細節；點下去，右邊面板才列出完整清單

from datetime import datetime, timedelta

# 每個區域：id、名稱、圖示、中心座標 x/y、寬 w、高 h、形狀、對應的地點關鍵字
ZONES = [
    {"id": "gate", "name": "正門牌坊", "emoji": "⛩️", "x": 960, "y": 345, "w": 62, "h": 38, "shape": "gate",
     "aliases": ["正門牌坊", "正門", "牌樓", "中大路"]},
    {"id": "admin", "name": "行政大樓", "emoji": "🏛️", "x": 805, "y": 335, "w": 62, "h": 42, "shape": "building",
     "aliases": ["行政大樓", "行政"]},
    {"id": "library", "name": "圖書館區", "emoji": "📚", "x": 700, "y": 335, "w": 70, "h": 42, "shape": "building",
     "aliases": ["中正圖書館", "總圖書館", "圖書館", "總圖"]},
    {"id": "activity", "name": "大禮堂", "emoji": "🎸", "x": 627, "y": 337, "w": 54, "h": 38, "shape": "building",
     "aliases": ["大禮堂", "學生活動中心", "活動中心"]},
    {"id": "teaching", "name": "教研大樓", "emoji": "🏫", "x": 557, "y": 337, "w": 58, "h": 40, "shape": "building",
     "aliases": ["教學研究綜合大樓", "教研大樓"]},
    {"id": "lake", "name": "中大湖", "emoji": "🦆", "x": 500, "y": 115, "w": 104, "h": 72, "shape": "lake",
     "aliases": ["中大湖", "湖"]},
    {"id": "literature", "name": "文學院區", "emoji": "📖", "x": 770, "y": 245, "w": 80, "h": 48, "shape": "building",
     "aliases": ["人文社會科學大樓", "文學一館", "文學二館", "文學院", "文學"]},
    {"id": "science", "name": "科學一館", "emoji": "🔬", "x": 779, "y": 405, "w": 64, "h": 42, "shape": "building",
     "aliases": ["科學一館", "科一館", "科一", "科學館", "科學館區"]},
    {"id": "science2", "name": "科學二館", "emoji": "🔬", "x": 590, "y": 170, "w": 58, "h": 40, "shape": "building",
     "aliases": ["科學二館", "科二館", "科二"]},
    {"id": "science3", "name": "科學三館", "emoji": "🔬", "x": 608, "y": 113, "w": 58, "h": 40, "shape": "building",
     "aliases": ["科學三館", "科三館", "科三", "鴻經館"]},
    {"id": "science4", "name": "科學四館", "emoji": "🔬", "x": 545, "y": 46, "w": 58, "h": 40, "shape": "building",
     "aliases": ["科學四館", "科四館", "科四", "地科"]},
    {"id": "science5", "name": "科學五館", "emoji": "🔬", "x": 650, "y": 44, "w": 58, "h": 40, "shape": "building",
     "aliases": ["科學五館", "科五館", "科五"]},
    {"id": "engineering", "name": "工程一館", "emoji": "⚙️", "x": 653, "y": 416, "w": 60, "h": 42, "shape": "building",
     "aliases": ["工程一館", "工一館", "工一", "工程一", "工程館區", "工程"]},
    {"id": "engineering2", "name": "工程二館", "emoji": "⚙️", "x": 568, "y": 416, "w": 60, "h": 42, "shape": "building",
     "aliases": ["工程二館", "工二館", "工二", "工程二"]},
    {"id": "engineering3", "name": "工程三館", "emoji": "⚙️", "x": 292, "y": 385, "w": 60, "h": 42, "shape": "building",
     "aliases": ["工程三館", "工三館", "工三", "工程三"]},
    {"id": "engineering4", "name": "工程四館", "emoji": "⚙️", "x": 173, "y": 375, "w": 60, "h": 42, "shape": "building",
     "aliases": ["工程四館", "工四館", "工四", "工程四"]},
    {"id": "engineering5", "name": "工程五館", "emoji": "⚙️", "x": 164, "y": 526, "w": 60, "h": 42, "shape": "building",
     "aliases": ["工程五館", "工五館", "工五", "工程五"]},
    {"id": "guoding", "name": "國鼎光電", "emoji": "🔭", "x": 405, "y": 170, "w": 72, "h": 44, "shape": "building",
     "aliases": ["國鼎光電大樓", "國鼎"]},
    {"id": "management", "name": "管理學院", "emoji": "💼", "x": 750, "y": 105, "w": 72, "h": 44, "shape": "building",
     "aliases": ["管理二館", "管理學院", "管二館", "管院"]},
    {"id": "sports", "name": "運動中心／網球場", "emoji": "🏃", "x": 430, "y": 240, "w": 100, "h": 60, "shape": "field",
     "aliases": ["運動中心", "網球場", "體育館", "操場", "游泳池", "健身房", "大力館", "壘球場", "球場"]},
    {"id": "hakka", "name": "客家學院", "emoji": "🏫", "x": 405, "y": 83, "w": 80, "h": 50, "shape": "building",
     "aliases": ["客家學院", "客家學院大樓"]},
    {"id": "pool", "name": "室內游泳池", "emoji": "🏊", "x": 302, "y": 145, "w": 82, "h": 46, "shape": "building",
     "aliases": ["室內游泳池", "室內泳池"]},
    {"id": "north_facility", "name": "圖書／綜教", "emoji": "🏫", "x": 705, "y": 165, "w": 70, "h": 44, "shape": "building",
     "aliases": ["國際圖書資料館", "國際圖書館", "志希館", "綜教館"]},
    {"id": "eastgate", "name": "校史館／東側建築", "emoji": "🏛️", "x": 870, "y": 440, "w": 70, "h": 60, "shape": "building",
     "aliases": ["校史館", "播憩樓"]},
    {"id": "dorm", "name": "宿舍區（圖外）", "emoji": "🛏️", "x": 55, "y": 590, "w": 88, "h": 44, "shape": "building",
     "aliases": ["宿舍", "舍", "研舍", "ihouse"]},
    {"id": "canteen", "name": "松苑／南側生活區", "emoji": "🍱", "x": 465, "y": 505, "w": 86, "h": 40, "shape": "building",
     "aliases": ["產學營運中心", "松苑", "學生餐廳", "餐廳", "便利商店", "郵局", "超商"]},
    {"id": "pinecone_hall", "name": "松果館", "emoji": "🌰", "x": 810, "y": 590, "w": 62, "h": 38, "shape": "building",
     "aliases": ["松果館"]},
    {"id": "play_hall", "name": "游藝館", "emoji": "🎭", "x": 890, "y": 555, "w": 68, "h": 42, "shape": "building",
     "aliases": ["游藝館"]},
    {"id": "backgate", "name": "南側道路出口", "emoji": "🌙", "x": 510, "y": 610, "w": 70, "h": 36, "shape": "gate",
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
