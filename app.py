# app.py —— 櫃台：Streamlit 頁面與導覽（中大圈 NCU Loop MVP）
# 執行：streamlit run app.py
#
# 頁面：首頁｜🗺️ 松鼠地圖｜🔎 失物招領（主線）｜🤝 任務互助｜🎪 活動資訊｜💬 我的私訊｜🐿️ 我的松鼠
# 小提醒：Streamlit 每次按按鈕都會「從頭重跑一次整個檔案」，
#        所以需要記住的東西（登入者、正在看的討論串…）都放在 st.session_state

from datetime import datetime, date, time

import streamlit as st

import storage
from storage import (load_data, save_data, get_next_id, now_text, find_by_id, replace_by_id,
                     load_thread, save_thread, load_all_threads,
                     USERS_PATH, LOSTFOUND_PATH, TASKS_PATH, EVENTS_PATH, REPORTS_PATH, BLOCKS_PATH,
                     PROFILES_PATH, PINECONES_PATH, today_text)
import auth
import lostfound
import tasks as tasks_mod
import events as events_mod
import chat
import ai_helper
import campus_map
import squirrel
import map_component
import quests
import shop
import wardrobe

PAGE_HOME = "🏠 首頁"
PAGE_MAP = "🗺️ 松鼠地圖"
PAGE_ME = "🐿️ 我的松鼠"
PAGE_QUEST = "🎯 松果任務"
PAGE_SHOP = "🛍️ 松果商店"
PAGE_LF = "🔎 失物招領"
PAGE_TASK = "🤝 任務互助"
PAGE_EVENT = "🎪 活動資訊"
PAGE_CHAT = "💬 我的私訊"
PAGES = [PAGE_HOME, PAGE_MAP, PAGE_QUEST, PAGE_SHOP, PAGE_LF, PAGE_TASK, PAGE_EVENT, PAGE_CHAT, PAGE_ME]

PRIVACY_NOTE = "🔒 請勿填寫學號、手機、Email、身分證字號；聯絡一律走站內私訊。"


# ======================================================================
# 共用小工具
# ======================================================================

def me():
    """回傳目前登入者暱稱，未登入回傳空字串"""
    return st.session_state.get("user", "")


def source_badge(source):
    """顯示 AI／規則 來源標籤"""
    if source == "AI":
        st.caption("🤖 AI 建議（請確認後再使用）")
    else:
        st.caption("📏 規則建議（未使用 AI）")


def split_words(text):
    """把「黑色, 水壺、貼紙」拆成 ['黑色', '水壺', '貼紙']"""
    for sep in ["，", "、", " ", "；"]:
        text = text.replace(sep, ",")
    result = []
    for word in text.split(","):
        word = word.strip()
        if word != "" and word not in result:
            result.append(word)
    return result[:5]


def to_date(text, default):
    """'YYYY-MM-DD' → date 物件；失敗回傳 default"""
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return default


def to_time(text, default):
    """'YYYY-MM-DD HH:MM' → time 物件；失敗回傳 default"""
    try:
        return datetime.strptime(text[11:16], "%H:%M").time()
    except (ValueError, TypeError):
        return default


def warn_sensitive(*texts):
    """若文字中有個資，顯示「已自動遮蔽」提醒"""
    found = []
    for t in texts:
        for f in ai_helper.detect_sensitive(t):
            if f["type"] not in found:
                found.append(f["type"])
    if len(found) > 0:
        st.warning("🔒 偵測到 " + "、".join(found) + "，公開內容已自動遮蔽。")


def go_to_chat(thread_id):
    """切換到私訊頁並打開某個討論串"""
    st.session_state["goto"] = PAGE_CHAT
    st.session_state["active_thread"] = thread_id
    st.rerun()


def go_to_page(page):
    """切換到別的頁面"""
    st.session_state["goto"] = page
    st.rerun()


def notify(text):
    """存一則通知，下一次畫面重跑時用 st.toast 顯示（避免 st.rerun 把它吃掉）"""
    notes = st.session_state.get("notes", [])
    notes.append(text)
    st.session_state["notes"] = notes


def show_notes():
    """把暫存的通知顯示出來"""
    for text in st.session_state.get("notes", []):
        st.toast(text)
    st.session_state["notes"] = []


def ensure_profile(nickname):
    """確保這個人有松鼠檔案（第一次登入時建立）"""
    profiles = load_data(PROFILES_PATH)
    for p in profiles:
        if p["nickname"] == nickname:
            return p
    profile = squirrel.default_profile(nickname)
    save_data(PROFILES_PATH, squirrel.save_profile(profiles, profile))
    return profile


def give_pinecones(nickname, amount, reason, ref):
    """發松果（同一個 ref 只發一次），發成功就通知"""
    ledger = load_data(PINECONES_PATH)
    if squirrel.add_pinecones(ledger, nickname, amount, reason, ref):
        save_data(PINECONES_PATH, ledger)
        # 每週任務「伸出援手」「失物英雄」的進度記在「被感謝的人」身上
        if reason == "完成任務":
            bump_counter("help_task", nickname)
        if reason == "物歸原主":
            bump_counter("return_item", nickname)
        if nickname == me():
            notify("🌰 " + reason + " +" + str(amount) + " 松果")
        else:
            notify("🌰 已送給 " + nickname + " " + str(amount) + " 顆松果（" + reason + "）")
        return True
    return False


def load_my_profile():
    """讀取（並補齊）目前登入者的松鼠檔案與今日進度"""
    profiles = load_data(PROFILES_PATH)
    profile = squirrel.get_profile(profiles, me())
    quests.ensure_progress(profile, today_text())
    return profiles, profile


def save_my_profile(profile):
    """寫回松鼠檔案（寫入前重新讀檔）"""
    latest = load_data(PROFILES_PATH)
    save_data(PROFILES_PATH, squirrel.save_profile(latest, profile))


def bump_counter(counter, nickname=""):
    """任務計數 +1（預設是自己）"""
    if nickname == "":
        nickname = me()
    if nickname == "":
        return
    profiles = load_data(PROFILES_PATH)
    profile = squirrel.get_profile(profiles, nickname)
    quests.bump(profile, counter, today_text())
    save_data(PROFILES_PATH, squirrel.save_profile(profiles, profile))


def avatar_html(profile, size):
    """某人的松鼠圖（HTML 字串）"""
    return squirrel.svg_to_img(squirrel.profile_svg(squirrel.normalize_profile(profile), size), size)


def squirrel_img(fur, outfit, size):
    """畫一隻指定毛色與穿搭的松鼠（<img> 形式，st.html 才顯示得出來）"""
    return squirrel.svg_to_img(squirrel.squirrel_svg(fur, outfit, size), size)


def start_chat(target_type, target, claim_answers):
    """開啟（或找到舊的）討論串，存檔後跳到私訊頁"""
    user = me()
    blocks = load_data(BLOCKS_PATH)
    if chat.is_blocked(blocks, user, target["owner"]):
        st.error("你和對方之間有封鎖紀錄，無法開啟私訊。")
        return
    threads = load_all_threads()
    thread = chat.open_thread(threads, target_type, target, user, claim_answers)
    if thread is None:
        st.warning("不能對自己的刊登或任務開啟私訊。")
        return
    if thread["id"] == 0:
        thread["id"] = get_next_id(threads)
        thread = chat.send_message(thread, chat.SYSTEM_NAME,
                                   "私訊已建立。提醒：不要先付錢、不要提供驗證碼或帳號密碼，面交請約公共場所。", "system")
        save_thread(thread)
    go_to_chat(thread["id"])


# ======================================================================
# 側邊欄：登入／註冊
# ======================================================================

def render_auth_sidebar():
    """側邊欄登入／註冊／登出，以 st.session_state 保存登入者"""
    st.sidebar.title("🎓 中大圈 NCU Loop")
    if me() != "":
        profile = ensure_profile(me())
        total = squirrel.total_pinecones(load_data(PINECONES_PATH), me())
        st.sidebar.html('<div style="display:flex;align-items:center;gap:10px;background:#FFF5DA;border:1.5px solid #E9D29A;'
                        'border-radius:14px;padding:6px 10px">' + avatar_html(profile, 54)
                        + '<div><b style="font-size:16px">' + me() + '</b><br><span style="font-size:14px">🌰 '
                        + str(total) + ' 松果　📍' + campus_map.zone_name(profile.get("zone", "gate")) + '</span></div></div>')
        quests.ensure_progress(profile, today_text())
        claim = quests.claimable_count(profile, today_text())
        if not quests.has_checked_in(profile, today_text()):
            st.sidebar.warning("📅 今天還沒簽到喔！")
        elif claim > 0:
            st.sidebar.info("🎁 有 " + str(claim) + " 個任務獎勵可以領")
        if st.sidebar.button("登出"):
            st.session_state["user"] = ""
            st.session_state["active_thread"] = 0
            st.rerun()
    else:
        tab_login, tab_reg = st.sidebar.tabs(["登入", "註冊"])
        with tab_login:
            nick = st.text_input("暱稱", key="login_nick")
            pw = st.text_input("密碼", type="password", key="login_pw")
            if st.button("登入", key="btn_login"):
                users = load_data(USERS_PATH)
                if auth.login_user(users, nick, pw):
                    st.session_state["user"] = nick.strip()
                    ensure_profile(nick.strip())
                    st.rerun()
                else:
                    st.error("暱稱或密碼錯誤")
            st.caption("示範帳號：小宇／小晴／小安／小凱，密碼 demo1234")
        with tab_reg:
            nick2 = st.text_input("暱稱（2–12 字）", key="reg_nick")
            pw2 = st.text_input("密碼（至少 6 碼）", type="password", key="reg_pw")
            if st.button("註冊", key="btn_reg"):
                users = load_data(USERS_PATH)
                result = auth.register_user(users, nick2, pw2)
                if result["ok"]:
                    users.append(result["user"])
                    save_data(USERS_PATH, users)
                    st.session_state["user"] = result["user"]["nickname"]
                    ensure_profile(result["user"]["nickname"])
                    notify("🐿️ 歡迎！到「我的松鼠」幫自己打扮一下吧")
                    st.rerun()
                else:
                    st.error(result["message"])

    st.sidebar.divider()
    if ai_helper.is_ai_enabled():
        st.sidebar.caption("🤖 AI 模式：開啟（失敗時自動退回規則版）")
    else:
        st.sidebar.caption("📏 AI 模式：關閉（目前全部使用規則版）")
    st.sidebar.caption("⚠️ 示範資料，全部為虛構")


# ======================================================================
# 首頁
# ======================================================================

def item_icon(item):
    """失物的小圖示"""
    if item["kind"] == "拾獲":
        return "🟢"
    return "🔴"


def get_created(record):
    """排序用：建立時間"""
    return record.get("created_at", "")


