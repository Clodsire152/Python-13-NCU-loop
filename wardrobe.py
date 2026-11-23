# wardrobe.py —— 松鼠衣櫃：所有衣服與毛色的資料（名稱、部位、價格、稀有度、SVG 圖形）
#
# 部位（slot）：head 頭飾、face 臉部、body 上衣、hand 手持、back 背部
# 松鼠畫布是 64×64，面向左邊。重要座標：頭中心 (23,26) 半徑 11；身體中心 (29,44)；
#   眼睛 (19,24.5)；鼻子 (11.5,28)；手（抱松果的位置）(19,42)；尾巴在右邊
#
# 🎓 中大系列：只使用「NCU」「中大」文字和松樹、中大湖鴨子等元素，都是團隊自己畫的原創設計，
#    沒有使用學校官方校徽。如果之後想放官方校徽或做成實體周邊，必須先取得學校授權。

SLOTS = ["head", "face", "body", "hand", "back"]
SLOT_NAMES = {"head": "頭飾", "face": "臉部", "body": "上衣", "hand": "手持", "back": "背部"}
RARITY_COLORS = {"普通": "#7A8B99", "稀有": "#2E7DD7", "傳說": "#D18A00"}

# 毛色：前 5 種免費，後面要用松果買
FURS = [
    {"id": "栗棕", "colors": ["#B0702F", "#7A4A1C"], "price": 0, "rarity": "普通"},
    {"id": "灰松", "colors": ["#9A9A9A", "#626262"], "price": 0, "rarity": "普通"},
    {"id": "橘紅", "colors": ["#D8712F", "#9B4615"], "price": 0, "rarity": "普通"},
    {"id": "奶茶", "colors": ["#CDA57F", "#93704E"], "price": 0, "rarity": "普通"},
    {"id": "巧克力", "colors": ["#7A4A2A", "#4A2A14"], "price": 0, "rarity": "普通"},
    {"id": "雪白", "colors": ["#F1EDE6", "#C9C2B6"], "price": 80, "rarity": "稀有"},
    {"id": "黑夜", "colors": ["#3F3F4E", "#22222C"], "price": 80, "rarity": "稀有"},
    {"id": "抹茶", "colors": ["#8DB36B", "#5E8546"], "price": 120, "rarity": "稀有"},
    {"id": "星空紫", "colors": ["#7B5EC6", "#4A3487"], "price": 300, "rarity": "傳說"},
    {"id": "黃金", "colors": ["#E9B949", "#B8862A"], "price": 400, "rarity": "傳說"},
]

