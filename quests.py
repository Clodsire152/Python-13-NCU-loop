# quests.py —— 松果任務系統：每日簽到、今日金松果點、每日任務、每週任務、徽章獎勵
#
# 【防灌分設計】（評審可能會問：「這樣大家不會為了松果亂刊登嗎？」）
#   1. 「刊登」本身不給松果 → 沒有理由發假刊登
#   2. 幫助別人的大額松果，一定由「被幫助的人」確認才發（見 squirrel.py）
#   3. 每個任務每天／每週只能領一次（用 ref 去重複），探索松果每天有上限
#   4. 簽到連續天數的加成有上限
#
# 每天的「金松果點」和「每日任務」用日期算出來（hashlib），所以同一天大家看到的都一樣，
# 不需要另外存設定，也不需要伺服器排程。

import hashlib
from datetime import datetime, timedelta

import campus_map
import squirrel

# ---------------- 數字設定（要調整獎勵就改這裡） ----------------
CHECKIN_BASE = 5            # 每日簽到基本松果
CHECKIN_STREAK_MAX = 5      # 連續簽到加成最多 +5
CHECKIN_DAY7_BONUS = 20     # 每連續 7 天額外 +20
TREASURE_COUNT = 3          # 每天幾個金松果點
TREASURE_REWARD = 3         # 撿到一顆金松果
DAILY_PICK = 3              # 每天從題庫抽幾個任務

# 每天固定的任務
DAILY_FIXED = [
    {"id": "walk3", "icon": "🐾", "name": "松鼠散步", "desc": "在地圖上走過 3 個不同區域", "counter": "visit", "goal": 3, "reward": 5},
    {"id": "treasure_all", "icon": "✨", "name": "尋寶達人", "desc": "撿齊今天全部 3 顆金松果", "counter": "treasure", "goal": 3, "reward": 10},
]
# 每天從這裡抽 3 個
DAILY_POOL = [
    {"id": "interest", "icon": "🎪", "name": "活動探險家", "desc": "對 1 個活動按「有興趣」", "counter": "interest", "goal": 1, "reward": 3},
    {"id": "reply", "icon": "💬", "name": "熱心回覆", "desc": "在私訊回覆 1 則訊息", "counter": "message", "goal": 1, "reward": 3},
    {"id": "search", "icon": "🔍", "name": "地圖偵探", "desc": "用地圖搜尋找 1 次東西", "counter": "search", "goal": 1, "reward": 2},
    {"id": "match", "icon": "🧩", "name": "配對小幫手", "desc": "查看 1 次失物配對", "counter": "match", "goal": 1, "reward": 2},
    {"id": "patrol", "icon": "🔎", "name": "失物巡邏", "desc": "走到 2 個有失物刊登的區域", "counter": "lf_zone", "goal": 2, "reward": 4},
    {"id": "dress", "icon": "👗", "name": "換個造型", "desc": "換一次松鼠的穿搭", "counter": "dress", "goal": 1, "reward": 2},
    {"id": "task_browse", "icon": "🤝", "name": "看看誰需要幫忙", "desc": "走到 2 個有任務的區域", "counter": "task_zone", "goal": 2, "reward": 4},
    {"id": "event_zone", "icon": "🎶", "name": "活動巡禮", "desc": "走到 1 個有活動的區域", "counter": "event_zone", "goal": 1, "reward": 2},
]
# 每週任務（週一重置）
WEEKLY = [
    {"id": "checkin5", "icon": "📅", "name": "勤勞松鼠", "desc": "本週簽到 5 天", "counter": "checkin", "goal": 5, "reward": 30},
    {"id": "explore8", "icon": "🗺️", "name": "環校之旅", "desc": "本週走過 8 個不同區域", "counter": "zones", "goal": 8, "reward": 25},
    {"id": "help1", "icon": "🤝", "name": "伸出援手", "desc": "本週完成 1 個別人的任務（發布者確認）", "counter": "help_task", "goal": 1, "reward": 20},
    {"id": "return1", "icon": "💎", "name": "失物英雄", "desc": "本週幫 1 位同學找回失物（失主確認）", "counter": "return_item", "goal": 1, "reward": 30},
]
# 解鎖徽章時可以領的一次性獎勵
BADGE_REWARDS = {"newbie": 5, "explorer": 20, "honest": 30, "helper": 30, "guardian": 50}


# ======================================================================
# 日期工具
# ======================================================================