def render_home_page():
    """首頁：松鼠橫幅、數字看板、今日探索、最新動態、線上松鼠"""
    items = load_data(LOSTFOUND_PATH)
    all_tasks = load_data(TASKS_PATH)
    all_events = load_data(EVENTS_PATH)
    profiles = load_data(PROFILES_PATH)
    ledger = load_data(PINECONES_PATH)

    hero_squirrel = squirrel_img("栗棕", {"head": "grad_cap"}, 150)
    st.html(
        '<div style="display:flex;align-items:center;gap:22px;padding:22px 28px;border-radius:24px;'
        'background:linear-gradient(120deg,#2F7A5B 0%,#4E9A6E 55%,#E8C47A 100%);color:#FFF8E7;'
        'box-shadow:0 8px 24px rgba(47,122,91,.25)">'
        + hero_squirrel +
        '<div><div style="font-size:34px;font-weight:800;letter-spacing:1px">中大圈 NCU Loop</div>'
        '<div style="font-size:18px;margin-top:4px">找得回物品・幫得上同學・逛得到活動</div>'
        '<div style="font-size:14px;margin-top:10px;opacity:.9">變成一隻中大松鼠，在校園地圖上跑來跑去，看看哪裡有人需要幫忙 🌲</div>'
        '</div></div>')
    st.write("")

    lost_open = 0
    returned = 0
    for item in items:
        if item["status"] == "尋找中":
            lost_open = lost_open + 1
        else:
            returned = returned + 1
    task_open = len(tasks_mod.list_tasks(all_tasks, "全部", "", "招募中"))
    upcoming = len(events_mod.list_events(all_events, "全部", "", True))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔎 尋找中的物品", lost_open)
    c2.metric("🎉 已物歸原主", returned)
    c3.metric("🤝 招募中任務", task_open)
    c4.metric("🎪 即將舉行活動", upcoming)

    left, right = st.columns([3, 2])
    with left:
        st.markdown("#### 🔥 最新動態")
        feed = []
        for item in items:
            feed.append({"created_at": item["created_at"], "icon": item_icon(item),
                         "text": item["owner"] + " " + item["kind"] + "了「" + item["name"] + "」",
                         "place": item["location"]})
        for task in all_tasks:
            feed.append({"created_at": task["created_at"], "icon": "🟠",
                         "text": task["owner"] + " 發布任務「" + task["title"] + "」", "place": task["location"]})
        for event in all_events:
            feed.append({"created_at": event["created_at"], "icon": "🟣",
                         "text": event["org"].replace("（虛構）", "") + " 發布活動「" + event["title"].replace("（虛構）", "") + "」",
                         "place": event["place"]})
        feed = sorted(feed, key=get_created, reverse=True)
        with st.container(border=True):
            for f in feed[:7]:
                zone = campus_map.location_to_zone(f["place"])
                where = "📍" + f["place"]
                if zone != "":
                    where = "📍" + campus_map.zone_name(zone)
                st.markdown(f["icon"] + " " + f["text"] + "　<span style='color:#8A7A60;font-size:13px'>" + where
                            + "・" + f["created_at"][5:] + "</span>", unsafe_allow_html=True)
        if st.button("🗺️ 到松鼠地圖上看看", type="primary", use_container_width=True):
            go_to_page(PAGE_MAP)

    with right:
        if me() != "":
            profiles_now, profile = load_my_profile()
            today = today_text()
            st.markdown("#### 🎯 今天的松果")
            with st.container(border=True):
                if quests.has_checked_in(profile, today):
                    st.write("📅 已簽到（連續 " + str(profile["checkin"]["streak"]) + " 天）")
                else:
                    if st.button("📅 今日簽到 +" + str(quests.checkin_reward(quests.next_streak(profile, today))) + " 松果",
                                 type="primary", use_container_width=True):
                        do_checkin_now()
                        st.rerun()
                left_gold = quests.remaining_treasures(profile, today)
                st.write("✨ 金松果還有 " + str(len(left_gold)) + " 顆沒撿")
                claim = quests.claimable_count(profile, today)
                if claim > 0:
                    st.write("🎁 有 **" + str(claim) + "** 個任務獎勵可以領！")
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("🎯 任務中心", use_container_width=True):
                        go_to_page(PAGE_QUEST)
                with b2:
                    if st.button("🛍️ 逛商店", use_container_width=True):
                        go_to_page(PAGE_SHOP)
                st.caption("我的松果：🌰 " + str(squirrel.total_pinecones(load_data(PINECONES_PATH), me())))
        st.markdown("#### 🐿️ 線上松鼠")
        online_html = ""
        now = datetime.now()
        for p in profiles:
            if p.get("visible", True) and squirrel.is_online(p, now):
                online_html = (online_html + '<div style="text-align:center;width:72px">' + avatar_html(p, 56)
                               + '<div style="font-size:12px">' + p["nickname"] + '</div><div style="font-size:11px;color:#8A7A60">'
                               + campus_map.zone_name(p.get("zone", "gate")) + '</div></div>')
        if online_html == "":
            st.caption("現在沒有其他松鼠在線上。")
        else:
            st.html('<div style="display:flex;flex-wrap:wrap;gap:6px">' + online_html + '</div>')
    st.caption("⚠️ 所有資料皆為示範資料（虛構）。平台不經手任何金錢。地圖上的松鼠位置是你在網站上逛到哪裡，不是真實定位。")


# ======================================================================
# 🗺️ 松鼠地圖
# ======================================================================

def handle_move(user, zone_id):
    """松鼠走到某個區域：更新位置、發探索松果"""
    st.session_state["map_zone"] = zone_id
    if user == "":
        return
    today = today_text()
    profiles = load_data(PROFILES_PATH)
    profile = squirrel.get_profile(profiles, user)
    quests.ensure_progress(profile, today)
    first_today = squirrel.move_to(profile, zone_id, today)
    # 這個區域有沒有失物／任務／活動（給每日任務「失物巡邏」等使用）
    zone_info = None
    infos = campus_map.build_zone_infos(load_data(LOSTFOUND_PATH), load_data(TASKS_PATH), load_data(EVENTS_PATH))
    for info in infos:
        if info["id"] == zone_id:
            zone_info = info
    quests.record_zone_visit(profile, zone_id, zone_info, today)
    ledger = load_data(PINECONES_PATH)
    got_treasure = quests.collect_treasure(profile, ledger, zone_id, today)
    got_explore = 0
    if first_today:
        got_explore = squirrel.explore_reward(ledger, profile, zone_id, today)
    save_data(PROFILES_PATH, squirrel.save_profile(profiles, profile))
    if got_treasure + got_explore > 0:
        save_data(PINECONES_PATH, ledger)
    if got_treasure > 0:
        notify("✨ 撿到今日金松果！+" + str(got_treasure) + " 松果（還剩 "
               + str(len(quests.remaining_treasures(profile, today))) + " 顆）")
    if got_explore > 0:
        notify("🐾 新足跡「" + campus_map.zone_name(zone_id) + "」+" + str(got_explore) + " 松果")


@st.fragment(run_every=10)
def map_fragment(user, highlight):
    """地圖本體：每 10 秒更新一次其他松鼠的位置；使用者點區域時整頁重跑"""
    items = load_data(LOSTFOUND_PATH)
    all_tasks = load_data(TASKS_PATH)
    all_events = load_data(EVENTS_PATH)
    profiles = load_data(PROFILES_PATH)
    selected = st.session_state.get("map_zone", "")
    args = campus_map.build_map_args(items, all_tasks, all_events, profiles, user, selected, highlight)
    args["treasures"] = []
    if user != "":
        mine = squirrel.get_profile(profiles, user)
        args["treasures"] = quests.remaining_treasures(mine, today_text())
    value = map_component.squirrel_map(args, key="campus_map")
    if value is not None and value.get("ts") != st.session_state.get("map_last_ts"):
        st.session_state["map_last_ts"] = value.get("ts")
        if campus_map.get_zone(value.get("zone")) is not None:     # 只接受真的存在的區域
            handle_move(user, value["zone"])
            st.rerun()


def render_zone_panel(zone_id):
    """地圖右邊：這個區域的失物、任務、活動"""
    if zone_id == "":
        st.markdown("#### 👈 點地圖上的建築物")
        st.write("你的松鼠會跳過去，這裡會列出那個地方的失物、任務和活動。")
        st.markdown("- 徽章上的**數字**＝那裡有幾筆資料\n- **色點**：🔴 遺失　🟢 拾獲　🟠 任務　🟣 活動\n"
                    "- 徽章外有**紅色波紋**＝24 小時內有新刊登\n- **⏰**＝有任務 3 小時內截止\n"
                    "- 點一下地圖後，可以用**方向鍵／WASD**自由走路")
        return
    zone = campus_map.get_zone(zone_id)
    items = load_data(LOSTFOUND_PATH)
    all_tasks = load_data(TASKS_PATH)
    all_events = load_data(EVENTS_PATH)
    zone_items = []
    for item in campus_map.items_in_zone(items, zone_id, "location"):
        if item["status"] == "尋找中":
            zone_items.append(item)
    zone_tasks = []
    for task in campus_map.items_in_zone(all_tasks, zone_id, "location"):
        if task["status"] == "招募中":
            zone_tasks.append(task)
    zone_events = campus_map.items_in_zone(events_mod.list_events(all_events, "全部", "", True), zone_id, "place")

    st.markdown("### " + zone["emoji"] + " " + zone["name"])
    here = []
    for p in load_data(PROFILES_PATH):
        if p.get("zone") == zone_id and p["nickname"] != me() and p.get("visible", True):
            here.append(p)
    if len(here) > 0:
        html = ""
        for p in here[:6]:
            html = html + '<span title="' + p["nickname"] + '">' + avatar_html(p, 36) + '</span>'
        names = []
        for p in here:
            names.append(p["nickname"])
        st.html('<div style="display:flex;align-items:center;gap:2px">' + html
                + '<span style="margin-left:8px;color:#6B5B40">' + "、".join(names) + ' 也在這裡</span></div>')

    tab1, tab2, tab3 = st.tabs(["🔎 失物 " + str(len(zone_items)), "🤝 任務 " + str(len(zone_tasks)),
                                "🎪 活動 " + str(len(zone_events))])
    with tab1:
        if len(zone_items) == 0:
            st.caption("這裡目前沒有尋找中的物品。")
        for item in zone_items:
            render_item_card(item, items, "map")
        if me() != "" and st.button("➕ 在這裡刊登失物", key="map_new_item"):
            st.session_state["lf_location"] = zone["name"]
            notify("📍 地點已幫你填好「" + zone["name"] + "」，請切到「我要刊登」分頁")
            go_to_page(PAGE_LF)
    with tab2:
        if len(zone_tasks) == 0:
            st.caption("這裡目前沒有招募中的任務。")
        for task in zone_tasks:
            render_task_card(task, "map")
        if me() != "" and st.button("➕ 在這裡發布任務", key="map_new_task"):
            st.session_state["tk_location"] = zone["name"]
            notify("📍 地點已幫你填好「" + zone["name"] + "」，請切到「發布任務」分頁")
            go_to_page(PAGE_TASK)
    with tab3:
        if len(zone_events) == 0:
            st.caption("這裡最近沒有活動。")
        for event in zone_events:
            render_event_card(event, "map")


