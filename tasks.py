# tasks.py —— 任務互助邏輯（M2）：發布、瀏覽、接單、完成、取消
# 酬勞 reward 只是雙方自行約定的文字說明，平台不經手任何金錢

from storage import now_text

TASK_TYPES = ["代拿代購", "代跑腿", "揪人", "日常求助"]
TASK_STATUSES = ["招募中", "已額滿", "已完成", "已取消"]


def create_task(task_type, title, description, location, deadline, reward, slots, keywords, owner):
    """建立新任務（dict，狀態「招募中」，尚未存檔；id 由呼叫端補上）"""
    if slots < 1:
        slots = 1
    return {
        "id": 0,
        "type": task_type,
        "title": title.strip(),
        "description": description.strip(),
        "location": location.strip(),
        "deadline": deadline,
        "reward": reward.strip(),
        "slots": slots,
        "helpers": [],
        "keywords": keywords,
        "owner": owner,
        "status": "招募中",
        "created_at": now_text(),
    }


def get_deadline(task):
    """排序用：取出截止時間"""
    return task.get("deadline", "")


def list_tasks(tasks, task_type, keyword, status):
    """依類型、關鍵字、狀態篩選；"全部" 與空字串代表不篩選；依截止時間由近到遠"""
    result = []
    keyword = keyword.strip()
    for task in tasks:
        if task_type not in ("", "全部") and task["type"] != task_type:
            continue
        if status not in ("", "全部") and task["status"] != status:
            continue
        if keyword != "":
            text = task["title"] + task["description"] + task["location"] + " ".join(task["keywords"])
            if keyword not in text:
                continue
        result.append(task)
    return sorted(result, key=get_deadline)


def accept_task(task, nickname):
    """接單：擋下發布者本人、重複接單、非招募中；人數滿了改成「已額滿」"""
    if task["owner"] == nickname:
        return {"ok": False, "message": "不能接自己發布的任務", "task": task}
    if nickname in task["helpers"]:
        return {"ok": False, "message": "你已經接過這個任務了", "task": task}
    if task["status"] != "招募中":
        return {"ok": False, "message": "這個任務目前是「" + task["status"] + "」，不能接單", "task": task}
    task["helpers"].append(nickname)
    if len(task["helpers"]) >= task["slots"]:
        task["status"] = "已額滿"
    return {"ok": True, "message": "接單成功！請到「我的私訊」和發布者確認細節", "task": task}


def complete_task(task, nickname):
    """只有發布者、且狀態為招募中或已額滿時，才能改成「已完成」"""
    if task["owner"] != nickname:
        return False
    if task["status"] not in ("招募中", "已額滿"):
        return False
    task["status"] = "已完成"
    return True


def cancel_task(task, nickname):
    """只有發布者能取消（已完成的任務不能再取消）"""
    if task["owner"] != nickname:
        return False
    if task["status"] == "已完成":
        return False
    task["status"] = "已取消"
    return True
