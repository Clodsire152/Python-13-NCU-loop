# tests/test_core.py —— 不需要 Streamlit 的核心邏輯測試
# 執行方式（在 ncu-loop 資料夾裡）：python tests/test_core.py
# 每個 test_ 開頭的函式都會被執行；全部通過會印出「全部通過」

import os
import sys

# 讓測試找得到上一層的程式檔
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["USE_AI"] = "false"      # 測試一律用規則版，結果才穩定

from datetime import datetime, timedelta

import storage
import auth
import lostfound
import tasks
import events
import chat
import ai_helper
import campus_map
import squirrel
import quests
import shop
import wardrobe


def day(offset):
    """今天 + offset 天"""
    return (datetime.now() + timedelta(days=offset)).strftime("%Y-%m-%d")


def sample_items():
    """測試用的失物資料"""
    lost = lostfound.create_item("遺失", "黑色保溫水壺", "雨傘水壺", "圖書館", day(-1), "三樓掉的",
                                 ["黑色", "保溫水壺", "水壺"], "小宇", [], [])
    lost["id"] = 1
    found = lostfound.create_item("拾獲", "黑色保溫水壺", "雨傘水壺", "圖書館", day(-1), "瓶身有貼紙",
                                  ["黑色", "水壺", "貼紙"], "小晴", ["貼紙圖案？", "刮痕？"], ["貓咪", "瓶蓋"])
    found["id"] = 2
    umbrella = lostfound.create_item("拾獲", "藍色折疊傘", "雨傘水壺", "工程一館", day(-20), "",
                                     ["藍色", "傘"], "小凱", ["q", "q"], ["a", "a"])
    umbrella["id"] = 3
    return [lost, found, umbrella]


# ---------------- storage ----------------

def test_storage_roundtrip():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp.json")
    storage.save_data(path, [{"id": 1, "text": "中文"}])
    assert storage.load_data(path) == [{"id": 1, "text": "中文"}]
    os.remove(path)
    assert storage.load_data(path) == []          # 不存在回傳 []


def test_next_id():
    assert storage.get_next_id([]) == 1
    assert storage.get_next_id([{"id": 3}, {"id": 7}]) == 8


# ---------------- auth ----------------

def test_register_and_login():
    users = []
    r = auth.register_user(users, "小宇", "abc123")
    assert r["ok"]
    assert "abc123" not in str(r["user"])          # 不存明碼
    users.append(r["user"])
    assert auth.login_user(users, "小宇", "abc123")
    assert not auth.login_user(users, "小宇", "wrong!")
    assert not auth.register_user(users, "小宇", "abc123")["ok"]   # 重複
    assert not auth.register_user(users, "A", "abc123")["ok"]      # 太短
    assert not auth.register_user(users, "小晴", "123")["ok"]       # 密碼太短


def test_salt_differs():
    a = auth.register_user([], "甲甲", "same123")["user"]
    b = auth.register_user([], "乙乙", "same123")["user"]
    assert a["password_hash"] != b["password_hash"]    # 加鹽：同密碼不同雜湊


# ---------------- 失物招領 ----------------

def test_match_score_hand_example():
    items = sample_items()
    result = lostfound.score_pair(items[0], items[1])
    # 類別 +3、地點 +2、同一天 +2、關鍵字（黑色、水壺；保溫水壺也在對方名稱中）最多 +3
    assert result["score"] == 10, result


def test_find_matches_rules():
    items = sample_items()
    matches = lostfound.find_matches(items[0], items)
    assert len(matches) == 1                       # 雨傘相差 >7 天、類型也不同物品 → 不列入
    assert matches[0]["item"]["id"] == 2
    assert lostfound.find_matches(items[1], [items[1]]) == []   # 不會和自己配對


def test_mark_resolved_only_owner():
    items = sample_items()
    assert not lostfound.mark_resolved(items[0], "小晴")
    assert lostfound.mark_resolved(items[0], "小宇")
    assert items[0]["status"] == "已尋回"
    assert lostfound.find_matches(items[1], items) == []        # 已尋回不再配對