def render_map_page():
    """松鼠地圖頁"""
    st.title("🗺️ 松鼠地圖")
    st.caption("示意地圖（非實際比例）｜一個區域只顯示一個徽章，避免畫面雜亂｜松鼠位置＝你在網站上逛到哪，不是 GPS 定位")
    items = load_data(LOSTFOUND_PATH)
    all_tasks = load_data(TASKS_PATH)
    all_events = load_data(EVENTS_PATH)
    keyword = st.text_input("🔍 在地圖上找（例如：水壺、羽球、攝影）", key="map_search")
    highlight = campus_map.search_zones(items, all_tasks, all_events, keyword)
    if keyword.strip() != "" and keyword != st.session_state.get("last_map_search", ""):
        st.session_state["last_map_search"] = keyword
        bump_counter("search")
    if keyword.strip() != "":
        if len(highlight) == 0:
            st.caption("找不到符合的資料。")
        else:
            names = []
            for z in highlight:
                names.append(campus_map.zone_name(z))
            st.caption("✨ 在這些地方找到了（地圖上發亮）：" + "、".join(names))
    missing = campus_map.unmapped_count(items, all_tasks, all_events)
    if missing > 0:
        st.caption("ℹ️ 有 " + str(missing) + " 筆資料的地點對不到地圖區域，不會顯示在地圖上（可以在各頁面看到）。")

    left, right = st.columns([3, 2])
    with left:
        map_fragment(me(), highlight)
    with right:
        with st.container(border=True):
            render_zone_panel(st.session_state.get("map_zone", ""))


# ======================================================================
# 🎯 松果任務
# ======================================================================

def progress_card(quest, status, scope, key):
    """一張任務卡：圖示、名稱、進度條、領取按鈕"""
    with st.container(border=True):
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown("**" + quest["icon"] + " " + quest["name"] + "**　🌰 +" + str(quest["reward"]))
            st.progress(status["count"] / status["goal"], text=quest["desc"] + "（" + str(status["count"]) + "/" + str(status["goal"]) + "）")
        with col2:
            if status["claimed"]:
                st.button("✅ 已領", key=key, disabled=True, use_container_width=True)
            elif status["done"]:
                if st.button("🎁 領取", key=key, type="primary", use_container_width=True):
                    profiles, profile = load_my_profile()
                    ledger = load_data(PINECONES_PATH)
                    got = quests.claim_quest(profile, ledger, quest, scope, today_text())
                    if got > 0:
                        save_data(PINECONES_PATH, ledger)
                        save_my_profile(profile)
                        notify("🎉 完成「" + quest["name"] + "」+" + str(got) + " 松果")
                    st.rerun()
            else:
                st.button("進行中", key=key, disabled=True, use_container_width=True)


def do_checkin_now():
    """按下簽到"""
    profiles, profile = load_my_profile()
    ledger = load_data(PINECONES_PATH)
    got = quests.do_checkin(profile, ledger, today_text())
    if got > 0:
        save_data(PINECONES_PATH, ledger)
        save_my_profile(profile)
        notify("📅 簽到成功！連續 " + str(profile["checkin"]["streak"]) + " 天，+" + str(got) + " 松果")


def checkin_strip(profile):
    """7 天簽到格子（HTML）"""
    today = today_text()
    streak = profile["checkin"]["streak"]
    if profile["checkin"]["last"] not in (today, quests.yesterday_of(today)):
        streak = 0
    done_in_cycle = streak % 7
    if streak > 0 and done_in_cycle == 0:
        done_in_cycle = 7
    if profile["checkin"]["last"] != today and done_in_cycle == 7:
        done_in_cycle = 0       # 上一輪 7 天已滿、今天還沒簽 → 新的一輪
    html = '<div style="display:flex;gap:6px;flex-wrap:wrap">'
    for day in range(1, 8):
        if day <= done_in_cycle:
            style = "background:#2F7A5B;color:#fff;border:2px solid #2F7A5B"
            mark = "✅"
        else:
            style = "background:#fff;color:#3B2A1A;border:2px dashed #D8C69C"
            mark = "🌰"
        reward = quests.checkin_reward(streak - done_in_cycle + day)
        if day == 7:
            mark = "🎁"
        html = (html + '<div style="' + style + ';border-radius:12px;width:64px;padding:6px 0;text-align:center">'
                '<div style="font-size:12px">第 ' + str(day) + ' 天</div><div style="font-size:20px">' + mark
                + '</div><div style="font-size:12px">+' + str(reward) + '</div></div>')
    return html + '</div>'


def render_quest_page():
    """松果任務中心：簽到、金松果、每日任務、每週任務、徽章獎勵"""
    st.title("🎯 松果任務")
    today = today_text()
    profiles, profile = load_my_profile()
    ledger = load_data(PINECONES_PATH)
    c1, c2, c3 = st.columns(3)
    c1.metric("🌰 目前松果", squirrel.total_pinecones(ledger, me()))
    c2.metric("🔥 連續簽到", str(profile["checkin"]["streak"]) + " 天")
    c3.metric("🎁 可領取", str(quests.claimable_count(profile, today)) + " 個")

    # 簽到
    with st.container(border=True):
        st.markdown("#### 📅 每日簽到")
        st.html(checkin_strip(profile))
        if quests.has_checked_in(profile, today):
            st.caption("今天已經簽到了，明天再來！連續簽到越多天拿越多，第 7 天有大禮包 🎁")
        else:
            streak = quests.next_streak(profile, today)
            if st.button("📅 簽到領 " + str(quests.checkin_reward(streak)) + " 顆松果", type="primary"):
                do_checkin_now()
                st.rerun()

    # 金松果
    with st.container(border=True):
        st.markdown("#### ✨ 今日金松果點")
        st.caption("每天校園裡會出現 3 顆金松果（大家看到的位置一樣），讓松鼠走過去就能撿，每顆 +"
                   + str(quests.TREASURE_REWARD) + "。")
        cols = st.columns(3)
        i = 0
        for zid in quests.treasure_zones(today):
            got = zid in profile["daily"]["treasures"]
            with cols[i]:
                if got:
                    st.success("✅ " + campus_map.zone_name(zid))
                else:
                    st.warning("✨ " + campus_map.zone_name(zid))
            i = i + 1
        if len(quests.remaining_treasures(profile, today)) > 0:
            if st.button("🗺️ 去地圖撿金松果"):
                go_to_page(PAGE_MAP)

    left, right = st.columns(2)
    with left:
        st.markdown("#### ☀️ 每日任務")
        st.caption("每天午夜重置；後 3 個每天輪替")
        for q in quests.today_quests(today):
            progress_card(q, quests.quest_status(profile, q, "daily"), "daily", "claim_d_" + q["id"])
    with right:
        st.markdown("#### 📆 每週任務")
        st.caption("每週一重置；幫助別人的任務要由「被幫助的人」確認才算")
        for q in quests.WEEKLY:
            progress_card(q, quests.quest_status(profile, q, "weekly"), "weekly", "claim_w_" + q["id"])

    st.markdown("#### 🏅 徽章獎勵")
    unlocked = squirrel.get_badges(ledger, profile)
    cols = st.columns(len(squirrel.BADGES))
    i = 0
    for b in squirrel.BADGES:
        with cols[i]:
            with st.container(border=True):
                st.markdown("<div style='text-align:center;font-size:30px'>" + b["icon"] + "</div>"
                            "<div style='text-align:center;font-weight:700'>" + b["name"] + "</div>"
                            "<div style='text-align:center;font-size:12px;color:#6B5B40'>" + b["desc"] + "</div>",
                            unsafe_allow_html=True)
                reward = quests.BADGE_REWARDS.get(b["id"], 0)
                if b["id"] in profile["badge_claimed"]:
                    st.button("✅ 已領", key="badge_" + b["id"], disabled=True, use_container_width=True)
                elif b["id"] in unlocked:
                    if st.button("🎁 +" + str(reward), key="badge_" + b["id"], type="primary", use_container_width=True):
                        got = quests.claim_badge(profile, ledger, b["id"], today)
                        if got > 0:
                            save_data(PINECONES_PATH, ledger)
                            save_my_profile(profile)
                            notify("🏅 徽章「" + b["name"] + "」獎勵 +" + str(got) + " 松果")
                        st.rerun()
                else:
                    st.button("🔒 +" + str(reward), key="badge_" + b["id"], disabled=True, use_container_width=True)
        i = i + 1

    with st.expander("📖 松果怎麼拿？"):
        st.markdown(
            "| 來源 | 松果 |\n|---|---|\n"
            "| 每日簽到 | 5～10（連續越多越多），第 7 天再 +20 |\n"
            "| 今日金松果點 | 每顆 +3，一天 3 顆 |\n"
            "| 新足跡（第一次走到某區） | +1，每天最多 5 |\n"
            "| 每日任務 | 2～10 |\n"
            "| 每週任務 | 20～30 |\n"
            "| 完成別人的任務（發布者確認） | +10 |\n"
            "| 幫人找回失物（失主確認） | +20 |\n"
            "| 解鎖徽章 | 5～50（一次性） |\n\n"
            "「刊登」本身不給松果，避免為了松果亂發文。松果只能在商店換虛擬造型，不能換錢。")


@st.dialog("🌰 每日簽到")
def checkin_dialog():
    """每天第一次進網站時跳出的簽到視窗"""
    profiles, profile = load_my_profile()
    streak = quests.next_streak(profile, today_text())
    st.html('<div style="text-align:center">' + avatar_html(profile, 120) + '</div>')
    st.markdown("<div style='text-align:center;font-size:18px'>早安，<b>" + me() + "</b>！今天是連續第 <b>"
                + str(streak) + "</b> 天</div>", unsafe_allow_html=True)
    st.html(checkin_strip(profile))
    remaining = quests.remaining_treasures(profile, today_text())
    names = []
    for zid in remaining:
        names.append(campus_map.zone_name(zid))
    if len(names) > 0:
        st.caption("✨ 今天的金松果在：" + "、".join(names))
    if st.button("📅 簽到領 " + str(quests.checkin_reward(streak)) + " 顆松果", type="primary", use_container_width=True):
        do_checkin_now()
        st.rerun()


# ======================================================================
# 🛍️ 松果商店（試衣間＋購買確認視窗）
# ======================================================================

STAGE_STYLE = ('<style>@keyframes sqbob{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}'
               '.sq-stage img{animation:sqbob 2.2s ease-in-out infinite}</style>')


def rarity_tag(rarity):
    """稀有度小標籤（HTML）"""
    color = wardrobe.RARITY_COLORS.get(rarity, "#7A8B99")
    return ('<span style="background:' + color + ';color:#fff;border-radius:999px;padding:1px 8px;font-size:11px">'
            + rarity + '</span>')


def stage_html(svg, caption, glow):
    """一個「展示台」：放大的松鼠＋底下的說明"""
    bg = "radial-gradient(circle,#FFF8E6 0%,#F2E8D2 75%)"
    if glow:
        bg = "radial-gradient(circle,#FFF3B0 0%,#F7DC8A 45%,#F2E8D2 80%)"
    return ('<div class="sq-stage" style="text-align:center;background:' + bg + ';border-radius:20px;padding:8px 4px">'
            + svg + '<div style="font-weight:700;font-size:14px">' + caption + '</div></div>')


def get_fitting():
    """目前試衣間裡試穿的衣服（slot → id）與毛色"""
    if "fitting" not in st.session_state:
        st.session_state["fitting"] = {}
    if "fitting_fur" not in st.session_state:
        st.session_state["fitting_fur"] = ""
    return st.session_state["fitting"], st.session_state["fitting_fur"]


def try_on_item(item):
    """把衣服放進試衣間（同部位會換掉）"""
    fitting, fur = get_fitting()
    fitting[item["slot"]] = item["id"]
    st.session_state["fitting"] = fitting


def take_off_fitting(slot):
    """試衣間脫掉某部位"""
    fitting, fur = get_fitting()
    if slot in fitting:
        del fitting[slot]
    st.session_state["fitting"] = fitting


