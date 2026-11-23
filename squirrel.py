# squirrel.py —— 中大松鼠：外觀、地圖上的位置、松果（積分）、徽章、排行榜
#
# 設計說明：
#   * 地圖上的松鼠位置是「你在網站上逛到哪裡」，不是真實 GPS 定位，也不會記錄真實位置
#   * 可以開「隱身」，別人就看不到你的松鼠
#   * 松果只是好玩的感謝點數，不能兌換金錢；而且一定由「受幫助的人」按下確認才會發出，
#     不能自己發給自己，降低灌分的動機
#
# 中央大學以「松」為精神象徵，所以積分叫「松果」🌰

import base64
from datetime import datetime, timedelta

from storage import now_text, today_text

import wardrobe

# 毛色與衣服的資料都在 wardrobe.py（衣櫃）
FUR_COLORS = {}
for _fur in wardrobe.FURS:
    FUR_COLORS[_fur["id"]] = _fur["colors"]
FREE_FURS = ["栗棕", "灰松", "橘紅", "奶茶", "巧克力"]

# 松果規則（數字集中在這裡，方便調整）
REWARD_RETURN_ITEM = 20      # 幫人找回失物（由失主確認）
REWARD_HELP_TASK = 10        # 完成別人的任務（由發布者確認）
REWARD_EXPLORE = 1           # 每天第一次走到某個區域
MAX_EXPLORE_PER_DAY = 5      # 探索松果每天最多 5 顆
ONLINE_MINUTES = 30          # 30 分鐘內有動作就算「在線上」

BADGES = [
    {"id": "newbie", "name": "初來乍到", "icon": "🌱", "desc": "拿到第一顆松果"},
    {"id": "explorer", "name": "校園探險家", "icon": "🧭", "desc": "走過 8 個以上的區域"},
    {"id": "honest", "name": "拾金不昧", "icon": "💎", "desc": "幫至少 1 位同學找回失物"},
    {"id": "helper", "name": "熱心松鼠", "icon": "🤝", "desc": "完成 3 個別人的任務"},
    {"id": "guardian", "name": "松林守護者", "icon": "🌲", "desc": "累積 100 顆松果"},
]


# ======================================================================
# 個人檔案（外觀＋位置）
# ======================================================================

def default_profile(nickname):
    """新使用者的預設松鼠"""
    return {
        "nickname": nickname,
        "fur": "栗棕",
        "owned": wardrobe.starter_items(),           # 擁有的衣服 id
        "owned_furs": list(FREE_FURS),               # 擁有的毛色
        "outfit": {"head": "", "face": "", "body": "", "hand": "", "back": ""},   # 每個部位穿什麼
        "visible": True,          # 是否在地圖上顯示
        "on_board": True,         # 是否出現在排行榜
        "zone": "gate",           # 一開始在正門
        "last_seen": now_text(),
        "visited_all": [],        # 曾經走過的區域
        "visited_date": today_text(),
        "visited_today": [],      # 今天走過的區域
    }


def normalize_profile(profile):
    """補齊舊資料缺少的欄位（例如舊版只有 accessory 一個配件）"""
    base = default_profile(profile["nickname"])
    for key in base:
        if key not in profile:
            profile[key] = base[key]
    for slot in wardrobe.SLOTS:
        if slot not in profile["outfit"]:
            profile["outfit"][slot] = ""
    old = profile.get("accessory", "")
    if old in wardrobe.LEGACY_ACCESSORY:
        item_id = wardrobe.LEGACY_ACCESSORY[old]
        item = wardrobe.get_item(item_id)
        if item_id not in profile["owned"]:
            profile["owned"].append(item_id)
        profile["outfit"][item["slot"]] = item_id
    if "accessory" in profile:
        del profile["accessory"]
    for fur in FREE_FURS:
        if fur not in profile["owned_furs"]:
            profile["owned_furs"].append(fur)
    return profile


def get_profile(profiles, nickname):
    """找某人的檔案（自動補齊欄位）；沒有就回傳預設值（尚未加入清單）"""
    for p in profiles:
        if p["nickname"] == nickname:
            return normalize_profile(p)
    return default_profile(nickname)


def save_profile(profiles, profile):
    """把檔案放回清單（有就取代、沒有就新增），回傳新清單"""
    result = []
    replaced = False
    for p in profiles:
        if p["nickname"] == profile["nickname"]:
            result.append(profile)
            replaced = True
        else:
            result.append(p)
    if not replaced:
        result.append(profile)
    return result