def week_key(today):
    """'2026-11-23' → '2026-W48'（週一開始算）"""
    d = datetime.strptime(today, "%Y-%m-%d")
    iso = d.isocalendar()
    return str(iso[0]) + "-W" + str(iso[1]).zfill(2)


def yesterday_of(today):
    """前一天的日期字串"""
    d = datetime.strptime(today, "%Y-%m-%d") - timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def date_number(text):
    """把文字變成一個固定的大數字（同樣的文字一定得到同樣的數字）"""
    return int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)


def pick_from(options, count, seed_text):
    """用 seed_text 決定，從 options 中挑出 count 個不重複的（每天固定）"""
    remaining = list(options)
    picked = []
    n = date_number(seed_text)
    while len(picked) < count and len(remaining) > 0:
        index = n % len(remaining)
        picked.append(remaining[index])
        remaining.pop(index)
        n = n // 7 + 13
    return picked


# ======================================================================
# 個人任務進度（存在 profile 裡）
# ======================================================================

def ensure_progress(profile, today):
    """確保 profile 裡有「今天」與「本週」的進度；換日／換週就歸零"""
    week = week_key(today)
    daily = profile.get("daily")
    if daily is None or daily.get("date") != today:
        profile["daily"] = {"date": today, "counters": {}, "claimed": [], "treasures": [], "seen_zones": []}
    weekly = profile.get("weekly")
    if weekly is None or weekly.get("week") != week:
        profile["weekly"] = {"week": week, "counters": {}, "claimed": [], "zones": []}
    if "checkin" not in profile:
        profile["checkin"] = {"last": "", "streak": 0}
    if "badge_claimed" not in profile:
        profile["badge_claimed"] = []
    return profile


def bump(profile, counter, today, amount=1):
    """某個計數 +amount（同時記到今天與本週）"""
    ensure_progress(profile, today)
    daily = profile["daily"]["counters"]
    weekly = profile["weekly"]["counters"]
    daily[counter] = daily.get(counter, 0) + amount
    weekly[counter] = weekly.get(counter, 0) + amount
    return profile


def get_count(profile, quest, scope):
    """某個任務目前的進度數字"""
    if scope == "weekly" and quest["counter"] == "zones":
        return len(profile["weekly"]["zones"])
    if scope == "daily" and quest["counter"] == "visit":
        if profile.get("visited_date") == profile["daily"]["date"]:
            return len(profile.get("visited_today", []))
        return 0
    if scope == "daily" and quest["counter"] == "treasure":
        return len(profile["daily"]["treasures"])
    if scope == "daily":
        return profile["daily"]["counters"].get(quest["counter"], 0)
    return profile["weekly"]["counters"].get(quest["counter"], 0)


def today_quests(today):
    """今天的每日任務：固定 2 個＋題庫抽 3 個"""
    return DAILY_FIXED + pick_from(DAILY_POOL, DAILY_PICK, "daily:" + today)


def quest_status(profile, quest, scope):
    """回傳 {"count", "goal", "done", "claimed"}"""
    count = get_count(profile, quest, scope)
    if scope == "daily":
        claimed = quest["id"] in profile["daily"]["claimed"]
    else:
        claimed = quest["id"] in profile["weekly"]["claimed"]
    shown = count
    if shown > quest["goal"]:
        shown = quest["goal"]
    return {"count": shown, "goal": quest["goal"], "done": count >= quest["goal"], "claimed": claimed}


def claim_quest(profile, ledger, quest, scope, today):
    """領取任務獎勵；沒完成或已領過回傳 0"""
    ensure_progress(profile, today)
    status = quest_status(profile, quest, scope)
    if not status["done"] or status["claimed"]:
        return 0
    if scope == "daily":
        ref = "quest:daily:" + today + ":" + quest["id"] + ":" + profile["nickname"]
        reason = "每日任務"
    else:
        ref = "quest:weekly:" + profile["weekly"]["week"] + ":" + quest["id"] + ":" + profile["nickname"]
        reason = "每週任務"
    if not squirrel.add_pinecones(ledger, profile["nickname"], quest["reward"], reason, ref):
        return 0
    if scope == "daily":
        profile["daily"]["claimed"].append(quest["id"])
    else:
        profile["weekly"]["claimed"].append(quest["id"])
    return quest["reward"]