def clear_fitting():
    """清空試衣間"""
    st.session_state["fitting"] = {}
    st.session_state["fitting_fur"] = ""


@st.dialog("🛍️ 確認購買", width="large")
def buy_dialog(fitting, fur_id):
    """購買確認：左邊「現在的你」、右邊「買了之後的你」，確認後才扣松果"""
    today = today_text()
    profiles, profile = load_my_profile()
    ledger = load_data(PINECONES_PATH)
    balance = squirrel.total_pinecones(ledger, me())
    cost = shop.fitting_cost(profile, fitting, fur_id, today)
    after_fur = profile["fur"]
    if fur_id != "":
        after_fur = fur_id
    before_svg = avatar_html(profile, 170)
    after_svg = squirrel_img(after_fur, shop.fitting_outfit(profile, fitting), 170)

    col1, col2, col3 = st.columns([5, 1, 5])
    with col1:
        st.html(STAGE_STYLE + stage_html(before_svg, "現在的你", False))
    with col2:
        st.html('<div style="font-size:34px;text-align:center;padding-top:70px">➜</div>')
    with col3:
        st.html(STAGE_STYLE + stage_html(after_svg, "換上之後 ✨", True))

    lines = ""
    for item in cost["items"]:
        price = shop.price_of(item, today)
        note = ""
        if price < item["price"]:
            note = "（今日特價，原價 " + str(item["price"]) + "）"
        lines = (lines + '<div style="display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px dashed #E4D3AC">'
                 '<span>' + wardrobe.SLOT_NAMES[item["slot"]] + '｜<b>' + item["name"] + '</b> ' + rarity_tag(item["rarity"])
                 + ' <span style="color:#D63A3A;font-size:12px">' + note + '</span></span><span>🌰 ' + str(price) + '</span></div>')
    if cost["fur"] is not None:
        lines = (lines + '<div style="display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px dashed #E4D3AC">'
                 '<span>毛色｜<b>' + cost["fur"]["id"] + '</b> ' + rarity_tag(cost["fur"]["rarity"]) + '</span><span>🌰 '
                 + str(cost["fur"]["price"]) + '</span></div>')
    after = balance - cost["total"]
    color = "#2F7A5B"
    if after < 0:
        color = "#D63A3A"
    st.html('<div style="background:#FFFDF6;border:1.5px solid #E4D3AC;border-radius:14px;padding:10px 14px">' + lines
            + '<div style="display:flex;justify-content:space-between;margin-top:8px;font-size:15px"><span>總價</span><b>🌰 '
            + str(cost["total"]) + '</b></div><div style="display:flex;justify-content:space-between;font-size:15px">'
            '<span>目前松果 → 購買後</span><b style="color:' + color + '">🌰 ' + str(balance) + ' → ' + str(after) + '</b></div></div>')

    if after < 0:
        st.warning("還差 " + str(-after) + " 顆松果。可以去「🎯 松果任務」簽到、撿金松果、完成任務來賺！")
        if st.button("知道了", key="dlg_ok", use_container_width=True):
            st.rerun()
        return
    b1, b2 = st.columns(2)
    with b1:
        if st.button("再想想", key="dlg_cancel", use_container_width=True):
            st.rerun()
    with b2:
        if st.button("✅ 確認購買並穿上", key="dlg_confirm", type="primary", use_container_width=True):
            profiles, fresh = load_my_profile()
            fresh_ledger = load_data(PINECONES_PATH)
            result = shop.buy_bundle(fresh, fresh_ledger, fitting, fur_id, today)
            if result["ok"]:
                save_data(PINECONES_PATH, fresh_ledger)
                save_my_profile(fresh)
                bump_counter("dress")
                clear_fitting()
                notify("🎉 " + result["message"])
            else:
                notify("😢 " + result["message"])
            st.rerun()


def render_fitting_room(profile, balance, today):
    """商店最上方的試衣間：大松鼠＋正在試穿的清單＋總價"""
    fitting, fur_id = get_fitting()
    show_fur = profile["fur"]
    if fur_id != "":
        show_fur = fur_id
    outfit = shop.fitting_outfit(profile, fitting)
    cost = shop.fitting_cost(profile, fitting, fur_id, today)
    trying = len(fitting) > 0 or fur_id != ""

    with st.container(border=True):
        left, right = st.columns([2, 3])
        with left:
            caption = "🌰 " + str(balance) + " 松果"
            if trying:
                caption = "試穿中…（還沒買）"
            st.html(STAGE_STYLE + stage_html(squirrel_img(show_fur, outfit, 200), caption, trying))
        with right:
            st.markdown("#### 👀 試衣間")
            if not trying:
                st.write("在下面的商品按 **👀 試穿**，衣服會直接穿到左邊的松鼠身上。")
                st.write("可以同時試穿不同部位（帽子＋上衣＋手持…），看整套效果再一次買下。")
                st.caption("目前松果：🌰 " + str(balance))
                return
            for slot in wardrobe.SLOTS:
                if slot in fitting:
                    item = wardrobe.get_item(fitting[slot])
                    status = "✅ 已擁有"
                    if item["id"] not in profile["owned"]:
                        status = "🌰 " + str(shop.price_of(item, today))
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        st.markdown(wardrobe.SLOT_NAMES[slot] + "｜**" + item["name"] + "**　" + status)
                    with c2:
                        st.button("✖", key="fit_off_" + slot, on_click=take_off_fitting, args=(slot,))
            if fur_id != "":
                st.markdown("毛色｜**" + fur_id + "**")
            st.divider()
            st.markdown("要買的東西合計：**🌰 " + str(cost["total"]) + "**　｜　目前松果：🌰 " + str(balance))
            b1, b2 = st.columns(2)
            with b1:
                st.button("↩️ 清空試衣間", on_click=clear_fitting, use_container_width=True)
            with b2:
                label = "✨ 直接穿上"
                if cost["total"] > 0:
                    label = "🛒 買下這一套（" + str(cost["total"]) + "）"
                if st.button(label, type="primary", use_container_width=True, key="fit_buy"):
                    buy_dialog(dict(fitting), fur_id)


def shop_card(item, profile, balance, today, key_prefix):
    """商品卡：小圖是「你的松鼠穿上這件」，按鈕有 試穿／購買／穿上／脫下"""
    owned = item["id"] in profile["owned"]
    wearing = profile["outfit"].get(item["slot"]) == item["id"]
    fitting, fur_id = get_fitting()
    in_fitting = fitting.get(item["slot"]) == item["id"]
    price = shop.price_of(item, today)
    with st.container(border=True):
        preview = squirrel_img(profile["fur"], shop.try_on(profile, item["id"]), 96)
        price_html = "🌰 " + str(price)
        if price < item["price"]:
            price_html = "<s style='color:#999'>🌰 " + str(item["price"]) + "</s> <b style='color:#D63A3A'>🌰 " + str(price) + " 特價</b>"
        if owned:
            price_html = "✅ 已擁有"
        ncu = ""
        if item["ncu"]:
            ncu = ' <span style="background:#2F7A5B;color:#fff;border-radius:999px;padding:1px 8px;font-size:11px">🎓 中大</span>'
        border = ""
        if in_fitting:
            border = "box-shadow:0 0 0 3px #F2B630;"
        st.html('<div style="text-align:center;background:radial-gradient(circle,#FFF8E6 0%,#F4EAD3 75%);border-radius:14px;'
                + border + '">' + preview + '</div><div style="text-align:center;margin-top:4px"><b>' + item["name"] + '</b><br>'
                + rarity_tag(item["rarity"]) + ncu + '<div style="font-size:12px;color:#6B5B40;min-height:32px">'
                + item["desc"].replace("🎓 中大系列：", "") + '</div>' + price_html + '</div>')
        key = key_prefix + "_" + item["id"]
        if wearing:
            if st.button("👕 脫下", key=key, use_container_width=True):
                change_outfit("unequip", item)
        elif owned:
            if st.button("✨ 穿上", key=key, type="primary", use_container_width=True):
                change_outfit("equip", item)
        else:
            c1, c2 = st.columns(2)
            with c1:
                if in_fitting:
                    st.button("試穿中", key=key + "_try", disabled=True, use_container_width=True)
                else:
                    st.button("👀 試穿", key=key + "_try", on_click=try_on_item, args=(item,), use_container_width=True)
            with c2:
                if st.button("🛒 買", key=key, type="primary", use_container_width=True):
                    buy_dialog({item["slot"]: item["id"]}, "")


def change_outfit(action, item):
    """穿上或脫下一件已擁有的衣服並存檔"""
    profiles, profile = load_my_profile()
    if action == "equip":
        shop.equip(profile, item["id"])
    else:
        shop.unequip(profile, item["slot"])
    save_my_profile(profile)
    bump_counter("dress")
    take_off_fitting(item["slot"])
    st.rerun()


def render_shop_grid(items, profile, balance, today, key_prefix):
    """商品排成每列 4 個"""
    cols = st.columns(4)
    i = 0
    for item in items:
        with cols[i % 4]:
            shop_card(item, profile, balance, today, key_prefix)
        i = i + 1


def try_on_fur(fur_id):
    """試穿毛色"""
    st.session_state["fitting_fur"] = fur_id


def render_shop_page():
    """松果商店：試衣間、今日特價、分類商品、毛色"""
    st.title("🛍️ 松果商店")
    today = today_text()
    profiles, profile = load_my_profile()
    ledger = load_data(PINECONES_PATH)
    balance = squirrel.total_pinecones(ledger, me())
    get_fitting()

    render_fitting_room(profile, balance, today)

    deal = wardrobe.get_item(shop.daily_deal(today))
    deal_price = shop.price_of(deal, today)
    st.info("⏰ **今日特價**：" + deal["name"] + "　~~🌰 " + str(deal["price"]) + "~~ → **🌰 " + str(deal_price)
            + "**（8 折，在「" + wardrobe.SLOT_NAMES[deal["slot"]] + "」分頁）　｜　松果只能換虛擬造型，不能換錢")

    names = ["🎓 中大系列"]
    for slot in wardrobe.SLOTS:
        names.append(wardrobe.SLOT_NAMES[slot])
    names.append("🎨 毛色")
    tabs = st.tabs(names)
    with tabs[0]:
        st.caption("團隊原創設計，只使用「NCU」「中大」字樣與松樹、中大湖鴨子等元素，沒有使用學校官方校徽。")
        render_shop_grid(wardrobe.ncu_items(), profile, balance, today, "ncu")
    i = 1
    for slot in wardrobe.SLOTS:
        with tabs[i]:
            render_shop_grid(wardrobe.items_by_slot(slot), profile, balance, today, "s_" + slot)
        i = i + 1
    with tabs[len(names) - 1]:
        fitting, fitting_fur = get_fitting()
        cols = st.columns(5)
        j = 0
        for fur in wardrobe.FURS:
            with cols[j % 5]:
                with st.container(border=True):
                    border = ""
                    if fitting_fur == fur["id"]:
                        border = "box-shadow:0 0 0 3px #F2B630;border-radius:12px;"
                    price_text = "✅ 已擁有"
                    if fur["id"] not in profile["owned_furs"]:
                        price_text = "🌰 " + str(fur["price"])
                    st.html('<div style="text-align:center;' + border + '">' + squirrel_img(fur["id"], profile["outfit"], 80)
                            + '<br><b>' + fur["id"] + '</b><br>' + rarity_tag(fur["rarity"]) + '<br>' + price_text + '</div>')
                    key = "fur_" + fur["id"]
                    if profile["fur"] == fur["id"]:
                        st.button("使用中", key=key, disabled=True, use_container_width=True)
                    elif fur["id"] in profile["owned_furs"]:
                        if st.button("換上", key=key, use_container_width=True):
                            shop.set_fur(profile, fur["id"])
                            save_my_profile(profile)
                            bump_counter("dress")
                            st.rerun()
                    else:
                        c1, c2 = st.columns(2)
                        with c1:
                            st.button("👀", key=key + "_try", help="試穿這個毛色", on_click=try_on_fur, args=(fur["id"],),
                                      use_container_width=True)
                        with c2:
                            if st.button("🛒", key=key, help="購買", type="primary", use_container_width=True):
                                buy_dialog({}, fur["id"])
            j = j + 1