def move_to(profile, zone_id, today):
    """松鼠走到某區域：更新位置與足跡；回傳 True 代表「今天第一次來這裡」"""
    profile["zone"] = zone_id
    profile["last_seen"] = now_text()
    if profile.get("visited_date") != today:
        profile["visited_date"] = today
        profile["visited_today"] = []
    if zone_id not in profile["visited_all"]:
        profile["visited_all"].append(zone_id)
    if zone_id in profile["visited_today"]:
        return False
    profile["visited_today"].append(zone_id)
    return True


def is_online(profile, now):
    """最近 ONLINE_MINUTES 分鐘內有動作就算在線上"""
    try:
        t = datetime.strptime(profile["last_seen"], "%Y-%m-%d %H:%M")
    except (ValueError, KeyError, TypeError):
        return False
    return now - t <= timedelta(minutes=ONLINE_MINUTES)


# ======================================================================
# 松果
# ======================================================================

def add_pinecones(ledger, nickname, amount, reason, ref):
    """記一筆松果；同一個 ref 只會發一次（避免重複按按鈕灌分）。回傳 True 代表有發出"""
    for row in ledger:
        if row["ref"] == ref:
            return False
    ledger.append({"nickname": nickname, "amount": amount, "reason": reason, "ref": ref,
                   "created_at": now_text()})
    return True


def total_pinecones(ledger, nickname):
    """某人「目前持有」的松果（賺到的 − 花掉的）"""
    total = 0
    for row in ledger:
        if row["nickname"] == nickname:
            total = total + row["amount"]
    return total


def earned_pinecones(ledger, nickname):
    """某人「累計賺到」的松果（買東西不會減少，用在排行榜與徽章）"""
    total = 0
    for row in ledger:
        if row["nickname"] == nickname and row["amount"] > 0:
            total = total + row["amount"]
    return total


def count_reason(ledger, nickname, reason):
    """某人因為某種原因拿過幾次松果"""
    count = 0
    for row in ledger:
        if row["nickname"] == nickname and row["reason"] == reason:
            count = count + 1
    return count


def explore_reward(ledger, profile, zone_id, today):
    """探索獎勵：每天第一次到某區域 +1（每天最多 5 顆）。回傳拿到幾顆（每日任務改到 quests.py 領取）"""
    nickname = profile["nickname"]
    got = 0
    today_count = 0
    for row in ledger:
        if row["nickname"] == nickname and row["reason"] == "探索" and row["ref"].startswith("explore:" + today):
            today_count = today_count + 1
    if today_count < MAX_EXPLORE_PER_DAY:
        if add_pinecones(ledger, nickname, REWARD_EXPLORE, "探索", "explore:" + today + ":" + zone_id + ":" + nickname):
            got = got + REWARD_EXPLORE
    return got


def get_badges(ledger, profile):
    """依松果紀錄與足跡算出已解鎖的徽章 id"""
    nickname = profile["nickname"]
    unlocked = []
    total = earned_pinecones(ledger, nickname)
    if total >= 1:
        unlocked.append("newbie")
    if len(profile.get("visited_all", [])) >= 8:
        unlocked.append("explorer")
    if count_reason(ledger, nickname, "物歸原主") >= 1:
        unlocked.append("honest")
    if count_reason(ledger, nickname, "完成任務") >= 3:
        unlocked.append("helper")
    if total >= 100:
        unlocked.append("guardian")
    return unlocked


def get_total(row):
    """排序用"""
    return row["total"]


def leaderboard(ledger, profiles, limit):
    """松果排行榜：依「累計賺到」排序（只列出願意上榜的人）"""
    rows = []
    for p in profiles:
        if p.get("on_board", True):
            rows.append({"nickname": p["nickname"], "total": earned_pinecones(ledger, p["nickname"]),
                         "profile": normalize_profile(p)})
    rows = sorted(rows, key=get_total, reverse=True)
    return rows[:limit]


# ======================================================================
# 松鼠圖案（SVG）：Python 產生，地圖元件和個人頁共用同一份
# ======================================================================

def outfit_from(outfit):
    """把穿搭整理成 dict；也接受舊版的配件名稱字串（例如 "學士帽"）"""
    result = {"head": "", "face": "", "body": "", "hand": "", "back": ""}
    if isinstance(outfit, dict):
        for slot in result:
            result[slot] = outfit.get(slot, "")
    elif isinstance(outfit, str) and outfit in wardrobe.LEGACY_ACCESSORY:
        item = wardrobe.get_item(wardrobe.LEGACY_ACCESSORY[outfit])
        result[item["slot"]] = item["id"]
    return result


