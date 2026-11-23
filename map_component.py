# map_component.py —— 把 components/squirrel_map/index.html 包成 Streamlit 可以用的元件
# 用法：value = squirrel_map(args, key="campus_map")
#       使用者點了地圖上的區域，value 會變成 {"zone": "library", "ts": 1732333333333}
#       ts 是時間戳記，用來分辨「這是新的點擊」還是「上一次留下來的值」

import os

import streamlit.components.v1 as components

_COMPONENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "components", "squirrel_map")
_squirrel_map = components.declare_component("squirrel_map", path=_COMPONENT_DIR)


def squirrel_map(args, key):
    """顯示松鼠地圖，回傳使用者最後一次點選的區域（沒有就回傳 None）"""
    return _squirrel_map(zones=args["zones"], me=args["me"], others=args["others"],
                         selected=args["selected"], highlight=args["highlight"],
                         treasures=args.get("treasures", []),
                         key=key, default=None)