# ======================================================================
# 🐿️ 我的松鼠（衣櫃、徽章、排行榜、隱私）
# ======================================================================

def render_me_page():
    """我的松鼠：衣櫃換裝、松果、徽章、排行榜、隱私設定"""
    st.title("🐿️ 我的松鼠")
    user = me()
    profiles, profile = load_my_profile()
    ledger = load_data(PINECONES_PATH)

    left, right = st.columns([2, 3])
    with left:
        with st.container(border=True):
            st.markdown("#### 👗 我的衣櫃")
            fur_index = 0
            if profile["fur"] in profile["owned_furs"]:
                fur_index = profile["owned_furs"].index(profile["fur"])
            fur = st.selectbox("毛色", profile["owned_furs"], index=fur_index, key="me_fur")
            new_outfit = {}
            for slot in wardrobe.SLOTS:
                options = ["（不穿）"]
                ids = [""]
                for item_id in profile["owned"]:
                    item = wardrobe.get_item(item_id)
                    if item is not None and item["slot"] == slot:
                        options.append(item["name"])
                        ids.append(item_id)
                index = 0
                if profile["outfit"].get(slot, "") in ids:
                    index = ids.index(profile["outfit"][slot])
                choice = st.selectbox(wardrobe.SLOT_NAMES[slot], options, index=index, key="me_slot_" + slot)
                new_outfit[slot] = ids[options.index(choice)]
            st.html('<div style="text-align:center;background:radial-gradient(circle,#FFF5DA 0%,#F2E8D2 70%);'
                    'border-radius:20px;padding:10px">' + squirrel_img(fur, new_outfit, 190)
                    + '<div style="font-weight:700;font-size:18px">' + user + '</div></div>')
            st.caption("衣服不夠？到「🛍️ 松果商店」用松果兌換。")
            visible = st.toggle("在地圖上顯示我的松鼠（關掉＝隱身）", value=profile.get("visible", True), key="me_visible")
            on_board = st.toggle("出現在松果排行榜", value=profile.get("on_board", True), key="me_board")
            if st.button("💾 儲存", type="primary", use_container_width=True):
                profiles, fresh = load_my_profile()
                changed = fresh["fur"] != fur or fresh["outfit"] != new_outfit
                shop.set_fur(fresh, fur)
                for slot in wardrobe.SLOTS:
                    if new_outfit[slot] == "":
                        shop.unequip(fresh, slot)
                    else:
                        shop.equip(fresh, new_outfit[slot])
                fresh["visible"] = visible
                fresh["on_board"] = on_board
                save_my_profile(fresh)
                if changed:
                    bump_counter("dress")
                notify("✨ 已儲存")
                st.rerun()

    with right:
        c1, c2, c3 = st.columns(3)
        c1.metric("🌰 目前松果", squirrel.total_pinecones(ledger, user))
        c2.metric("👕 收藏", str(len(profile["owned"])) + "/" + str(len(wardrobe.ITEMS)))
        c3.metric("🧭 走過的區域", str(len(profile.get("visited_all", []))) + "/" + str(len(campus_map.ZONES)))

        st.markdown("#### 🏅 徽章")
        unlocked = squirrel.get_badges(ledger, profile)
        html = '<div style="display:flex;flex-wrap:wrap;gap:8px">'
        for b in squirrel.BADGES:
            style = "background:#FFF5DA;border:2px solid #E9C55A"
            if b["id"] not in unlocked:
                style = "background:#EEE;border:2px dashed #CCC;filter:grayscale(1);opacity:.55"
            html = (html + '<div style="' + style + ';border-radius:14px;padding:8px 10px;width:118px;text-align:center">'
                    '<div style="font-size:28px">' + b["icon"] + '</div><div style="font-weight:700;font-size:14px">' + b["name"]
                    + '</div><div style="font-size:11px;color:#6B5B40">' + b["desc"] + '</div></div>')
        st.html(html + '</div>')

        st.markdown("#### 🏆 松果排行榜（累計賺到的松果，買東西不會扣）")
        rows = squirrel.leaderboard(ledger, profiles, 10)
        html = '<div style="display:flex;flex-direction:column;gap:4px">'
        rank = 1
        for r in rows:
            medal = str(rank) + "."
            if rank == 1:
                medal = "🥇"
            elif rank == 2:
                medal = "🥈"
            elif rank == 3:
                medal = "🥉"
            bg = "#FFFFFF"
            if r["nickname"] == user:
                bg = "#FFF0C2"
            html = (html + '<div style="display:flex;align-items:center;gap:10px;background:' + bg
                    + ';border:1px solid #E7DAB8;border-radius:12px;padding:2px 12px">'
                    '<span style="width:28px;font-size:18px">' + medal + '</span>'
                    + avatar_html(r["profile"], 40)
                    + '<span style="flex:1;font-weight:600">' + r["nickname"] + '</span><span>🌰 ' + str(r["total"]) + '</span></div>')
            rank = rank + 1
        st.html(html + '</div>')

        with st.expander("🧾 我的松果紀錄"):
            mine = []
            for row in ledger:
                if row["nickname"] == user:
                    mine.append(row)
            if len(mine) == 0:
                st.caption("還沒有紀錄。")
            for row in sorted(mine, key=get_created, reverse=True)[:30]:
                sign = "+"
                if row["amount"] < 0:
                    sign = ""
                st.write("🌰 " + sign + str(row["amount"]) + "　" + row["reason"] + "　" + row["created_at"])


# ======================================================================
# 🔎 失物招領（主線）
# ======================================================================

def render_matches(item, items, prefix):
    """顯示某筆刊登的配對結果（規則候選 → AI 重新排序與理由）"""
    candidates = lostfound.find_matches(item, items, 5)
    if len(candidates) == 0:
        st.caption("目前沒有分數達門檻（≥4）的配對，之後有人刊登會再出現。")
        return
    # 同一組候選只問一次 AI，避免每次重跑畫面都重新呼叫
    cache_key = "match_" + str(item["id"])
    ids = []
    for c in candidates:
        ids.append(c["item"]["id"])
    cached = st.session_state.get(cache_key)
    if cached is None or cached["ids"] != ids:
        cached = {"ids": ids, "result": ai_helper.rerank_matches(item, candidates)}
        st.session_state[cache_key] = cached
    result = cached["result"]
    source_badge(result["source"])
    rank = 1
    for m in result["data"][:3]:
        other = m["item"]
        with st.container(border=True):
            st.markdown("**#" + str(rank) + "　" + other["kind"] + "：" + other["name"] + "**　（規則分數 "
                        + str(m["score"]) + "）")
            st.write("💡 " + m["reason"])
            st.caption("計分明細：" + "；".join(m.get("detail", [])))
            if other["owner"] != me():
                if st.button("💬 聯絡 " + other["owner"], key=prefix + "_match_contact_" + str(item["id"]) + "_" + str(other["id"])):
                    if other["kind"] == "拾獲":
                        st.session_state["claim_target"] = other["id"]
                        st.info("這是拾獲刊登，請到「瀏覽與搜尋」找到這筆，先回答驗證問題再私訊。")
                    else:
                        start_chat("item", other, [])
        rank = rank + 1


def render_item_card(item, items, prefix):
    """顯示一筆失物刊登卡片與可做的動作"""
    user = me()
    with st.container(border=True):
        icon = "🟢 拾獲"
        if item["kind"] == "遺失":
            icon = "🔴 遺失"
        st.markdown("#### " + icon + "｜" + item["name"])
        st.caption(item["category"] + "　📍" + item["location"] + "　📅" + item["date"]
                   + "　👤" + item["owner"] + "　狀態：" + item["status"])
        st.write(item["description"])
        if len(item["keywords"]) > 0:
            st.caption("🏷️ " + "、".join(item["keywords"]))
        if item["category"] == "證件卡片":
            st.info("🪪 證件類冒領風險較高，建議同時交給校內既有的失物招領管道（如總務處或警衛室，以學校公告為準）。")

        if item["status"] != "尋找中":
            return
        key = prefix + "_" + str(item["id"])
        if item["owner"] == user:
            helper = ""
            if item["kind"] == "遺失":
                peers = chat.peers_of_target(load_all_threads(), "item", item["id"])
                if len(peers) > 0:
                    pick = st.selectbox("誰幫你找到的？（他會得到 " + str(squirrel.REWARD_RETURN_ITEM) + " 顆松果）",
                                        ["（我自己找到的）"] + peers, key="helper_" + key)
                    if pick != "（我自己找到的）":
                        helper = pick
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🧩 看配對", key="show_match_" + key):
                    st.session_state["open_match_" + key] = not st.session_state.get("open_match_" + key, False)
                    if st.session_state["open_match_" + key]:
                        bump_counter("match")
            with col2:
                if st.button("✅ 標記已尋回", key="resolve_" + key):
                    all_items = load_data(LOSTFOUND_PATH)       # 寫入前重新讀檔
                    target = find_by_id(all_items, item["id"])
                    if target is not None and lostfound.mark_resolved(target, user):
                        save_data(LOSTFOUND_PATH, all_items)
                        notify("🎉 已標記為已尋回！")
                        if helper != "":
                            give_pinecones(helper, squirrel.REWARD_RETURN_ITEM, "物歸原主", "return:item:" + str(item["id"]))
                        st.rerun()
            if st.session_state.get("open_match_" + key, False):
                render_matches(item, items, prefix)
        else:
            if item["kind"] == "拾獲":
                with st.expander("🙋 這可能是我的 → 回答驗證問題後私訊",
                                 expanded=(st.session_state.get("claim_target") == item["id"])):
                    st.caption("你的答案只會給拾獲者看，由拾獲者「人工」判斷是否為失主。")
                    answers = []
                    i = 0
                    for q in item["verify_questions"]:
                        answers.append(st.text_input(q, key="claim_" + key + "_" + str(i)))
                        i = i + 1
                    if st.button("送出答案並開啟私訊", key="claim_btn_" + key):
                        filled = True
                        for a in answers:
                            if a.strip() == "":
                                filled = False
                        if not filled:
                            st.warning("請先回答所有驗證問題。")
                        else:
                            masked = []
                            for a in answers:
                                masked.append(ai_helper.mask_sensitive(a.strip()))
                            start_chat("item", item, masked)
            else:
                if st.button("💬 我撿到了，私訊 " + item["owner"], key="contact_" + key):
                    start_chat("item", item, [])


