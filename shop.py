# shop.py —— 松果商店：用松果兌換衣服與毛色、穿上／脫下、每日特價
# 松果只能換「虛擬造型」，不能換錢或實體商品。

import squirrel
import wardrobe
import quests

DAILY_DISCOUNT = 20    # 每日特價打 8 折（減 20%）


def daily_deal(today):
    """今天的特價商品 id（每天不同，大家一樣；免費的不會被選到）"""
    paid = []
    for item in wardrobe.ITEMS:
        if item["price"] > 0:
            paid.append(item["id"])
    return quests.pick_from(paid, 1, "deal:" + today)[0]


def price_of(item, today):
    """某件衣服今天的價格（特價品打折）"""
    if item["id"] == daily_deal(today):
        return item["price"] * (100 - DAILY_DISCOUNT) // 100
    return item["price"]


def buy_item(profile, ledger, item_id, today):
    """買衣服：回傳 {"ok", "message"}；成功會扣松果（記一筆負數）並加入衣櫃"""
    item = wardrobe.get_item(item_id)
    if item is None:
        return {"ok": False, "message": "找不到這件商品"}
    if item_id in profile["owned"]:
        return {"ok": False, "message": "你已經有這件了"}
    price = price_of(item, today)
    balance = squirrel.total_pinecones(ledger, profile["nickname"])
    if balance < price:
        return {"ok": False, "message": "松果不夠，還差 " + str(price - balance) + " 顆"}
    if not squirrel.add_pinecones(ledger, profile["nickname"], -price, "商店購買",
                                  "buy:" + profile["nickname"] + ":" + item_id):
        return {"ok": False, "message": "這件已經買過了"}
    profile["owned"].append(item_id)
    return {"ok": True, "message": "買到「" + item["name"] + "」了！花了 " + str(price) + " 顆松果"}


def buy_fur(profile, ledger, fur_id):
    """買毛色：同樣扣松果"""
    fur = wardrobe.get_fur(fur_id)
    if fur["id"] != fur_id:
        return {"ok": False, "message": "找不到這個毛色"}
    if fur_id in profile["owned_furs"]:
        return {"ok": False, "message": "你已經有這個毛色了"}
    balance = squirrel.total_pinecones(ledger, profile["nickname"])
    if balance < fur["price"]:
        return {"ok": False, "message": "松果不夠，還差 " + str(fur["price"] - balance) + " 顆"}
    if not squirrel.add_pinecones(ledger, profile["nickname"], -fur["price"], "商店購買",
                                  "buyfur:" + profile["nickname"] + ":" + fur_id):
        return {"ok": False, "message": "這個毛色已經買過了"}
    profile["owned_furs"].append(fur_id)
    return {"ok": True, "message": "換上新毛色「" + fur_id + "」了！"}


def equip(profile, item_id):
    """穿上某件衣服（要先擁有）；同部位的舊衣服會被換掉。回傳 True 代表成功"""
    item = wardrobe.get_item(item_id)
    if item is None or item_id not in profile["owned"]:
        return False
    profile["outfit"][item["slot"]] = item_id
    return True


def unequip(profile, slot):
    """脫下某部位的衣服"""
    if slot in profile["outfit"]:
        profile["outfit"][slot] = ""
    return profile


def set_fur(profile, fur_id):
    """換毛色（要先擁有）"""
    if fur_id not in profile["owned_furs"]:
        return False
    profile["fur"] = fur_id
    return True


def try_on(profile, item_id):
    """試穿：回傳一份「穿上這件之後」的穿搭（不會改到原本的檔案）"""
    outfit = dict(profile["outfit"])
    item = wardrobe.get_item(item_id)
    if item is not None:
        outfit[item["slot"]] = item_id
    return outfit


# ======================================================================
# 試衣間：可以同時試穿好幾件（還沒買的也可以），看整套效果再決定
# ======================================================================

def fitting_outfit(profile, fitting):
    """把「試衣間裡的衣服」疊在目前穿搭上，回傳新的穿搭（不會改到原本檔案）"""
    outfit = dict(profile["outfit"])
    for slot in fitting:
        outfit[slot] = fitting[slot]
    return outfit


def fitting_cost(profile, fitting, fur_id, today):
    """算出試衣間裡「還沒擁有」的東西：回傳 {"items": [...], "fur": 毛色或 None, "total": 總價}"""
    result = {"items": [], "fur": None, "total": 0}
    for slot in fitting:
        item = wardrobe.get_item(fitting[slot])
        if item is not None and item["id"] not in profile["owned"]:
            result["items"].append(item)
            result["total"] = result["total"] + price_of(item, today)
    if fur_id != "" and fur_id not in profile["owned_furs"]:
        fur = wardrobe.get_fur(fur_id)
        result["fur"] = fur
        result["total"] = result["total"] + fur["price"]
    return result


def buy_bundle(profile, ledger, fitting, fur_id, today):
    """一次買下試衣間裡所有還沒擁有的東西並穿上；松果不夠就一件都不買"""
    cost = fitting_cost(profile, fitting, fur_id, today)
    balance = squirrel.total_pinecones(ledger, profile["nickname"])
    if balance < cost["total"]:
        return {"ok": False, "message": "松果不夠，還差 " + str(cost["total"] - balance) + " 顆"}
    for item in cost["items"]:
        buy_item(profile, ledger, item["id"], today)
    if cost["fur"] is not None:
        buy_fur(profile, ledger, cost["fur"]["id"])
    for slot in fitting:
        if fitting[slot] == "":
            unequip(profile, slot)
        else:
            equip(profile, fitting[slot])
    if fur_id != "":
        set_fur(profile, fur_id)
    return {"ok": True, "message": "整套換上了！花了 " + str(cost["total"]) + " 顆松果"}