def claimable_count(profile, today):
    """有幾個任務「完成了但還沒領」（用來在選單顯示紅點）"""
    ensure_progress(profile, today)
    n = 0
    for q in today_quests(today):
        s = quest_status(profile, q, "daily")
        if s["done"] and not s["claimed"]:
            n = n + 1
    for q in WEEKLY:
        s = quest_status(profile, q, "weekly")
        if s["done"] and not s["claimed"]:
            n = n + 1
    return n


# ======================================================================
# 每日簽到
# ======================================================================

def checkin_reward(streak):
    """連續第 streak 天簽到可以拿幾顆"""
    bonus = streak - 1
    if bonus > CHECKIN_STREAK_MAX:
        bonus = CHECKIN_STREAK_MAX
    total = CHECKIN_BASE + bonus
    if streak % 7 == 0:
        total = total + CHECKIN_DAY7_BONUS
    return total


def has_checked_in(profile, today):
    """今天簽到過了嗎"""
    ensure_progress(profile, today)
    return profile["checkin"]["last"] == today


def next_streak(profile, today):
    """如果今天簽到，會是連續第幾天"""
    ensure_progress(profile, today)
    if profile["checkin"]["last"] == yesterday_of(today):
        return profile["checkin"]["streak"] + 1
    if profile["checkin"]["last"] == today:
        return profile["checkin"]["streak"]
    return 1


def do_checkin(profile, ledger, today):
    """簽到：回傳拿到的松果（今天已簽過回傳 0）"""
    if has_checked_in(profile, today):
        return 0
    streak = next_streak(profile, today)
    amount = checkin_reward(streak)
    if not squirrel.add_pinecones(ledger, profile["nickname"], amount, "每日簽到",
                                  "checkin:" + today + ":" + profile["nickname"]):
        return 0
    profile["checkin"] = {"last": today, "streak": streak}
    bump(profile, "checkin", today)
    return amount


# ======================================================================
# 今日金松果點（走到特定地點）
# ======================================================================

def treasure_zones(today):
    """今天的 3 個金松果點（每天不同，大家一樣）"""
    ids = []
    for z in campus_map.ZONES:
        ids.append(z["id"])
    return pick_from(ids, TREASURE_COUNT, "treasure:" + today)


def remaining_treasures(profile, today):
    """這個人今天還沒撿的金松果點"""
    ensure_progress(profile, today)
    result = []
    for zid in treasure_zones(today):
        if zid not in profile["daily"]["treasures"]:
            result.append(zid)
    return result


def collect_treasure(profile, ledger, zone_id, today):
    """走到金松果點就撿起來；回傳拿到幾顆（不是金松果點或已撿過回傳 0）"""
    ensure_progress(profile, today)
    if zone_id not in treasure_zones(today) or zone_id in profile["daily"]["treasures"]:
        return 0
    if not squirrel.add_pinecones(ledger, profile["nickname"], TREASURE_REWARD, "金松果",
                                  "treasure:" + today + ":" + zone_id + ":" + profile["nickname"]):
        return 0
    profile["daily"]["treasures"].append(zone_id)
    return TREASURE_REWARD


def record_zone_visit(profile, zone_id, zone_info, today):
    """走到某區域時，更新「本週走過的區域」與「有失物／任務／活動的區域」計數（同一區每天只算一次）"""
    ensure_progress(profile, today)
    if zone_id not in profile["weekly"]["zones"]:
        profile["weekly"]["zones"].append(zone_id)
    if zone_id in profile["daily"]["seen_zones"]:
        return profile
    profile["daily"]["seen_zones"].append(zone_id)
    if zone_info is None:
        return profile
    counts = zone_info["counts"]
    if counts["lost"] + counts["found"] > 0:
        bump(profile, "lf_zone", today)
    if counts["task"] > 0:
        bump(profile, "task_zone", today)
    if counts["event"] > 0:
        bump(profile, "event_zone", today)
    return profile


# ======================================================================
# 徽章獎勵
# ======================================================================

def claim_badge(profile, ledger, badge_id, today):
    """領取徽章的一次性獎勵；沒解鎖或領過回傳 0"""
    ensure_progress(profile, today)
    if badge_id not in squirrel.get_badges(ledger, profile) or badge_id in profile["badge_claimed"]:
        return 0
    amount = BADGE_REWARDS.get(badge_id, 0)
    if amount == 0:
        return 0
    if not squirrel.add_pinecones(ledger, profile["nickname"], amount, "徽章獎勵",
                                  "badge:" + badge_id + ":" + profile["nickname"]):
        return 0
    profile["badge_claimed"].append(badge_id)
    return amount