def render_item_form():
    """刊登表單（含 AI-1 一句話填表、AI-5 驗證問題）"""
    user = me()
    st.markdown("##### ✨ 一句話刊登")
    one = st.text_input("用一句話描述，例如：「昨天下午在圖書館掉了黑色保溫水壺」", key="lf_one")
    if st.button("🪄 幫我填表", key="lf_parse"):
        result = ai_helper.parse_form_text(one, "item")
        data = result["data"]
        # 在表單元件「畫出來之前」設定 session_state，就能把值填進去
        if data["kind"] in lostfound.KINDS:
            st.session_state["lf_kind"] = data["kind"]
        st.session_state["lf_name"] = data["name"]
        st.session_state["lf_category"] = data["category"]
        st.session_state["lf_location"] = data["location"]
        st.session_state["lf_date"] = to_date(data["date"], date.today())
        st.session_state["lf_desc"] = data["description"]
        st.session_state["lf_kw"] = "、".join(data["keywords"])
        st.session_state["lf_parse_info"] = {"source": result["source"], "missing": data["missing"]}

    info = st.session_state.get("lf_parse_info")
    if info is not None:
        source_badge(info["source"])
        if len(info["missing"]) > 0:
            st.warning("還缺：" + "、".join(info["missing"]) + "，請在下面補填。")
        else:
            st.success("欄位都填好了，請檢查後送出。")

    st.divider()
    st.caption(PRIVACY_NOTE)
    kind = st.radio("種類", lostfound.KINDS, horizontal=True, key="lf_kind")
    name = st.text_input("物品名稱", key="lf_name")
    category = st.selectbox("類別", lostfound.CATEGORIES, key="lf_category")
    if category == "證件卡片":
        st.info("🪪 證件類物品請同時交由校內既有的失物招領管道處理（如總務處或警衛室，以學校公告為準）。")
    location = st.text_input("地點", key="lf_location")
    item_date = st.date_input("日期", key="lf_date")
    desc = st.text_area("描述（外觀、特徵）", key="lf_desc")
    kw = st.text_input("關鍵字（用逗號或頓號分隔，最多 5 個）", key="lf_kw")

    questions = []
    answers = []
    if kind == "拾獲":
        st.markdown("##### 🔐 認領驗證問題（只有失主答得出）")
        if st.button("🪄 建議驗證問題", key="lf_q_btn"):
            q = ai_helper.make_verify_questions({"name": name, "category": category, "description": desc})
            st.session_state["lf_q1"] = q["data"][0]
            st.session_state["lf_q2"] = q["data"][1]
            st.session_state["lf_q_source"] = q["source"]
        if "lf_q_source" in st.session_state:
            source_badge(st.session_state["lf_q_source"])
        q1 = st.text_input("問題 1", key="lf_q1")
        a1 = st.text_input("問題 1 的正確答案（只有你看得到，不會送給 AI）", key="lf_a1")
        q2 = st.text_input("問題 2", key="lf_q2")
        a2 = st.text_input("問題 2 的正確答案（只有你看得到，不會送給 AI）", key="lf_a2")
        st.caption("⚠️ 請不要把答案寫進公開描述裡。")
        questions = [q1, q2]
        answers = [a1, a2]

    if st.button("📮 送出刊登", type="primary", key="lf_submit"):
        if name.strip() == "" or location.strip() == "":
            st.error("請填寫物品名稱與地點。")
            return
        if kind == "拾獲" and (questions[0].strip() == "" or questions[1].strip() == ""):
            st.error("拾獲刊登需要 2 個驗證問題。")
            return
        warn_sensitive(name, location, desc)
        item = lostfound.create_item(kind, ai_helper.mask_sensitive(name), category, ai_helper.mask_sensitive(location),
                                     item_date.strftime("%Y-%m-%d"), ai_helper.mask_sensitive(desc), split_words(kw), user,
                                     questions, answers)
        items = load_data(LOSTFOUND_PATH)        # 寫入前重新讀檔
        item["id"] = get_next_id(items)
        items.append(item)
        save_data(LOSTFOUND_PATH, items)
        st.success("刊登成功！下面是系統找到的可能配對：")
        st.session_state["lf_parse_info"] = None
        render_matches(item, items, "new")


def render_lostfound_page():
    """失物招領頁（含 AI-1、AI-2、AI-3、AI-5）"""
    st.title("🔎 失物招領")
    st.caption("示範資料｜聯絡走站內私訊，不公開聯絡方式")
    items = load_data(LOSTFOUND_PATH)
    tab_browse, tab_new, tab_mine = st.tabs(["瀏覽與搜尋", "我要刊登", "我的刊登"])

    with tab_browse:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            kind = st.selectbox("種類", ["全部"] + lostfound.KINDS, key="lf_f_kind")
        with col2:
            category = st.selectbox("類別", ["全部"] + lostfound.CATEGORIES, key="lf_f_cat")
        with col3:
            status = st.selectbox("狀態", ["尋找中", "已尋回", "全部"], key="lf_f_status")
        with col4:
            keyword = st.text_input("關鍵字", key="lf_f_kw")
        result = lostfound.search_items(items, kind, category, keyword, status)
        st.caption("共 " + str(len(result)) + " 筆")
        for item in result:
            render_item_card(item, items, "browse")

    with tab_new:
        if me() == "":
            st.warning("請先登入才能刊登。")
        else:
            render_item_form()

    with tab_mine:
        mine = []
        for item in items:
            if item["owner"] == me():
                mine.append(item)
        if len(mine) == 0:
            st.caption("你還沒有刊登。")
        for item in lostfound.sort_by_created(mine):
            render_item_card(item, items, "mine")


# ======================================================================
# 🤝 任務互助
# ======================================================================

def render_task_form():
    """發布任務表單（含 AI-1 一句話填表、AI-6 規範檢查）"""
    user = me()
    st.markdown("##### ✨ 一句話發布")
    one = st.text_input("例如：「明天中午幫我帶一杯飲料到圖書館，請你喝一杯」", key="tk_one")
    if st.button("🪄 幫我填表", key="tk_parse"):
        result = ai_helper.parse_form_text(one, "task")
        data = result["data"]
        st.session_state["tk_type"] = data["type"]
        st.session_state["tk_title"] = data["title"]
        st.session_state["tk_desc"] = data["description"]
        st.session_state["tk_location"] = data["location"]
        st.session_state["tk_date"] = to_date(data["deadline"], date.today())
        st.session_state["tk_time"] = to_time(data["deadline"], time(18, 0))
        st.session_state["tk_reward"] = data["reward"]
        st.session_state["tk_kw"] = "、".join(data["keywords"])
        st.session_state["tk_parse_info"] = {"source": result["source"], "missing": data["missing"]}

    info = st.session_state.get("tk_parse_info")
    if info is not None:
        source_badge(info["source"])
        if len(info["missing"]) > 0:
            st.warning("還缺：" + "、".join(info["missing"]) + "，請在下面補填。")

    st.divider()
    st.caption(PRIVACY_NOTE)
    task_type = st.selectbox("類型", tasks_mod.TASK_TYPES, key="tk_type")
    title = st.text_input("標題", key="tk_title")
    desc = st.text_area("說明", key="tk_desc")
    location = st.text_input("地點", key="tk_location")
    col1, col2 = st.columns(2)
    with col1:
        d = st.date_input("截止日期", key="tk_date")
    with col2:
        t = st.time_input("截止時間", key="tk_time")
    reward = st.text_input("酬勞（雙方自行約定的文字說明，平台不經手金流）", key="tk_reward")
    slots = st.number_input("需要人數", min_value=1, max_value=20, value=1, key="tk_slots")
    kw = st.text_input("關鍵字（逗號分隔）", key="tk_kw")

    check = st.session_state.get("tk_check")
    ack = False
    if check is not None and check["data"]["level"] == "提醒":
        ack = st.checkbox("我已閱讀上面的提醒，仍要發布", key="tk_ack")

    if st.button("🛡️ 檢查規範並發布", type="primary", key="tk_submit"):
        if title.strip() == "" or location.strip() == "":
            st.error("請填寫標題與地點。")
            return
        check = ai_helper.check_task_rules(title, desc + " " + reward)
        st.session_state["tk_check"] = check
        level = check["data"]["level"]
        if level == "禁止":
            st.error("⛔ 不能發布：" + "；".join(check["data"]["reasons"]))
            source_badge(check["source"])
            return
        if level == "提醒" and not ack:
            st.rerun()   # 重跑一次讓「我已閱讀」勾選框出現
        warn_sensitive(title, desc, location, reward)
        task = tasks_mod.create_task(task_type, ai_helper.mask_sensitive(title), ai_helper.mask_sensitive(desc),
                                     ai_helper.mask_sensitive(location), d.strftime("%Y-%m-%d") + " " + t.strftime("%H:%M"),
                                     ai_helper.mask_sensitive(reward), int(slots), split_words(kw), user)
        all_tasks = load_data(TASKS_PATH)
        task["id"] = get_next_id(all_tasks)
        all_tasks.append(task)
        save_data(TASKS_PATH, all_tasks)
        st.session_state["tk_check"] = None
        st.session_state["tk_parse_info"] = None
        st.success("發布成功！")

    check = st.session_state.get("tk_check")
    if check is not None and check["data"]["level"] == "提醒":
        st.warning("⚠️ 規範提醒：\n- " + "\n- ".join(check["data"]["reasons"]))
        source_badge(check["source"])


def render_task_card(task, prefix):
    """顯示一筆任務卡片與動作"""
    user = me()
    with st.container(border=True):
        st.markdown("#### [" + task["type"] + "] " + task["title"])
        st.caption("📍" + task["location"] + "　⏰ 截止 " + task["deadline"] + "　👤" + task["owner"]
                   + "　狀態：" + task["status"] + "　名額 " + str(len(task["helpers"])) + "/" + str(task["slots"]))
        st.write(task["description"])
        if task["reward"] != "":
            st.caption("🎁 酬勞：" + task["reward"] + "（雙方自行約定，平台不經手金流）")
        key = prefix + "_" + str(task["id"])
        if task["owner"] == user:
            if len(task["helpers"]) > 0:
                st.caption("已接單：" + "、".join(task["helpers"]))
            if task["status"] in ("招募中", "已額滿"):
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ 完成", key="tk_done_" + key):
                        update_task(task["id"], "complete")
                with col2:
                    if st.button("🗑️ 取消", key="tk_cancel_" + key):
                        update_task(task["id"], "cancel")
        else:
            if user in task["helpers"]:
                if st.button("💬 私訊發布者", key="tk_chat_" + key):
                    start_chat("task", task, [])
            elif task["status"] == "招募中":
                if st.button("🙋 我要接單", key="tk_accept_" + key):
                    all_tasks = load_data(TASKS_PATH)           # 寫入前重新讀檔
                    target = find_by_id(all_tasks, task["id"])
                    result = tasks_mod.accept_task(target, user)
                    if result["ok"]:
                        save_data(TASKS_PATH, all_tasks)
                        start_chat("task", result["task"], [])
                    else:
                        st.error(result["message"])