def test_search_items():
    items = sample_items()
    assert len(lostfound.search_items(items, "拾獲", "全部", "", "全部")) == 2
    assert len(lostfound.search_items(items, "全部", "全部", "傘", "全部")) == 1


# ---------------- 任務互助 ----------------

def test_task_flow():
    t = tasks.create_task("揪人", "羽球", "", "體育館", day(1) + " 10:00", "", 2, [], "小凱")
    assert not tasks.accept_task(t, "小凱")["ok"]                 # 不能接自己的
    assert tasks.accept_task(t, "小宇")["ok"]
    assert not tasks.accept_task(t, "小宇")["ok"]                 # 不能重複
    assert t["status"] == "招募中"
    assert tasks.accept_task(t, "小安")["ok"]
    assert t["status"] == "已額滿"
    assert not tasks.accept_task(t, "小晴")["ok"]                 # 額滿
    assert not tasks.complete_task(t, "小宇")                     # 只有發布者
    assert tasks.complete_task(t, "小凱")
    assert not tasks.cancel_task(t, "小凱")                       # 已完成不能取消


def test_task_rules():
    assert ai_helper.check_task_rules("幫我代考微積分", "")["data"]["level"] == "禁止"
    assert ai_helper.check_task_rules("幫買菸", "")["data"]["level"] == "禁止"
    assert ai_helper.check_task_rules("借我帳號密碼", "")["data"]["level"] == "禁止"
    assert ai_helper.check_task_rules("幫買便當", "請先匯款給我")["data"]["level"] == "提醒"
    assert ai_helper.check_task_rules("幫帶一杯飲料", "到圖書館")["data"]["level"] == "通過"


# ---------------- 活動 ----------------

def test_events():
    e1 = events.create_event("攝影體驗", "攝影社", "社團招生", "活動中心", day(3) + " 18:00", day(3) + " 20:00",
                             "", ["攝影", "新生"], "javascript:alert(1)", "小晴")
    e1["id"] = 1
    e2 = events.create_event("舊比賽", "", "運動競賽", "", day(-3) + " 18:00", day(-3) + " 20:00", "", [], "", "小凱")
    e2["id"] = 2
    assert e1["link"] == ""                                       # 非 http(s) 連結被拿掉
    assert len(events.list_events([e1, e2], "全部", "", True)) == 1
    events.toggle_interest(e1, "小宇")
    assert e1["interested"] == ["小宇"]
    events.toggle_interest(e1, "小宇")
    assert e1["interested"] == []
    rec = ai_helper.recommend_events([e1, e2], "喜歡攝影")
    assert rec["source"] == "規則"
    assert rec["data"][0]["event"]["id"] == 1


# ---------------- 私訊 ----------------

def test_chat_flow():
    items = sample_items()
    found = items[1]
    assert chat.open_thread([], "item", found, "小晴", []) is None   # 不能私訊自己
    th = chat.open_thread([], "item", found, "小宇", ["貓咪", "刮痕"])
    th["id"] = 1
    assert th["verified"] == "未驗證"
    assert chat.open_thread([th], "item", found, "小宇", []) is th   # 回傳舊的
    th = chat.send_message(th, "小凱", "我是路人", "user")
    assert len(th["messages"]) == 0                                  # 非參與者
    th = chat.send_message(th, "小宇", "   ", "user")
    assert len(th["messages"]) == 0                                  # 空白
    th = chat.send_message(th, "小宇", "你好", "user")
    assert len(chat.get_new_messages(th, 0)) == 1
    th = chat.propose_meetup(th, "小宇", "圖書館一樓服務台前", day(1) + " 12:10")
    assert th["meetup"]["status"] == "待確認"
    th = chat.confirm_meetup(th, "小宇")                              # 提出者不能自己確認
    assert th["meetup"]["status"] == "待確認"
    th = chat.confirm_meetup(th, "小晴")
    assert th["meetup"]["status"] == "已確認"
    th = chat.verify_claim(th, "小宇", True)                          # 認領者不能自己判定
    assert th["verified"] == "未驗證"
    th = chat.verify_claim(th, "小晴", True)
    assert th["verified"] == "通過"
    lost_thread = chat.open_thread([], "item", items[0], "小晴", ["x"])
    assert lost_thread["verified"] == "不適用" and lost_thread["claim_answers"] == []