def layer_svg(outfit, slot):
    """取出某個部位那件衣服的 SVG；沒穿就回傳空字串"""
    item = wardrobe.get_item(outfit.get(slot, ""))
    if item is None:
        return ""
    return item["svg"]


def squirrel_svg(fur, outfit, size):
    """產生一隻松鼠的 SVG 字串（面向左邊）。outfit 是各部位穿搭；size 是顯示的像素大小"""
    colors = FUR_COLORS.get(fur, FUR_COLORS["栗棕"])
    main = colors[0]
    dark = colors[1]
    outfit = outfit_from(outfit)
    hand = layer_svg(outfit, "hand")
    back = layer_svg(outfit, "back")
    back_front = ""
    back_item = wardrobe.get_item(outfit["back"])
    if back_item is not None and back_item.get("front"):
        back_front = back      # 帆布袋、吉他這種「掛在身體前面」的，畫在上衣之後
        back = ""
    if hand == "":
        # 沒有拿東西時，抱著招牌松果
        hand = ('<ellipse cx="19" cy="42" rx="4" ry="5" fill="#8B5A2B"/>'
                '<path d="M15.5 40 L22.5 40 M15.5 43 L22.5 43 M16.5 46 L21.5 46" stroke="#5E3A17" stroke-width="0.9"/>')
    # 圖層順序：尾巴 → 背部 → 身體 → 上衣 → 頭 → 臉部 → 頭飾 → 手持 → 小手
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="' + str(size) + '" height="' + str(size) + '">'
        '<path d="M38 52 C62 54 66 26 52 14 C42 6 32 16 40 24 C47 30 47 40 36 44 Z" fill="' + dark + '"/>'
        '<path d="M41 48 C57 48 59 28 50 19 C45 14 39 18 44 23" fill="none" stroke="' + main + '" stroke-width="3" stroke-linecap="round"/>'
        + back +
        '<ellipse cx="29" cy="44" rx="12" ry="13" fill="' + main + '"/>'
        '<ellipse cx="25.5" cy="46" rx="6.5" ry="8.5" fill="#F6E7CF"/>'
        '<ellipse cx="23" cy="57" rx="4.5" ry="2.4" fill="' + dark + '"/>'
        '<ellipse cx="34" cy="57" rx="4.5" ry="2.4" fill="' + dark + '"/>'
        + layer_svg(outfit, "body") + back_front +
        '<path d="M14 21 L15 9 L22 16 Z" fill="' + main + '"/>'
        '<path d="M25 15 L30 5 L33 17 Z" fill="' + main + '"/>'
        '<path d="M27 15 L30 9 L31.5 16 Z" fill="#F2B9A6"/>'
        '<circle cx="23" cy="26" r="11" fill="' + main + '"/>'
        '<ellipse cx="15" cy="29" rx="5" ry="4" fill="#F6E7CF"/>'
        '<circle cx="19" cy="24.5" r="2.3" fill="#2B1D14"/><circle cx="19.7" cy="23.8" r="0.8" fill="#fff"/>'
        '<circle cx="11.5" cy="28" r="1.4" fill="#3A2418"/>'
        '<circle cx="17" cy="31" r="2.2" fill="#F4A3A3" opacity="0.75"/>'
        + layer_svg(outfit, "face")
        + layer_svg(outfit, "head")
        + hand +
        '<ellipse cx="21" cy="39.5" rx="2.6" ry="2" fill="' + main + '"/>'
        '</svg>'
    )


def profile_svg(profile, size):
    """依某人的檔案畫出他的松鼠"""
    return squirrel_svg(profile.get("fur", "栗棕"), profile.get("outfit", profile.get("accessory", "")), size)


def svg_to_img(svg, size):
    """把 SVG 轉成 <img> 標籤。
    為什麼要轉？Streamlit 的 st.html 會「消毒」HTML，直接放 <svg> 會被拿掉而顯示不出來；
    把 SVG 編碼成 data:image 網址放進 <img>，就能正常顯示。（base64 是 Python 標準函式庫）"""
    data = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return ('<img src="data:image/svg+xml;base64,' + data + '" width="' + str(size) + '" height="' + str(size)
            + '" style="display:inline-block;vertical-align:middle" alt="松鼠">')