def update_task(task_id, action):
    """完成或取消任務（先重新讀檔再寫入）"""
    all_tasks = load_data(TASKS_PATH)
    target = find_by_id(all_tasks, task_id)
    if target is None:
        return
    if action == "complete":
        ok = tasks_mod.complete_task(target, me())
    else:
        ok = tasks_mod.cancel_task(target, me())
    if ok:
        save_data(TASKS_PATH, all_tasks)
        if action == "complete":
            # 由發布者按「完成」，每位接單者各得松果（不能自己發給自己）
            for helper in target["helpers"]:
                give_pinecones(helper, squirrel.REWARD_HELP_TASK, "完成任務", "task:" + str(task_id) + ":" + helper)
        st.rerun()
    else:
        st.error("無法變更這個任務的狀態。")


def render_task_page():
    """任務互助頁（含 AI-1、AI-6）"""
    st.title("🤝 任務互助")
    st.caption("示範資料｜禁止代考代寫、違禁品、索取帳號密碼；平台不經手金流")
    all_tasks = load_data(TASKS_PATH)
    tab_browse, tab_new, tab_mine = st.tabs(["瀏覽任務", "發布任務", "我的任務"])
    with tab_browse:
        col1, col2, col3 = st.columns(3)
        with col1:
            task_type = st.selectbox("類型", ["全部"] + tasks_mod.TASK_TYPES, key="tk_f_type")
        with col2:
            status = st.selectbox("狀態", ["招募中", "已額滿", "已完成", "已取消", "全部"], key="tk_f_status")
        with col3:
            keyword = st.text_input("關鍵字", key="tk_f_kw")
        result = tasks_mod.list_tasks(all_tasks, task_type, keyword, status)
        st.caption("共 " + str(len(result)) + " 筆（依截止時間由近到遠）")
        for task in result:
            render_task_card(task, "browse")
    with tab_new:
        if me() == "":
            st.warning("請先登入才能發布。")
        else:
            render_task_form()
    with tab_mine:
        found = False
        for task in all_tasks:
            if task["owner"] == me() or me() in task["helpers"]:
                render_task_card(task, "mine")
                found = True
        if not found:
            st.caption("你還沒有發布或接下任務。")


# ======================================================================
# 🎪 活動資訊（精簡版）
# ======================================================================

def render_event_card(event, key_prefix):
    """顯示一筆活動"""
    user = me()
    with st.container(border=True):
        st.markdown("#### " + event["title"])
        st.caption("[" + event["category"] + "] " + event["org"] + "　📍" + event["place"]
                   + "　🕒 " + event["start"] + " ～ " + event["end"][11:])
        st.write(event["description"])
        st.caption("🏷️ " + "、".join(event["tags"]) + "　❤️ " + str(len(event["interested"])) + " 人有興趣")
        col1, col2 = st.columns(2)
        with col1:
            if user != "":
                label = "❤️ 有興趣"
                if user in event["interested"]:
                    label = "💔 取消有興趣"
                if st.button(label, key=key_prefix + "_int_" + str(event["id"])):
                    all_events = load_data(EVENTS_PATH)
                    target = find_by_id(all_events, event["id"])
                    if target is not None:
                        events_mod.toggle_interest(target, user)
                        save_data(EVENTS_PATH, all_events)
                        if user in target["interested"]:
                            bump_counter("interest")
                        st.rerun()
        with col2:
            if event["link"] != "":
                st.link_button("🔗 報名／資訊連結（外部網站）", event["link"])


def render_event_page():
    """活動資訊頁（含 AI-1、AI-7）"""
    st.title("🎪 活動資訊")
    st.caption("示範資料｜系統只顯示發布者填的連結，不抓取、不轉載外部內容")
    all_events = load_data(EVENTS_PATH)
    tab_browse, tab_rec, tab_new = st.tabs(["瀏覽活動", "AI 興趣推薦", "發布活動"])

    with tab_browse:
        col1, col2, col3 = st.columns(3)
        with col1:
            category = st.selectbox("分類", ["全部"] + events_mod.EVENT_CATEGORIES, key="ev_f_cat")
        with col2:
            keyword = st.text_input("關鍵字", key="ev_f_kw")
        with col3:
            upcoming = st.checkbox("只看未結束", value=True, key="ev_f_up")
        for event in events_mod.list_events(all_events, category, keyword, upcoming):
            render_event_card(event, "browse")

    with tab_rec:
        interest = st.text_input("說說你的興趣，例如：「喜歡攝影，想認識新朋友」", key="ev_interest")
        if st.button("🪄 推薦給我", key="ev_rec_btn"):
            upcoming_events = events_mod.list_events(all_events, "全部", "", True)
            st.session_state["ev_rec"] = ai_helper.recommend_events(upcoming_events, interest)
        rec = st.session_state.get("ev_rec")
        if rec is not None:
            source_badge(rec["source"])
            if len(rec["data"]) == 0:
                st.caption("目前沒有符合的活動，換個說法試試看。")
            for r in rec["data"]:
                st.write("💡 " + r["reason"])
                latest = find_by_id(all_events, r["event"]["id"])
                if latest is not None:
                    render_event_card(latest, "rec")

    with tab_new:
        if me() == "":
            st.warning("請先登入才能發布。")
            return
        one = st.text_input("一句話發布，例如：「週五晚上有攝影社新生體驗」", key="ev_one")
        if st.button("🪄 幫我填表", key="ev_parse"):
            result = ai_helper.parse_form_text(one, "event")
            data = result["data"]
            st.session_state["ev_title"] = data["title"]
            st.session_state["ev_org"] = data["org"]
            st.session_state["ev_cat"] = data["category"]
            st.session_state["ev_place"] = data["place"]
            st.session_state["ev_date"] = to_date(data["start"], date.today())
            st.session_state["ev_start"] = to_time(data["start"], time(19, 0))
            st.session_state["ev_end"] = to_time(data["end"], time(21, 0))
            st.session_state["ev_tags"] = "、".join(data["tags"])
            st.session_state["ev_desc"] = data["description"]
            st.session_state["ev_source"] = result["source"]
        if "ev_source" in st.session_state:
            source_badge(st.session_state["ev_source"])
        st.caption(PRIVACY_NOTE)
        title = st.text_input("活動名稱", key="ev_title")
        org = st.text_input("主辦單位", key="ev_org")
        category = st.selectbox("分類", events_mod.EVENT_CATEGORIES, key="ev_cat")
        place = st.text_input("地點", key="ev_place")
        d = st.date_input("日期", key="ev_date")
        col1, col2 = st.columns(2)
        with col1:
            start_t = st.time_input("開始", key="ev_start")
        with col2:
            end_t = st.time_input("結束", key="ev_end")
        desc = st.text_area("說明", key="ev_desc")
        tags = st.text_input("標籤（逗號分隔）", key="ev_tags")
        link = st.text_input("報名連結（選填，需以 https:// 開頭）", key="ev_link")
        if st.button("📮 發布活動", type="primary", key="ev_submit"):
            if title.strip() == "":
                st.error("請填寫活動名稱。")
                return
            day_text = d.strftime("%Y-%m-%d")
            warn_sensitive(title, desc)
            event = events_mod.create_event(ai_helper.mask_sensitive(title), org, category, place,
                                            day_text + " " + start_t.strftime("%H:%M"), day_text + " " + end_t.strftime("%H:%M"),
                                            ai_helper.mask_sensitive(desc), split_words(tags), link, me())
            latest = load_data(EVENTS_PATH)
            event["id"] = get_next_id(latest)
            latest.append(event)
            save_data(EVENTS_PATH, latest)
            st.success("發布成功！")


# ======================================================================
# 💬 我的私訊（準即時，約 3 秒更新）
# ======================================================================

@st.fragment(run_every=3)
def chat_box(thread_id, user):
    """每 3 秒自動重新讀檔，顯示最新訊息、驗證狀態與面交卡片"""
    thread = load_thread(thread_id)
    if thread is None or not chat.is_participant(thread, user):
        st.error("你沒有權限查看這個討論串。")     # 沙盒：非參與者一律看不到
        return

    # 狀態列
    status_text = "對象：" + thread["target_title"] + "　｜　對方：" + chat.other_person(thread, user)
    if thread["verified"] != "不適用":
        status_text = status_text + "　｜　認領驗證：" + thread["verified"]
    st.caption(status_text)

    # 面交卡片
    meetup = thread["meetup"]
    if meetup is not None:
        with st.container(border=True):
            icon = "⏳"
            if meetup["status"] == "已確認":
                icon = "✅"
            st.markdown(icon + " **面交／交接（" + meetup["status"] + "）**：" + meetup["place"] + "｜" + meetup["time"])
            st.caption("提出者：" + meetup["proposed_by"] + "　已確認：" + "、".join(meetup["confirmed_by"]))
            if meetup["status"] == "待確認" and user not in meetup["confirmed_by"]:
                if st.button("👍 確認這個時間地點", key="confirm_meetup_" + str(thread_id)):
                    fresh = load_thread(thread_id)          # 寫入前重新讀檔
                    fresh = chat.confirm_meetup(fresh, user)
                    save_thread(fresh)
                    st.rerun()

    # 訊息
    with st.container(height=380):
        for msg in thread["messages"]:
            if msg["kind"] == "system":
                st.info("📢 " + msg["text"] + "　(" + msg["created_at"][11:] + ")")
            elif msg["sender"] == user:
                with st.chat_message("user"):
                    st.write(msg["text"])
                    st.caption("我 · " + msg["created_at"][11:])
            else:
                with st.chat_message("assistant", avatar="🧑"):
                    st.write(msg["text"])
                    st.caption(msg["sender"] + " · " + msg["created_at"][11:])
    st.caption("🔄 準即時：約每 3 秒自動更新")


def do_send(thread_id, text):
    """真正寫入一則訊息：寫入前立刻重新讀檔再附加，縮小兩人同時寫入的衝突"""
    user = me()
    blocks = load_data(BLOCKS_PATH)
    thread = load_thread(thread_id)
    if thread is None:
        return
    if chat.is_blocked(blocks, user, chat.other_person(thread, user)):
        st.session_state["chat_error"] = "此對話已封鎖，無法傳送訊息。"
        return
    before = len(thread["messages"])
    thread = chat.send_message(thread, user, text, "user")
    save_thread(thread)
    if len(thread["messages"]) > before:
        bump_counter("message")


def on_send(thread_id):
    """按下「送出」的回呼：先做隱私與防詐檢查，有疑慮就先暫存、讓使用者決定"""
    key = "chat_text_" + str(thread_id)
    text = st.session_state.get(key, "").strip()
    if text == "":
        return
    sensitive = ai_helper.detect_sensitive(text)
    scam = ai_helper.detect_scam_risk(text)
    if len(sensitive) > 0 or len(scam) > 0:
        st.session_state["pending_msg"] = {"thread_id": thread_id, "text": text, "sensitive": sensitive, "scam": scam}
    else:
        do_send(thread_id, text)
    st.session_state[key] = ""


def on_pending(choice):
    """處理暫存訊息：原樣送出／遮蔽後送出／取消"""
    pending = st.session_state.get("pending_msg")
    if pending is None:
        return
    if choice == "send":
        do_send(pending["thread_id"], pending["text"])
    elif choice == "mask":
        do_send(pending["thread_id"], ai_helper.mask_sensitive(pending["text"]))
    st.session_state["pending_msg"] = None


def on_quick_reply(thread_id, text):
    """點快速回覆：只把草稿放進輸入框，不自動送出（人在迴圈）"""
    st.session_state["chat_text_" + str(thread_id)] = text