def test_block_and_report():
    blocks = chat.block_user([], "小宇", "小凱")
    assert chat.is_blocked(blocks, "小凱", "小宇")
    assert not chat.is_blocked(blocks, "小宇", "小晴")
    th = {"id": 5, "owner": "小晴", "peer": "小宇"}
    r = chat.create_report([], th, "小宇", "騷擾或不當言語", "")
    assert r["reported"] == "小晴" and r["thread_id"] == 5


# ---------------- AI 能力層（規則版） ----------------

def test_privacy_guard():
    text = "我的學號 112502001，手機 0912-345-678，信箱 abc@g.ncu.edu.tw，身分證 A123456789"
    types = []
    for f in ai_helper.detect_sensitive(text):
        types.append(f["type"])
    for t in ["學號", "手機", "Email", "身分證"]:
        assert t in types, types
    masked = ai_helper.mask_sensitive(text)
    for secret in ["112502001", "0912-345-678", "abc@g.ncu.edu.tw", "A123456789"]:
        assert secret not in masked


def test_scam_detect():
    assert len(ai_helper.detect_scam_risk("請先匯款運費給我")) > 0
    assert len(ai_helper.detect_scam_risk("把簡訊驗證碼給我")) > 0
    assert len(ai_helper.detect_scam_risk("加賴聊比較快")) > 0
    assert ai_helper.detect_scam_risk("明天中午圖書館見") == []


def test_parse_item_sentence():
    r = ai_helper.parse_form_text("昨天下午在圖書館掉了黑色保溫水壺", "item")
    d = r["data"]
    assert r["source"] == "規則"
    assert d["kind"] == "遺失"
    assert d["name"] == "黑色保溫水壺"
    assert d["category"] == "雨傘水壺"
    assert d["location"] == "圖書館"
    assert d["date"] == day(-1)
    assert d["missing"] == []


def test_parse_task_sentence():
    d = ai_helper.parse_form_text("明天中午幫我帶一杯飲料到圖書館，請你喝一杯", "task")["data"]
    assert d["type"] == "代拿代購"
    assert d["location"] == "圖書館"
    assert d["deadline"] == day(1) + " 12:00"
    assert "請你喝一杯" in d["reward"]


def test_parse_event_sentence():
    d = ai_helper.parse_form_text("週五晚上有攝影社新生體驗", "event")["data"]
    assert d["category"] == "社團招生"
    assert d["org"] == "攝影社"
    assert d["start"].endswith("19:00")


def test_meetup_whitelist():
    r = ai_helper.suggest_meetup("item", {"location": "圖書館", "category": "證件卡片"}, None)
    for s in r["data"]["spots"]:
        assert s in ai_helper.SAFE_SPOTS
    assert "失物招領管道" in r["data"]["tips"]


def test_rerank_rule_fallback():
    items = sample_items()
    cands = lostfound.find_matches(items[0], items, 5)
    r = ai_helper.rerank_matches(items[0], cands)
    assert r["source"] == "規則"
    assert r["data"][0]["item"]["id"] == 2
    assert "圖書館" in r["data"][0]["reason"]


def test_ai_output_validation():
    # 模擬 AI 亂回：不合法的類別、日期，都不能被採用
    rule = ai_helper.rule_parse_item("昨天在圖書館掉了黑色水壺")
    merged = ai_helper.merge_ai_fields(rule, {"category": "外星物品", "date": "昨天", "kind": "偷的"}, "item")
    assert merged["category"] == "雨傘水壺"
    assert merged["date"] == rule["date"]
    assert merged["kind"] == "遺失"


