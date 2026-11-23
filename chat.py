# chat.py —— 站內私訊與面交約定（CH，失物與任務共用），以及檢舉／封鎖
#
# 安全設計（回應助教「獨立沙盒、詐騙、資安」的提醒）：
#   1. 沙盒：每個討論串只存在自己的檔案 data/chats/thread_編號.json，
#      只有 owner 與 peer 兩人能讀寫（is_participant），畫面每次顯示前都會檢查
#   2. 防詐：訊息送出前由 ai_helper.detect_scam_risk 檢查（匯款、驗證碼、外部連結…）並提醒
#   3. 檢舉＋封鎖：任何一方可檢舉（記錄原因與討論串 id），封鎖後雙方都不能再傳訊息
#   4. 訊息長度上限 300 字，避免灌爆檔案

from storage import now_text

MAX_MESSAGE_LEN = 300
SYSTEM_NAME = "系統"
REPORT_REASONS = ["疑似詐騙（要求匯款、驗證碼、帳號密碼）", "騷擾或不當言語", "冒領或身分可疑", "其他"]


def open_thread(threads, target_type, target, peer, claim_answers):
    """開啟討論串：同目標同 peer 已有就回傳舊的；peer 是刊登者本人回傳 None"""
    owner = target["owner"]
    if peer == owner:
        return None
    for thread in threads:
        if (thread["target_type"] == target_type and thread["target_id"] == target["id"]
                and thread["peer"] == peer):
            return thread

    # 判斷這個討論串需不需要認領驗證
    verified = "不適用"
    if target_type == "item" and target.get("kind") == "拾獲":
        verified = "未驗證"
    else:
        claim_answers = []

    if target_type == "item":
        title = target["name"]
    else:
        title = target["title"]

    now = now_text()
    return {
        "id": 0,                  # 由呼叫端用 get_next_id 補上
        "target_type": target_type,
        "target_id": target["id"],
        "target_title": title,
        "owner": owner,
        "peer": peer,
        "claim_answers": claim_answers,
        "verified": verified,
        "meetup": None,
        "messages": [],
        "created_at": now,
        "updated_at": now,
    }


def get_updated_at(thread):
    """排序用：取出最後更新時間"""
    return thread.get("updated_at", "")


def get_threads_for_user(threads, nickname):
    """回傳該使用者參與的討論串，依更新時間新到舊"""
    result = []
    for thread in threads:
        if is_participant(thread, nickname):
            result.append(thread)
    return sorted(result, key=get_updated_at, reverse=True)


def is_participant(thread, nickname):
    """只有 owner 與 peer 是參與者"""
    return nickname == thread["owner"] or nickname == thread["peer"]


def other_person(thread, me):
    """回傳討論串中「另一個人」的暱稱"""
    if me == thread["owner"]:
        return thread["peer"]
    return thread["owner"]


def next_message_id(thread):
    """討論串內訊息編號遞增"""
    max_id = 0
    for msg in thread["messages"]:
        if msg["id"] > max_id:
            max_id = msg["id"]
    return max_id + 1


def send_message(thread, sender, text, kind):
    """附加一則訊息並更新時間；非參與者、空白訊息則原樣回傳（系統訊息不檢查參與者）"""
    text = text.strip()
    if text == "":
        return thread
    if kind != "system" and not is_participant(thread, sender):
        return thread
    if len(text) > MAX_MESSAGE_LEN:
        text = text[:MAX_MESSAGE_LEN]
    now = now_text()
    thread["messages"].append({
        "id": next_message_id(thread),
        "sender": sender,
        "text": text,
        "kind": kind,
        "created_at": now,
    })
    thread["updated_at"] = now
    return thread


def get_new_messages(thread, last_id):
    """回傳 id 大於 last_id 的訊息"""
    result = []
    for msg in thread["messages"]:
        if msg["id"] > last_id:
            result.append(msg)
    return result


def propose_meetup(thread, sender, place, time_text):
    """提出面交：設定 meetup 為待確認，提出者自動算已確認，並加系統訊息"""
    if not is_participant(thread, sender):
        return thread
    if place.strip() == "" or time_text.strip() == "":
        return thread
    thread["meetup"] = {
        "place": place.strip(),
        "time": time_text.strip(),
        "proposed_by": sender,
        "confirmed_by": [sender],
        "status": "待確認",
    }
    text = sender + " 提出面交／交接：" + place.strip() + "，" + time_text.strip()
    return send_message(thread, SYSTEM_NAME, text, "system")


def confirm_meetup(thread, nickname):
    """對方確認後狀態改「已確認」；提出者自己不能重複確認"""
    meetup = thread["meetup"]
    if meetup is None or not is_participant(thread, nickname):
        return thread
    if nickname in meetup["confirmed_by"]:
        return thread
    meetup["confirmed_by"].append(nickname)
    meetup["status"] = "已確認"
    text = nickname + " 已確認面交：" + meetup["place"] + "，" + meetup["time"] + "。請約在人多的公共場所。"
    return send_message(thread, SYSTEM_NAME, text, "system")


def verify_claim(thread, nickname, passed):
    """只有 owner、且是失物討論串，才能把認領驗證設為「通過／未通過」"""
    if thread["target_type"] != "item" or nickname != thread["owner"]:
        return thread
    if thread["verified"] == "不適用":
        return thread
    if passed:
        thread["verified"] = "通過"
        text = nickname + " 判定認領驗證：通過"
    else:
        thread["verified"] = "未通過"
        text = nickname + " 判定認領驗證：未通過，請勿交付物品"
    return send_message(thread, SYSTEM_NAME, text, "system")


def confirm_received(thread, nickname):
    """認領者確認「我已拿回物品」，加一則系統訊息（物品狀態由 lostfound.mark_returned 改）"""
    if thread["target_type"] != "item" or nickname != thread["peer"] or thread["verified"] != "通過":
        return thread
    if thread.get("received"):
        return thread
    thread["received"] = True
    text = nickname + " 確認已拿回物品，謝謝 " + thread["owner"] + "！🌰 拾獲者獲得松果"
    return send_message(thread, SYSTEM_NAME, text, "system")


def peers_of_target(threads, target_type, target_id):
    """某個物品或任務的所有聯絡人（用來讓失主選「誰幫我找到的」）"""
    result = []
    for t in threads:
        if t["target_type"] == target_type and t["target_id"] == target_id and t["peer"] not in result:
            result.append(t["peer"])
    return result


# ---------- 檢舉與封鎖（最小版） ----------

def create_report(reports, thread, reporter, reason, note):
    """建立一筆檢舉紀錄（只記錄原因、說明、討論串 id，不複製訊息內容）"""
    max_id = 0
    for r in reports:
        if r["id"] > max_id:
            max_id = r["id"]
    return {
        "id": max_id + 1,
        "thread_id": thread["id"],
        "reporter": reporter,
        "reported": other_person(thread, reporter),
        "reason": reason,
        "note": note.strip()[:200],
        "status": "待處理",
        "created_at": now_text(),
    }


def is_blocked(blocks, user_a, user_b):
    """任何一方封鎖了另一方就回傳 True"""
    for b in blocks:
        if b["blocker"] == user_a and b["blocked"] == user_b:
            return True
        if b["blocker"] == user_b and b["blocked"] == user_a:
            return True
    return False


def block_user(blocks, blocker, blocked):
    """新增一筆封鎖（已封鎖過就不重複），回傳新的 list"""
    for b in blocks:
        if b["blocker"] == blocker and b["blocked"] == blocked:
            return blocks
    blocks.append({"blocker": blocker, "blocked": blocked, "created_at": now_text()})
    return blocks