def render_chat_actions(thread_id):
    """聊天視窗下方的輸入框、快速回覆、面交、驗證、檢舉封鎖"""
    user = me()
    thread = load_thread(thread_id)
    if thread is None or not chat.is_participant(thread, user):
        return
    other = chat.other_person(thread, user)
    blocks = load_data(BLOCKS_PATH)
    blocked = chat.is_blocked(blocks, user, other)

    if st.session_state.get("chat_error"):
        st.error(st.session_state["chat_error"])
        st.session_state["chat_error"] = ""

    # ---- 暫存訊息（AI-3 隱私提醒＋防詐提醒）----
    pending = st.session_state.get("pending_msg")
    if pending is not None and pending["thread_id"] == thread_id:
        with st.container(border=True):
            st.warning("你準備送出的訊息：「" + pending["text"] + "」")
            if len(pending["sensitive"]) > 0:
                types = []
                for s in pending["sensitive"]:
                    if s["type"] not in types:
                        types.append(s["type"])
                st.write("🔒 偵測到個資：" + "、".join(types) + "。站內私訊已能聯絡，通常不需要提供。")
            if len(pending["scam"]) > 0:
                st.write("🚨 防詐提醒：" + "、".join(pending["scam"]) + "。平台不經手金錢，請勿先付款或提供驗證碼。")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.button("遮蔽個資後送出", on_click=on_pending, args=("mask",), key="pend_mask")
            with col2:
                st.button("仍要原樣送出", on_click=on_pending, args=("send",), key="pend_send")
            with col3:
                st.button("取消", on_click=on_pending, args=("cancel",), key="pend_cancel")

    if blocked:
        st.error("🚫 此對話已封鎖，無法再傳送訊息。")
        return

    # ---- 輸入框 ----
    col1, col2 = st.columns([5, 1])
    with col1:
        st.text_input("輸入訊息（最多 300 字）", key="chat_text_" + str(thread_id), max_chars=chat.MAX_MESSAGE_LEN,
                      label_visibility="collapsed", placeholder="輸入訊息…")
    with col2:
        st.button("送出", on_click=on_send, args=(thread_id,), type="primary", key="send_" + str(thread_id))

    # ---- AI-4 快速回覆 ----
    if st.button("🪄 快速回覆草稿", key="qr_btn_" + str(thread_id)):
        st.session_state["qr_" + str(thread_id)] = ai_helper.quick_replies(thread, user)
    qr = st.session_state.get("qr_" + str(thread_id))
    if qr is not None:
        source_badge(qr["source"])
        cols = st.columns(3)
        i = 0
        for reply in qr["data"]:
            with cols[i]:
                st.button(reply, on_click=on_quick_reply, args=(thread_id, reply), key="qr_" + str(thread_id) + "_" + str(i))
            i = i + 1

    # ---- 找出這個討論串對應的物品或任務 ----
    if thread["target_type"] == "item":
        target = find_by_id(load_data(LOSTFOUND_PATH), thread["target_id"])
    else:
        target = find_by_id(load_data(TASKS_PATH), thread["target_id"])
    if target is None:
        target = {"location": "", "category": "", "name": thread["target_title"], "title": thread["target_title"]}

    # ---- 認領驗證（只有拾獲者看得到答案並判定）----
    if thread["verified"] != "不適用" and user == thread["owner"]:
        with st.expander("🔐 認領驗證（只有你看得到）", expanded=(thread["verified"] == "未驗證")):
            questions = target.get("verify_questions", [])
            correct = target.get("verify_answers", [])
            i = 0
            for q in questions:
                answer = "（未回答）"
                if i < len(thread["claim_answers"]):
                    answer = thread["claim_answers"][i]
                right = ""
                if i < len(correct):
                    right = correct[i]
                st.write("**" + q + "**")
                st.write("　對方回答：" + answer + "　｜　你設定的答案：" + right)
                i = i + 1
            st.caption("由你「人工」判斷；系統與 AI 不會自動判定。目前：" + thread["verified"])
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ 通過", key="verify_ok_" + str(thread_id)):
                    fresh = chat.verify_claim(load_thread(thread_id), user, True)
                    save_thread(fresh)
                    st.rerun()
            with col2:
                if st.button("❌ 未通過", key="verify_no_" + str(thread_id)):
                    fresh = chat.verify_claim(load_thread(thread_id), user, False)
                    save_thread(fresh)
                    st.rerun()

    # ---- 認領者：確認已拿回（拾獲者得到松果、物品自動改成已尋回）----
    if (thread["verified"] == "通過" and user == thread["peer"] and not thread.get("received")
            and thread["target_type"] == "item"):
        st.success("拾獲者已確認你的認領！面交拿到東西後，請按下面的按鈕。")
        if st.button("✅ 我已拿回物品（送 " + str(squirrel.REWARD_RETURN_ITEM) + " 顆松果給拾獲者）", key="received_" + str(thread_id)):
            all_items = load_data(LOSTFOUND_PATH)
            item = find_by_id(all_items, thread["target_id"])
            fresh = load_thread(thread_id)
            if item is not None and lostfound.mark_returned(item, fresh, user):
                save_data(LOSTFOUND_PATH, all_items)
                save_thread(chat.confirm_received(fresh, user))
                give_pinecones(thread["owner"], squirrel.REWARD_RETURN_ITEM, "物歸原主", "return:item:" + str(item["id"]))
                st.rerun()

    # ---- 面交／交接（AI-4 建議地點與時段）----
    with st.expander("📍 提出面交／交接"):
        if st.button("🪄 建議安全地點與時段", key="meet_ai_" + str(thread_id)):
            st.session_state["meet_" + str(thread_id)] = ai_helper.suggest_meetup(thread["target_type"], target, thread)
        sug = st.session_state.get("meet_" + str(thread_id))
        spots = ai_helper.SAFE_SPOTS
        slots = []
        if sug is not None:
            source_badge(sug["source"])
            st.info("🛡️ " + sug["data"]["tips"])
            spots = sug["data"]["spots"]
            for s in ai_helper.SAFE_SPOTS:
                if s not in spots:
                    spots = spots + [s]
            slots = sug["data"]["slots"]
        place = st.selectbox("地點（安全地點清單）", spots, key="meet_place_" + str(thread_id))
        if len(slots) > 0:
            st.caption("建議時段：" + "、".join(slots))
        col1, col2 = st.columns(2)
        with col1:
            md = st.date_input("日期", key="meet_date_" + str(thread_id))
        with col2:
            mt = st.time_input("時間", value=time(12, 10), key="meet_time_" + str(thread_id))
        if st.button("📨 提出", key="meet_send_" + str(thread_id)):
            fresh = load_thread(thread_id)
            fresh = chat.propose_meetup(fresh, user, place, md.strftime("%Y-%m-%d") + " " + mt.strftime("%H:%M"))
            save_thread(fresh)
            st.rerun()

    # ---- 檢舉與封鎖 ----
    with st.expander("🚩 檢舉／封鎖"):
        reason = st.selectbox("原因", chat.REPORT_REASONS, key="rep_reason_" + str(thread_id))
        note = st.text_input("補充說明（選填，200 字內）", key="rep_note_" + str(thread_id))
        col1, col2 = st.columns(2)
        with col1:
            if st.button("送出檢舉", key="rep_btn_" + str(thread_id)):
                reports = load_data(REPORTS_PATH)
                reports.append(chat.create_report(reports, thread, user, reason, note))
                save_data(REPORTS_PATH, reports)
                st.success("已記錄檢舉（討論串 #" + str(thread_id) + "）。若有立即危險請聯絡校安中心。")
        with col2:
            if st.button("🚫 封鎖對方", key="block_btn_" + str(thread_id)):
                save_data(BLOCKS_PATH, chat.block_user(load_data(BLOCKS_PATH), user, other))
                fresh = chat.send_message(load_thread(thread_id), chat.SYSTEM_NAME, "此對話已被封鎖。", "system")
                save_thread(fresh)
                st.rerun()


def render_chat_page():
    """我的私訊（chat_box 準即時、面交卡片、AI-4、AI-3 提醒、檢舉封鎖）"""
    st.title("💬 我的私訊")
    user = me()
    threads = chat.get_threads_for_user(load_all_threads(), user)
    if len(threads) == 0:
        st.caption("還沒有私訊。到失物招領或任務互助按「聯絡」就會出現在這裡。")
        return

    labels = []
    ids = []
    for t in threads:
        tag = "[任務]"
        if t["target_type"] == "item":
            tag = "[失物]"
        labels.append(tag + " " + t["target_title"] + " — 與 " + chat.other_person(t, user) + "（" + t["updated_at"][5:] + "）")
        ids.append(t["id"])
    active = st.session_state.get("active_thread", 0)
    index = 0
    if active in ids:
        index = ids.index(active)
    choice = st.selectbox("選擇對話", labels, index=index, key="thread_choice_" + str(active))
    thread_id = ids[labels.index(choice)]
    st.session_state["active_thread"] = thread_id

    chat_box(thread_id, user)
    render_chat_actions(thread_id)


# ======================================================================
# 主程式
# ======================================================================

def main():
    """導覽、未登入導向、整合"""
    st.set_page_config(page_title="中大圈 NCU Loop", page_icon="🐿️", layout="wide")
    storage.ensure_dirs()
    if "user" not in st.session_state:
        st.session_state["user"] = ""
    apply_style()

    render_auth_sidebar()

    # 其他頁面要求跳頁時（例如按了「聯絡」），在選單畫出來之前先改值
    if st.session_state.get("goto"):
        st.session_state["page"] = st.session_state["goto"]
        st.session_state["goto"] = ""
    page = st.sidebar.radio("功能選單", PAGES, key="page")
    show_notes()

    # 每天第一次進來：跳出簽到視窗（同一個瀏覽器分頁只跳一次）
    if me() != "" and st.session_state.get("checkin_prompted") != today_text():
        st.session_state["checkin_prompted"] = today_text()
        profiles_now, profile_now = load_my_profile()
        if not quests.has_checked_in(profile_now, today_text()):
            checkin_dialog()

    if page == PAGE_HOME:
        render_home_page()
        return
    if page == PAGE_MAP:
        render_map_page()
        return
    if me() == "" and page in (PAGE_CHAT, PAGE_ME, PAGE_QUEST, PAGE_SHOP):
        st.warning("請先從左邊登入。")
        return
    if me() == "":
        st.info("你目前是訪客，可以瀏覽；刊登、接單、私訊需要先登入。")

    if page == PAGE_LF:
        render_lostfound_page()
    elif page == PAGE_TASK:
        render_task_page()
    elif page == PAGE_EVENT:
        render_event_page()
    elif page == PAGE_CHAT:
        render_chat_page()
    elif page == PAGE_ME:
        render_me_page()
    elif page == PAGE_QUEST:
        render_quest_page()
    elif page == PAGE_SHOP:
        render_shop_page()


def apply_style():
    """一點點自訂樣式：圓角卡片、標題字重（主要配色寫在 .streamlit/config.toml）"""
    st.markdown("""
<style>
h1, h2, h3, h4 { font-weight: 800 !important; letter-spacing: .5px; }
div[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 16px !important; }
div[data-testid="stMetric"] { background: #FFFFFF; border: 1.5px solid #EADDBC; border-radius: 16px; padding: 10px 14px; }
button[kind="primary"] { border-radius: 999px !important; }
div[data-testid="stSidebar"] { background: #F4EAD3; }
</style>
""", unsafe_allow_html=True)


main()