def test_quick_replies_length():
    th = {"meetup": None, "messages": []}
    r = ai_helper.quick_replies(th, "小宇")
    assert len(r["data"]) == 3
    for reply in r["data"]:
        assert len(reply) <= 20


def test_ai_mock_validation():
    # 用假的 AI 回覆測試「輸出驗證」：捏造 id、白名單外地點、想放行禁止內容，都要退回或擋下
    items = sample_items()
    cands = lostfound.find_matches(items[0], items, 5)
    original = ai_helper.call_llm

    ai_helper.call_llm = lambda s, u: '{"ranking": [{"id": 2, "reason": "都是黑色水壺"}]}'
    assert ai_helper.rerank_matches(items[0], cands)["source"] == "AI"

    ai_helper.call_llm = lambda s, u: '{"ranking": [{"id": 99, "reason": "捏造的"}]}'
    assert ai_helper.rerank_matches(items[0], cands)["source"] == "規則"

    ai_helper.call_llm = lambda s, u: '{"level": "通過", "reasons": []}'
    assert ai_helper.check_task_rules("幫我代考", "")["data"]["level"] == "禁止"   # AI 不能放行

    ai_helper.call_llm = lambda s, u: '{"spots": ["我家樓下"], "tip": "x"}'
    assert ai_helper.suggest_meetup("item", {"location": ""}, None)["source"] == "規則"

    ai_helper.call_llm = lambda s, u: "這不是 JSON"
    assert ai_helper.make_verify_questions({"category": "鑰匙"})["source"] == "規則"

    ai_helper.call_llm = original


# ---------------- 地圖與松鼠 ----------------

def test_location_to_zone():
    assert campus_map.location_to_zone("圖書館三樓") == "library"
    assert campus_map.location_to_zone("中正圖書館") == "library"
    assert campus_map.location_to_zone("工程一館") == "engineering"
    assert campus_map.location_to_zone("工程二館") == "engineering2"
    assert campus_map.location_to_zone("工程三館 E6") == "engineering3"
    assert campus_map.location_to_zone("工程四館") == "engineering4"
    assert campus_map.location_to_zone("工程五館 E6") == "engineering5"
    assert campus_map.location_to_zone("科學一館") == "science"
    assert campus_map.location_to_zone("科學二館") == "science2"
    assert campus_map.location_to_zone("鴻經館・科學三館") == "science3"
    assert campus_map.location_to_zone("科學四館") == "science4"
    assert campus_map.location_to_zone("科學五館") == "science5"
    assert campus_map.location_to_zone("國鼎光電大樓") == "guoding"
    assert campus_map.location_to_zone("綜教館") == "north_facility"
    assert campus_map.location_to_zone("教學研究綜合大樓") == "teaching"
    assert campus_map.location_to_zone("大禮堂") == "activity"
    assert campus_map.location_to_zone("客家學院") == "hakka"
    assert campus_map.location_to_zone("室內游泳池") == "pool"
    assert campus_map.location_to_zone("志希館") == "north_facility"
    assert campus_map.location_to_zone("管理二館") == "management"
    assert campus_map.location_to_zone("文學二館") == "literature"
    assert campus_map.location_to_zone("人文社會科學大樓") == "literature"
    assert campus_map.location_to_zone("運動中心與網球場") == "sports"
    assert campus_map.location_to_zone("松苑") == "canteen"
    assert campus_map.location_to_zone("松果館") == "pinecone_hall"
    assert campus_map.location_to_zone("游藝館") == "play_hall"
    assert campus_map.location_to_zone("正門牌坊") == "gate"
    assert campus_map.location_to_zone("校史館") == "eastgate"
    assert campus_map.location_to_zone("男九舍") == "dorm"
    assert campus_map.location_to_zone("宵夜街") == "backgate"
    assert campus_map.location_to_zone("火星") == ""
    for zone in campus_map.ZONES:
        assert 0 <= zone["x"] - zone["w"] / 2
        assert zone["x"] + zone["w"] / 2 <= 1000
        assert 0 <= zone["y"] - zone["h"] / 2
        assert zone["y"] + zone["h"] / 2 <= 640


