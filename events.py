# events.py —— 活動資訊邏輯（M3，精簡版）：發布、瀏覽、標記有興趣
# 依助教建議，活動只做精簡版；簡報主線放在「失物招領＋安全私訊」

from storage import now_text

EVENT_CATEGORIES = ["學術講座", "藝文表演", "運動競賽", "志工服務", "社團招生", "其他"]


def create_event(title, org, category, place, start, end, description, tags, link, owner):
    """建立新活動（dict，interested 為空，尚未存檔）"""
    link = link.strip()
    if link != "" and not (link.startswith("https://") or link.startswith("http://")):
        link = ""   # 只接受 http(s) 開頭的連結，避免奇怪的連結格式
    return {
        "id": 0,
        "title": title.strip(),
        "org": org.strip(),
        "category": category,
        "place": place.strip(),
        "start": start,
        "end": end,
        "description": description.strip(),
        "tags": tags,
        "link": link,
        "owner": owner,
        "interested": [],
        "created_at": now_text(),
    }


def get_start(event):
    """排序用：取出開始時間"""
    return event.get("start", "")


def list_events(events, category, keyword, only_upcoming, now=""):
    """依分類、關鍵字篩選；only_upcoming 為真時排除已結束者；依開始時間由近到遠"""
    if now == "":
        now = now_text()
    result = []
    keyword = keyword.strip()
    for event in events:
        if category not in ("", "全部") and event["category"] != category:
            continue
        if only_upcoming and event["end"] < now:
            continue
        if keyword != "":
            text = event["title"] + event["org"] + event["description"] + " ".join(event["tags"])
            if keyword not in text:
                continue
        result.append(event)
    return sorted(result, key=get_start)


def toggle_interest(event, nickname):
    """切換「有興趣」：名單裡有就移除、沒有就加入，回傳更新後的活動"""
    if nickname in event["interested"]:
        event["interested"].remove(nickname)
    else:
        event["interested"].append(nickname)
    return event
