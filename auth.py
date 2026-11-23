# auth.py —— 帳號：註冊、登入、密碼雜湊
# 依助教建議：改用「加鹽」雜湊（PBKDF2-SHA256，標準函式庫 hashlib 就有），密碼至少 6 碼
# 注意：這是示範等級的登入，不是正式安全方案（正式版應串接校方登入）

import hashlib
import os

from storage import now_text

HASH_ROUNDS = 100000   # 雜湊重複次數，越多越難暴力破解


def make_salt():
    """產生一段隨機的鹽（16 bytes，轉成十六進位字串）"""
    return os.urandom(16).hex()


def hash_password(password, salt):
    """用鹽把密碼雜湊成十六進位字串；同樣的密碼＋同樣的鹽，結果一定相同"""
    result = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), HASH_ROUNDS)
    return result.hex()


def find_user(users, nickname):
    """在使用者清單中找暱稱相同的人，找不到回傳 None"""
    for user in users:
        if user["nickname"] == nickname:
            return user
    return None


def register_user(users, nickname, password):
    """註冊：檢查暱稱 2–12 字且不重複、密碼至少 6 碼；成功時 user 是新帳號（尚未存檔）"""
    nickname = nickname.strip()
    if len(nickname) < 2 or len(nickname) > 12:
        return {"ok": False, "message": "暱稱需要 2–12 個字", "user": None}
    if nickname == "系統":
        return {"ok": False, "message": "這個暱稱保留給系統使用", "user": None}
    if find_user(users, nickname) is not None:
        return {"ok": False, "message": "這個暱稱已經有人用了", "user": None}
    if len(password) < 6:
        return {"ok": False, "message": "密碼至少需要 6 碼", "user": None}

    salt = make_salt()
    user = {
        "nickname": nickname,
        "salt": salt,
        "password_hash": hash_password(password, salt),
        "created_at": now_text(),
    }
    return {"ok": True, "message": "註冊成功！", "user": user}


def login_user(users, nickname, password):
    """登入：暱稱存在且密碼雜湊相符才回傳 True"""
    user = find_user(users, nickname.strip())
    if user is None:
        return False
    return hash_password(password, user["salt"]) == user["password_hash"]