def test_zone_icons_do_not_overlap():
    for i, first in enumerate(campus_map.ZONES):
        for second in campus_map.ZONES[i + 1:]:
            horizontal_gap = abs(first["x"] - second["x"]) - (first["w"] + second["w"]) / 2
            vertical_gap = abs(first["y"] - second["y"]) - (first["h"] + second["h"]) / 2
            assert horizontal_gap >= 0 or vertical_gap >= 0, (first["id"], second["id"])


def test_zone_infos_counts():
    items = sample_items()
    t = tasks.create_task("代拿代購", "帶飲料", "", "圖書館", (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M"),
                          "", 1, [], "小安")
    t["id"] = 1
    infos = campus_map.build_zone_infos(items, [t], [])
    lib = None
    for z in infos:
        if z["id"] == "library":
            lib = z
    assert lib["counts"] == {"lost": 1, "found": 1, "task": 1, "event": 0}
    assert lib["urgent"] and lib["new"]
    assert len(infos) == len(campus_map.ZONES)


def test_map_search():
    items = sample_items()
    assert campus_map.search_zones(items, [], [], "水壺") == ["library"]
    assert campus_map.search_zones(items, [], [], "") == []


def test_move_and_explore_reward():
    p = squirrel.default_profile("小宇")
    ledger = []
    today = "2026-11-23"
    total = 0
    for zid in ["library", "lake", "sports", "library"]:
        first = squirrel.move_to(p, zid, today)
        if first:
            total = total + squirrel.explore_reward(ledger, p, zid, today)
    assert p["zone"] == "library"
    assert total == 3                                          # 3 個新區域 +3，重複的不算
    assert squirrel.total_pinecones(ledger, "小宇") == 3


def test_explore_daily_cap():
    p = squirrel.default_profile("小宇")
    ledger = []
    for z in campus_map.ZONES:
        if squirrel.move_to(p, z["id"], "2026-11-23"):
            squirrel.explore_reward(ledger, p, z["id"], "2026-11-23")
    assert squirrel.count_reason(ledger, "小宇", "探索") == squirrel.MAX_EXPLORE_PER_DAY
    assert "explorer" in squirrel.get_badges(ledger, p)        # 走過 8 區以上


def test_pinecones_no_double():
    ledger = []
    assert squirrel.add_pinecones(ledger, "小晴", 20, "物歸原主", "return:item:2")
    assert not squirrel.add_pinecones(ledger, "小晴", 20, "物歸原主", "return:item:2")
    assert squirrel.total_pinecones(ledger, "小晴") == 20
    assert "honest" in squirrel.get_badges(ledger, squirrel.default_profile("小晴"))


def test_mark_returned_needs_verify():
    items = sample_items()
    found = items[1]
    th = chat.open_thread([], "item", found, "小宇", ["貓咪", "刮痕"])
    th["id"] = 1
    assert not lostfound.mark_returned(found, th, "小宇")      # 還沒驗證通過
    th = chat.verify_claim(th, "小晴", True)
    assert not lostfound.mark_returned(found, th, "小晴")      # 拾獲者不能自己按
    assert lostfound.mark_returned(found, th, "小宇")
    assert found["status"] == "已尋回"
    th = chat.confirm_received(th, "小宇")
    assert th["received"]


def test_leaderboard_privacy():
    a = squirrel.default_profile("甲甲")
    b = squirrel.default_profile("乙乙")
    b["on_board"] = False
    ledger = []
    squirrel.add_pinecones(ledger, "乙乙", 50, "完成任務", "x")
    rows = squirrel.leaderboard(ledger, [a, b], 10)
    assert len(rows) == 1 and rows[0]["nickname"] == "甲甲"


def test_map_args_hide_invisible():
    a = squirrel.default_profile("小宇")
    b = squirrel.default_profile("小晴")
    b["visible"] = False
    args = campus_map.build_map_args([], [], [], [a, b], "小宇", "", [])
    assert args["me"]["name"] == "小宇"
    assert args["others"] == []                                   # 隱身的人不會出現
    assert "<svg" in args["me"]["svg"]


# ---------------- 任務系統與商店 ----------------

def test_checkin_streak():
    p = squirrel.default_profile("小宇")
    ledger = []
    assert quests.do_checkin(p, ledger, "2026-11-20") == 5          # 第 1 天
    assert quests.do_checkin(p, ledger, "2026-11-20") == 0          # 同一天不能再領
    assert quests.do_checkin(p, ledger, "2026-11-21") == 6          # 連續第 2 天 +1
    assert quests.do_checkin(p, ledger, "2026-11-23") == 5          # 斷掉了，重新算
    assert p["checkin"]["streak"] == 1
    assert quests.checkin_reward(7) == 5 + 5 + 20                    # 第 7 天大獎
    assert quests.checkin_reward(30) == 5 + 5                         # 加成有上限


def test_treasures_same_for_everyone():
    t1 = quests.treasure_zones("2026-11-23")
    assert t1 == quests.treasure_zones("2026-11-23")
    assert len(t1) == 3 and len(set(t1)) == 3
    p = squirrel.default_profile("小宇")
    ledger = []
    assert quests.collect_treasure(p, ledger, t1[0], "2026-11-23") == quests.TREASURE_REWARD
    assert quests.collect_treasure(p, ledger, t1[0], "2026-11-23") == 0          # 不能重複撿
    not_treasure = ""
    for z in campus_map.ZONES:
        if z["id"] not in t1:
            not_treasure = z["id"]
    assert quests.collect_treasure(p, ledger, not_treasure, "2026-11-23") == 0
    assert len(quests.remaining_treasures(p, "2026-11-23")) == 2


def test_daily_quests_claim():
    today = "2026-11-23"
    qs = quests.today_quests(today)
    assert len(qs) == 5 and qs == quests.today_quests(today)
    p = squirrel.default_profile("小宇")
    ledger = []
    walk = qs[0]
    assert quests.claim_quest(p, ledger, walk, "daily", today) == 0           # 還沒完成
    for z in ["library", "lake", "sports"]:
        squirrel.move_to(p, z, today)
    assert quests.claim_quest(p, ledger, walk, "daily", today) == walk["reward"]
    assert quests.claim_quest(p, ledger, walk, "daily", today) == 0           # 不能領兩次
    quests.ensure_progress(p, "2026-11-24")                                      # 隔天重置
    assert p["daily"]["claimed"] == []


def test_weekly_and_badge():
    today = "2026-11-23"
    p = squirrel.default_profile("小晴")
    ledger = []
    quests.bump(p, "return_item", today)
    q = quests.WEEKLY[3]
    assert quests.claim_quest(p, ledger, q, "weekly", today) == 30
    squirrel.add_pinecones(ledger, "小晴", 20, "物歸原主", "r1")
    assert quests.claim_badge(p, ledger, "honest", today) == 30
    assert quests.claim_badge(p, ledger, "honest", today) == 0
    assert quests.claim_badge(p, ledger, "guardian", today) == 0                # 還沒解鎖


def test_zone_visit_counters():
    today = "2026-11-23"
    p = squirrel.default_profile("小宇")
    info = {"counts": {"lost": 1, "found": 0, "task": 2, "event": 0}}
    quests.record_zone_visit(p, "library", info, today)
    quests.record_zone_visit(p, "library", info, today)                          # 同一區不重複算
    assert p["daily"]["counters"]["lf_zone"] == 1
    assert p["daily"]["counters"]["task_zone"] == 1
    assert p["weekly"]["zones"] == ["library"]


def test_shop_buy_equip():
    today = "2026-11-23"
    p = squirrel.default_profile("小宇")
    ledger = []
    assert not shop.buy_item(p, ledger, "ncu_tee", today)["ok"]                  # 沒錢
    squirrel.add_pinecones(ledger, "小宇", 500, "測試", "t")
    price = shop.price_of(wardrobe.get_item("ncu_tee"), today)
    assert shop.buy_item(p, ledger, "ncu_tee", today)["ok"]
    assert squirrel.total_pinecones(ledger, "小宇") == 500 - price
    assert squirrel.earned_pinecones(ledger, "小宇") == 500                      # 排行榜不因購物下降
    assert not shop.buy_item(p, ledger, "ncu_tee", today)["ok"]                  # 不能重複買
    assert shop.equip(p, "ncu_tee") and p["outfit"]["body"] == "ncu_tee"
    assert not shop.equip(p, "crown")                                             # 沒買不能穿
    assert shop.try_on(p, "crown")["head"] == "crown" and p["outfit"]["head"] == ""
    assert not shop.set_fur(p, "黃金")
    assert shop.buy_fur(p, ledger, "雪白")["ok"] and shop.set_fur(p, "雪白")


def test_fitting_room_bundle():
    today = "2026-11-23"
    p = squirrel.default_profile("小宇")
    ledger = []
    fitting = {"head": "crown", "body": "scarf_red"}                            # 王冠沒買、圍巾是新手禮物
    cost = shop.fitting_cost(p, fitting, "雪白", today)
    assert len(cost["items"]) == 1 and cost["fur"]["id"] == "雪白"
    assert cost["total"] == shop.price_of(wardrobe.get_item("crown"), today) + 80
    assert shop.fitting_outfit(p, fitting)["head"] == "crown" and p["outfit"]["head"] == ""   # 試穿不改原本
    squirrel.add_pinecones(ledger, "小宇", 100, "測試", "t1")
    assert not shop.buy_bundle(p, ledger, fitting, "雪白", today)["ok"]          # 不夠 → 一件都不買
    assert "crown" not in p["owned"] and squirrel.total_pinecones(ledger, "小宇") == 100
    squirrel.add_pinecones(ledger, "小宇", 1000, "測試", "t2")
    assert shop.buy_bundle(p, ledger, fitting, "雪白", today)["ok"]
    assert p["outfit"]["head"] == "crown" and p["outfit"]["body"] == "scarf_red" and p["fur"] == "雪白"
    assert squirrel.total_pinecones(ledger, "小宇") == 1100 - cost["total"]


def test_daily_deal_discount():
    deal = wardrobe.get_item(shop.daily_deal("2026-11-23"))
    assert deal["price"] > 0
    assert shop.price_of(deal, "2026-11-23") < deal["price"]


def test_legacy_profile_migration():
    old = {"nickname": "舊用戶", "fur": "灰松", "accessory": "背包", "zone": "library", "visited_all": []}
    p = squirrel.normalize_profile(old)
    assert p["outfit"]["back"] == "backpack" and "backpack" in p["owned"]
    assert "accessory" not in p
    assert "<svg" in squirrel.profile_svg(p, 40)


def test_wardrobe_catalog():
    ids = []
    for item in wardrobe.ITEMS:
        assert item["slot"] in wardrobe.SLOTS
        assert item["id"] not in ids
        ids.append(item["id"])
    assert len(wardrobe.ITEMS) >= 35
    assert 5 <= len(wardrobe.ncu_items()) <= 12                                 # 中大系列只占一小部分


def run_all():
    """依序執行所有 test_ 函式"""
    names = sorted(globals().keys())
    passed = 0
    failed = 0
    for name in names:
        if name.startswith("test_"):
            try:
                globals()[name]()
                print("✅", name)
                passed = passed + 1
            except AssertionError as error:
                print("❌", name, error)
                failed = failed + 1
    print("-" * 40)
    if failed == 0:
        print("全部通過！共", passed, "項")
    else:
        print("通過", passed, "項，失敗", failed, "項")


if __name__ == "__main__":
    run_all()