# 每件衣服：id、名稱、部位、價格（0＝新手免費）、稀有度、是否中大系列、說明、SVG
ITEMS = [
    # ───────────── 頭飾 ─────────────
    {"id": "grad_cap", "name": "學士帽", "slot": "head", "price": 0, "rarity": "普通", "ncu": False, "desc": "新手禮物，祝你順利畢業",
     "svg": '<path d="M10 14 L25 8 L40 14 L25 20 Z" fill="#222"/><rect x="19" y="14" width="12" height="5" fill="#222"/>'
            '<path d="M39 14 L41 23" stroke="#F2C230" stroke-width="1.6"/><circle cx="41" cy="24" r="1.8" fill="#F2C230"/>'},
    {"id": "flower", "name": "小花", "slot": "head", "price": 30, "rarity": "普通", "ncu": False, "desc": "別在耳朵上的粉紅小花",
     "svg": '<circle cx="31" cy="9" r="2.4" fill="#FF8FB1"/><circle cx="35" cy="11" r="2.4" fill="#FF8FB1"/>'
            '<circle cx="33" cy="14" r="2.4" fill="#FF8FB1"/><circle cx="29" cy="12" r="2.4" fill="#FF8FB1"/><circle cx="32" cy="11.5" r="1.8" fill="#FFD54A"/>'},
    {"id": "headphones", "name": "耳機", "slot": "head", "price": 50, "rarity": "普通", "ncu": False, "desc": "圖書館讀書必備",
     "svg": '<path d="M13 24 Q22 6 34 20" fill="none" stroke="#333" stroke-width="2.4"/><rect x="30" y="19" width="6" height="8" rx="2" fill="#2E7DD7"/>'},
    {"id": "beanie", "name": "紅毛帽", "slot": "head", "price": 40, "rarity": "普通", "ncu": False, "desc": "冬天的中壢風很大",
     "svg": '<path d="M12 22 Q12 9 23 9 Q34 9 34 22 Z" fill="#D64545"/><rect x="11" y="19" width="24" height="5" rx="2.5" fill="#F4F4F4"/>'
            '<circle cx="23" cy="8" r="3.2" fill="#F4F4F4"/>'},
    {"id": "straw_hat", "name": "草帽", "slot": "head", "price": 40, "rarity": "普通", "ncu": False, "desc": "夏天去中大湖散步",
     "svg": '<ellipse cx="23" cy="16" rx="15" ry="3.5" fill="#E8C46A"/><path d="M15 16 Q15 7 23 7 Q31 7 31 16 Z" fill="#EFD27F"/>'
            '<rect x="15" y="12.5" width="16" height="3" fill="#C0392B"/>'},
    {"id": "cap_blue", "name": "藍色棒球帽", "slot": "head", "price": 50, "rarity": "普通", "ncu": False, "desc": "帽沿朝前，很有精神",
     "svg": '<path d="M12 19 Q12 8 23 8 Q34 8 34 17 Z" fill="#2E5EAA"/><path d="M13 19 L2 20.5 Q4 16.5 14 15.5 Z" fill="#1F4480"/>'},
    {"id": "bow", "name": "蝴蝶結", "slot": "head", "price": 45, "rarity": "普通", "ncu": False, "desc": "可愛加分",
     "svg": '<path d="M29 13 L23.5 8.5 L23.5 17.5 Z" fill="#FF6FA0"/><path d="M29 13 L34.5 8.5 L34.5 17.5 Z" fill="#FF6FA0"/>'
            '<circle cx="29" cy="13" r="2" fill="#E04B83"/>'},
    {"id": "party_hat", "name": "派對帽", "slot": "head", "price": 60, "rarity": "普通", "ncu": False, "desc": "期末考完就戴上",
     "svg": '<path d="M17 16 L24 0.5 L31 16 Z" fill="#8A5CD0"/><path d="M20 10 L28 10 M18.5 13.5 L29.5 13.5" stroke="#FFD54A" stroke-width="1.6"/>'
            '<circle cx="24" cy="1.5" r="2.2" fill="#FFD54A"/>'},
    {"id": "crown", "name": "松果王冠", "slot": "head", "price": 450, "rarity": "傳說", "ncu": False, "desc": "松林之王的象徵",
     "svg": '<path d="M13 16 L14 6 L18.5 11 L23 3.5 L27.5 11 L32 6 L33 16 Z" fill="#F5C518" stroke="#C9970C" stroke-width="1"/>'
            '<circle cx="23" cy="12" r="1.8" fill="#E0524C"/><circle cx="17" cy="13" r="1.3" fill="#2E7DD7"/><circle cx="29" cy="13" r="1.3" fill="#2F9E62"/>'},
    {"id": "ncu_cap", "name": "NCU 棒球帽", "slot": "head", "price": 120, "rarity": "稀有", "ncu": True, "desc": "🎓 中大系列：松林綠棒球帽",
     "svg": '<path d="M12 19 Q12 8 23 8 Q34 8 34 17 Z" fill="#1F6B4A"/><path d="M13 19 L2 20.5 Q4 16.5 14 15.5 Z" fill="#15513A"/>'
            '<text x="17" y="16" font-size="5.5" font-weight="bold" fill="#FFF" font-family="Arial">NCU</text>'},
    {"id": "duck_hat", "name": "中大湖鴨鴨帽", "slot": "head", "price": 150, "rarity": "稀有", "ncu": True, "desc": "🎓 中大系列：一隻小鴨坐在頭上",
     "svg": '<ellipse cx="25" cy="13" rx="7.5" ry="4.5" fill="#FFD43B"/><circle cx="20" cy="8" r="3.8" fill="#FFD43B"/>'
            '<path d="M16.5 8 L13 9 L16.5 10 Z" fill="#F08A24"/><circle cx="19" cy="7.2" r="0.9" fill="#222"/>'
            '<path d="M29 11 Q32 9 33 12" fill="none" stroke="#E0A800" stroke-width="1"/>'},

    # ───────────── 臉部 ─────────────
    {"id": "glasses", "name": "圓框眼鏡", "slot": "face", "price": 0, "rarity": "普通", "ncu": False, "desc": "新手禮物，看起來很會讀書",
     "svg": '<circle cx="19" cy="25" r="4" fill="rgba(255,255,255,0.25)" stroke="#222" stroke-width="1.4"/>'
            '<path d="M23 25 L33 23" stroke="#222" stroke-width="1.2"/>'},
    {"id": "sunglasses", "name": "墨鏡", "slot": "face", "price": 60, "rarity": "普通", "ncu": False, "desc": "酷松鼠",
     "svg": '<path d="M13.5 22.5 H24 V25.5 Q19 30 13.5 25.5 Z" fill="#111"/><path d="M24 23.5 L33 22" stroke="#111" stroke-width="1.4"/>'
            '<path d="M15 23.5 L18 23.5" stroke="#FFF" stroke-width="0.8" opacity="0.7"/>'},
    {"id": "monocle", "name": "單片眼鏡", "slot": "face", "price": 90, "rarity": "稀有", "ncu": False, "desc": "紳士的研究精神",
     "svg": '<circle cx="19" cy="24.8" r="3.7" fill="rgba(255,255,255,0.2)" stroke="#C9970C" stroke-width="1.3"/>'
            '<path d="M21 28 Q24 33 22 38" fill="none" stroke="#C9970C" stroke-width="0.8"/>'},
    {"id": "heart_blush", "name": "愛心腮紅", "slot": "face", "price": 35, "rarity": "普通", "ncu": False, "desc": "臉紅紅",
     "svg": '<path d="M17 33.5 L14.6 31 Q13.6 29.4 15.2 28.9 Q16.4 28.7 17 29.9 Q17.6 28.7 18.8 28.9 Q20.4 29.4 19.4 31 Z" fill="#FF5C8A"/>'},
    {"id": "mustache", "name": "小鬍子", "slot": "face", "price": 45, "rarity": "普通", "ncu": False, "desc": "教授的威嚴",
     "svg": '<path d="M7.5 31 Q10 28.5 12.5 30 Q15 28.5 17.5 31 Q14.5 33 12.5 31.6 Q10.5 33 7.5 31 Z" fill="#3A2418"/>'},

    # ───────────── 上衣 ─────────────
    {"id": "scarf_red", "name": "紅圍巾", "slot": "body", "price": 0, "rarity": "普通", "ncu": False, "desc": "新手禮物，暖暖的",
     "svg": '<path d="M15 34 Q25 40 35 33 L35 38 Q25 45 15 39 Z" fill="#D63A3A"/><rect x="29" y="36" width="5" height="10" rx="2" fill="#B82828"/>'},
    {"id": "bowtie", "name": "領結", "slot": "body", "price": 40, "rarity": "普通", "ncu": False, "desc": "正式場合必備",
     "svg": '<path d="M25 37 L19.5 34 L19.5 40 Z" fill="#C0392B"/><path d="M25 37 L30.5 34 L30.5 40 Z" fill="#C0392B"/><circle cx="25" cy="37" r="1.6" fill="#8E2A20"/>'},
    {"id": "sweater", "name": "條紋毛衣", "slot": "body", "price": 70, "rarity": "普通", "ncu": False, "desc": "暖色系條紋",
     "svg": '<path d="M17 41 Q17 32 29 32 Q41 32 41 41 L41 50 Q29 55 17 50 Z" fill="#E8A33D"/>'
            '<path d="M17.5 39 Q29 35 40.5 39 M17 44 Q29 41 41 44 M17.5 49 Q29 46 40.5 49" stroke="#FFF3D6" stroke-width="1.8" fill="none"/>'},
    {"id": "lab_coat", "name": "實驗袍", "slot": "body", "price": 90, "rarity": "稀有", "ncu": False, "desc": "科學館的日常",
     "svg": '<path d="M17 41 Q17 32 29 32 Q41 32 41 41 L42 55 Q29 58 16 55 Z" fill="#FAFAFA" stroke="#CCC" stroke-width="0.8"/>'
            '<path d="M24 33 L27 42 L30 33" fill="none" stroke="#BBB" stroke-width="1"/><rect x="31" y="45" width="6" height="4" fill="none" stroke="#BBB"/>'
            '<path d="M32 44 L32 47" stroke="#2E7DD7" stroke-width="1"/>'},
    {"id": "raincoat", "name": "小雨衣", "slot": "body", "price": 60, "rarity": "普通", "ncu": False, "desc": "下雨天也要去上課",
     "svg": '<path d="M17 41 Q17 32 29 32 Q41 32 41 41 L42 54 Q29 57 16 54 Z" fill="#FFD43B"/>'
            '<circle cx="27" cy="39" r="1.1" fill="#C99A00"/><circle cx="27" cy="44" r="1.1" fill="#C99A00"/><circle cx="27" cy="49" r="1.1" fill="#C99A00"/>'},
    {"id": "ncu_tee", "name": "NCU 字樣T恤", "slot": "body", "price": 100, "rarity": "稀有", "ncu": True, "desc": "🎓 中大系列：松林綠短T",
     "svg": '<path d="M17 41 Q17 32 29 32 Q41 32 41 41 L41 50 Q29 55 17 50 Z" fill="#2F7A5B"/>'
            '<text x="21.5" y="46" font-size="6" font-weight="bold" fill="#FFF" font-family="Arial">NCU</text>'},
    {"id": "ncu_hoodie", "name": "中大帽T", "slot": "body", "price": 160, "rarity": "稀有", "ncu": True, "desc": "🎓 中大系列：深藍色連帽上衣",
     "svg": '<path d="M17 41 Q17 32 29 32 Q41 32 41 41 L41 51 Q29 56 17 51 Z" fill="#23395B"/>'
            '<path d="M30 32 Q37 30 39 36" fill="none" stroke="#1A2A44" stroke-width="3"/>'
            '<path d="M25 34 L25 39 M28 34 L28 39" stroke="#E8E8E8" stroke-width="0.8"/>'
            '<text x="22" y="48" font-size="6" font-weight="bold" fill="#FFF">中大</text>'},
    {"id": "ncu_jersey", "name": "NCU 系際盃球衣", "slot": "body", "price": 180, "rarity": "稀有", "ncu": True, "desc": "🎓 中大系列：白底綠邊運動衣",
     "svg": '<path d="M17 41 Q17 32 29 32 Q41 32 41 41 L41 50 Q29 55 17 50 Z" fill="#FFFFFF" stroke="#2F7A5B" stroke-width="1.6"/>'
            '<text x="22.5" y="41" font-size="3.6" font-weight="bold" fill="#2F7A5B" font-family="Arial">NCU</text>'
            '<text x="22.5" y="49" font-size="7" font-weight="bold" fill="#2F7A5B" font-family="Arial">01</text>'},
    {"id": "pine_scarf", "name": "松濤圍巾", "slot": "body", "price": 130, "rarity": "稀有", "ncu": True, "desc": "🎓 中大系列：綠白條紋，象徵中大的松",
     "svg": '<path d="M15 34 Q25 40 35 33 L35 38 Q25 45 15 39 Z" fill="#2F7A5B"/>'
            '<path d="M18 35.5 L18 40.5 M23 36.8 L23 42 M28 36.6 L28 41.6" stroke="#FFF" stroke-width="1.6"/>'
            '<rect x="29" y="36" width="5" height="11" rx="2" fill="#2F7A5B"/><path d="M29 40 L34 40 M29 43.5 L34 43.5" stroke="#FFF" stroke-width="1.4"/>'},
    {"id": "duck_ring", "name": "中大湖鴨鴨泳圈", "slot": "body", "price": 200, "rarity": "稀有", "ncu": True, "desc": "🎓 中大系列：（請勿真的下湖游泳）",
     "svg": '<ellipse cx="29" cy="51" rx="15" ry="5.5" fill="#FFD43B" stroke="#E0A800" stroke-width="1"/>'
            '<ellipse cx="29" cy="50" rx="9" ry="2.6" fill="rgba(0,0,0,0.08)"/>'
            '<circle cx="14.5" cy="47" r="3.6" fill="#FFD43B" stroke="#E0A800" stroke-width="0.8"/>'
            '<path d="M11.3 47 L8.5 48 L11.3 48.8 Z" fill="#F08A24"/><circle cx="13.6" cy="46.2" r="0.8" fill="#222"/>'},
    {"id": "tuxedo", "name": "畢業典禮西裝", "slot": "body", "price": 350, "rarity": "傳說", "ncu": False, "desc": "人生重要的一天",
     "svg": '<path d="M17 41 Q17 32 29 32 Q41 32 41 41 L41 51 Q29 56 17 51 Z" fill="#20232A"/>'
            '<path d="M24 32.5 L28 44 L32 32.5 Z" fill="#FFFFFF"/><path d="M26 34 L28 36 L30 34 L28 37.5 Z" fill="#C0392B"/>'},

    # ───────────── 手持（會取代原本抱著的松果） ─────────────
    {"id": "bubble_tea", "name": "珍珠奶茶", "slot": "hand", "price": 40, "rarity": "普通", "ncu": False, "desc": "宵夜街必買",
     "svg": '<path d="M14.5 36 L23.5 36 L22.3 48 L15.7 48 Z" fill="#E9D3B0" stroke="#B89B6E" stroke-width="0.8"/>'
            '<circle cx="17.5" cy="46" r="1" fill="#3A2418"/><circle cx="20" cy="46.2" r="1" fill="#3A2418"/><circle cx="18.8" cy="44.3" r="1" fill="#3A2418"/>'
            '<path d="M21 36 L23.5 30" stroke="#FF6FA0" stroke-width="1.6"/>'},
    {"id": "book", "name": "原文書", "slot": "hand", "price": 35, "rarity": "普通", "ncu": False, "desc": "期中考前抱緊",
     "svg": '<rect x="12.5" y="37" width="12" height="10" rx="1" fill="#2E5EAA"/><rect x="13.5" y="38" width="10" height="1.5" fill="#FFD54A"/>'
            '<path d="M12.5 46 L24.5 46" stroke="#FFF" stroke-width="1"/>'},
    {"id": "coffee", "name": "咖啡", "slot": "hand", "price": 35, "rarity": "普通", "ncu": False, "desc": "早八救星",
     "svg": '<rect x="14" y="38" width="9" height="10" rx="1.5" fill="#FFFFFF" stroke="#999" stroke-width="0.8"/>'
            '<rect x="14" y="41" width="9" height="4" fill="#8B5A2B"/><path d="M17 36 Q16 34 17.5 32.5 M20 36 Q19 34 20.5 32.5" stroke="#BBB" fill="none" stroke-width="0.9"/>'},
    {"id": "ice_cream", "name": "冰淇淋", "slot": "hand", "price": 45, "rarity": "普通", "ncu": False, "desc": "夏天限定的快樂",
     "svg": '<path d="M15 41 L22 41 L18.5 50 Z" fill="#E0A85A"/><circle cx="18.5" cy="38.5" r="4" fill="#FFB3C7"/><circle cx="17" cy="37" r="1" fill="#FFF"/>'},
    {"id": "umbrella", "name": "小紅傘", "slot": "hand", "price": 55, "rarity": "普通", "ncu": False, "desc": "中壢下雨天的好朋友",
     "svg": '<path d="M1 21 Q10 9 19 21 Z" fill="#E0524C"/><path d="M5.5 21 Q10 15 14.5 21" fill="none" stroke="#B83A35" stroke-width="0.8"/>'
            '<path d="M10 21 L18 42" stroke="#555" stroke-width="1.2"/>'},
    {"id": "ncu_flag", "name": "NCU 加油小旗", "slot": "hand", "price": 90, "rarity": "稀有", "ncu": True, "desc": "🎓 中大系列：系際盃加油用",
     "svg": '<path d="M18 46 L9.5 3" stroke="#7A5230" stroke-width="1.3"/><path d="M9.5 3 L0.5 4.5 L0.5 11 L10.8 9.6 Z" fill="#2F7A5B"/>'
            '<text x="1.3" y="9.2" font-size="3.6" font-weight="bold" fill="#FFF" font-family="Arial">NCU</text>'},
    {"id": "gold_pinecone", "name": "金松果", "slot": "hand", "price": 300, "rarity": "傳說", "ncu": False, "desc": "閃閃發亮的傳說松果",
     "svg": '<ellipse cx="19" cy="42" rx="4.5" ry="5.5" fill="#F5C518" stroke="#C9970C" stroke-width="0.8"/>'
            '<path d="M15 40 L23 40 M15 43 L23 43 M16 46 L22 46" stroke="#C9970C" stroke-width="0.9"/>'
            '<path d="M11 35 L12 37 L14 38 L12 39 L11 41 L10 39 L8 38 L10 37 Z" fill="#FFF3A6"/>'},

    # ───────────── 背部 ─────────────
    {"id": "backpack", "name": "綠色背包", "slot": "back", "price": 50, "rarity": "普通", "ncu": False, "desc": "裝滿講義",
     "svg": '<rect x="37" y="34" width="11" height="15" rx="4" fill="#2F7A5B"/><path d="M38 38 Q34 40 34 46" stroke="#1F5A41" stroke-width="1.6" fill="none"/>'},
    {"id": "balloon", "name": "紅氣球", "slot": "back", "price": 40, "rarity": "普通", "ncu": False, "desc": "生日快樂",
     "svg": '<path d="M38 38 Q46 24 52 12" stroke="#777" stroke-width="0.8" fill="none"/><ellipse cx="53" cy="8" rx="5" ry="6" fill="#E0524C"/>'
            '<circle cx="51.5" cy="6" r="1.3" fill="#FFF" opacity="0.7"/>'},
    {"id": "guitar", "name": "吉他", "slot": "back", "price": 110, "rarity": "稀有", "ncu": False, "front": True, "desc": "社團成發主角",
     "svg": '<path d="M38 44 L55 17" stroke="#5E3A17" stroke-width="2.6"/><rect x="52.5" y="13" width="5" height="5" rx="1" fill="#3A2418"/>'
            '<ellipse cx="35" cy="50" rx="7.5" ry="6" fill="#C87533" stroke="#8E4E1E" stroke-width="0.8"/>'
            '<ellipse cx="39" cy="44" rx="5.5" ry="4.5" fill="#C87533" stroke="#8E4E1E" stroke-width="0.8"/>'
            '<circle cx="37" cy="47.5" r="2" fill="#3A2418"/>'},
    {"id": "cape", "name": "英雄披風", "slot": "back", "price": 140, "rarity": "稀有", "ncu": False, "desc": "幫助同學的超級英雄",
     "svg": '<path d="M18 34 Q29 30 40 34 L46 58 Q29 63 12 58 Z" fill="#C0392B"/>'},
    {"id": "ncu_tote", "name": "NCU 帆布袋", "slot": "back", "price": 110, "rarity": "稀有", "ncu": True, "front": True, "desc": "🎓 中大系列：米白帆布袋",
     "svg": '<path d="M30 33 Q38 34 40 42" fill="none" stroke="#2F7A5B" stroke-width="1.6"/>'
            '<rect x="33" y="41" width="14" height="13" rx="1.5" fill="#F3EBDD" stroke="#C9B48A" stroke-width="0.8"/>'
            '<text x="34.3" y="49.5" font-size="4.6" font-weight="bold" fill="#2F7A5B" font-family="Arial">NCU</text>'},
    {"id": "wings", "name": "天使翅膀", "slot": "back", "price": 400, "rarity": "傳說", "ncu": False, "desc": "幫助過很多人的證明",
     "svg": '<path d="M37 37 Q48 20 58 26 Q52 29 55 33 Q48 33 50 38 Q44 37 44 43 Q39 42 37 37 Z" fill="#FFFFFF" stroke="#D8D8D8" stroke-width="1"/>'
            '<path d="M43 33 Q49 28 54 29" fill="none" stroke="#E4E4E4" stroke-width="1"/>'},
]


def get_item(item_id):
    """用 id 找衣服，找不到回傳 None"""
    for item in ITEMS:
        if item["id"] == item_id:
            return item
    return None


def get_fur(fur_id):
    """用名稱找毛色，找不到回傳第一個（栗棕）"""
    for fur in FURS:
        if fur["id"] == fur_id:
            return fur
    return FURS[0]


def items_by_slot(slot):
    """列出某個部位的所有衣服"""
    result = []
    for item in ITEMS:
        if item["slot"] == slot:
            result.append(item)
    return result


def ncu_items():
    """列出中大系列"""
    result = []
    for item in ITEMS:
        if item["ncu"]:
            result.append(item)
    return result


def starter_items():
    """新手免費的衣服 id"""
    result = []
    for item in ITEMS:
        if item["price"] == 0:
            result.append(item["id"])
    return result


# 舊版只有一個「配件」欄位，這裡把舊名稱對應到新的衣服 id（讓舊資料還能用）
LEGACY_ACCESSORY = {"學士帽": "grad_cap", "圍巾": "scarf_red", "眼鏡": "glasses", "耳機": "headphones",
                    "小花": "flower", "背包": "backpack"}
