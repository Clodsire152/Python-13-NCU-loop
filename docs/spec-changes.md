# 程式與 spec.md 的差異（請同步更新 spec 第 4、5、7、8、10 章）

spec 第 10 章規定「函式名稱、參數、回傳值不得私自更動，要改先改文件並通知全組」。
這一版依助教回饋做了下面這些改動，**請組長確認後把 spec 一起改掉**。

## 1. 依助教回饋做的改動

| 助教意見 | 程式裡的改法 | 檔案 |
|---|---|---|
| 範圍過大 | P0 只做 M1、CH、M2、AI-1～AI-7 的規則版；M3 精簡版；**M4 討論區與照片不做** | 全部 |
| AI 份量不足、配對只靠規則 | 新增 `rerank_matches`：AI 在規則候選中重新排序＋寫理由，id 不在候選中就整份作廢 | ai_helper.py |
| 配對規則沒定義 | 檔案開頭寫了評分表與門檻（≥4），並附手算案例（10 分）與測試 | lostfound.py |
| `mark_resolved` 與 `set_item_status` 重疊 | 只保留 `mark_resolved`，沒有 `set_item_status` | lostfound.py |
| 密碼未加鹽、4 碼太短 | PBKDF2-SHA256 加鹽，至少 6 碼；users.json 多一個 `salt` 欄位 | auth.py |
| 沒有檢舉、封鎖 | 新增最小版檢舉（`reports.json`）與封鎖（`blocks.json`） | chat.py |
| 私訊要注意沙盒、詐騙 | 每個討論串一個檔；新增 `detect_scam_risk` 送出前提醒；訊息上限 300 字 | storage.py、ai_helper.py |
| 證件卡片冒領風險 | 刊登頁與卡片提示「同時交由校內既有失物招領管道」 | app.py |
| 並行寫入測試不穩 | 每個討論串一個檔＋寫入前重新讀＋暫存檔原子寫入；測試表請加註「Demo 採單人依序操作」 | storage.py |

## 2. 函式介面的差異（spec 第 10 章）

| 函式 | spec 寫的 | 程式實際 |
|---|---|---|
| `hash_password` | `(password)` | `(password, salt)`，另有 `make_salt()` |
| `register_user` | 密碼 ≥ 4 碼 | 密碼 ≥ 6 碼；暱稱「系統」保留 |
| `find_matches` | `(item, items)` | `(item, items, limit=3)`，每筆多一個 `detail`（計分明細） |
| `list_events` | `(events, category, keyword, only_upcoming)` | 多一個選填 `now=""`（方便測試） |
| 私訊存放 | `data/chats.json` 一個檔 | `data/chats/thread_編號.json` 每串一個檔；用 `load_all_threads()`、`load_thread(id)`、`save_thread(thread)` |
| 新增 | — | `ai_helper.rerank_matches(item, candidates)` → `{"data": [{"item", "score", "detail", "reason"}], "source"}` |
| 新增 | — | `ai_helper.detect_scam_risk(text)` → list[str] |
| 新增 | — | `ai_helper.is_ai_enabled()`、`ask_json()` |
| 新增 | — | `chat.create_report`、`chat.block_user`、`chat.is_blocked`、`chat.other_person` |
| `make_match_reason` | 有 | 保留；畫面實際用 `rerank_matches`（裡面已含理由） |
| 討論區 `forum.py` | P1 | **這版不做**（依助教建議砍範圍） |

## 3. spec 其他要修的地方（助教指出）

- 章節交叉引用全文重新檢查（第 14、15 章、13.1 自查表、10.9 等不存在）。
- 第 2 章補上「問題與觀察」：訪談 5 位同學的原話，以及「群組貼文／校內既有失物招領／其他校園 App／本專案」比較表。
- 9.2 的測量表補上「對不公開聯絡方式的接受度」問卷；簡報用實測數字，未測的標「預期」。

## 4. v2：松鼠地圖與松果（新增功能，請補進 spec 第 4、8、9、10 章）

| 項目 | 內容 |
|---|---|
| 新頁面 | 🗺️ 松鼠地圖、🐿️ 我的松鼠；首頁改版（數字看板、今日探索、最新動態、線上松鼠） |
| 新檔案 | `campus_map.py`、`squirrel.py`、`map_component.py`、`components/squirrel_map/index.html`、`.streamlit/config.toml` |
| 新資料 | `data/profiles.json`（造型、位置、足跡、隱身、上榜）、`data/pinecones.json`（松果紀錄，`ref` 去重複） |
| 新函式 | `campus_map.location_to_zone / build_zone_infos / build_map_args / search_zones / items_in_zone`；`squirrel.move_to / explore_reward / add_pinecones / get_badges / leaderboard / squirrel_svg`；`lostfound.mark_returned`；`chat.confirm_received / peers_of_target` |
| 例外 | 地圖元件是 JavaScript（不在 spec 第 7 章的語法限制內），請在 spec 註明「互動地圖元件例外」，並由負責人 `/explain` 看懂 |
| 獎勵防弊 | 松果一律由「受幫助的一方」觸發；探索松果每天上限 5 顆 |
| 隱私 | 松鼠位置是虛擬的網站瀏覽位置，非 GPS；可隱身、可不上榜 |

## 5. v3：任務系統與商店

| 項目 | 內容 |
|---|---|
| 新頁面 | 🎯 松果任務、🛍️ 松果商店；「我的松鼠」改成衣櫃；每日簽到彈窗 |
| 新檔案 | `wardrobe.py`（衣服資料與 SVG）、`quests.py`（簽到、金松果、每日／每週任務、徽章獎勵）、`shop.py`（購買、穿脫、特價） |
| 資料格式變更 | `profiles.json`：`accessory` 改成 `outfit`（5 個部位）＋`owned`、`owned_furs`、`checkin`、`daily`、`weekly`、`badge_claimed`；舊資料由 `squirrel.normalize_profile` 自動轉換 |
| 松果帳本 | 購買記成負數；`total_pinecones`＝目前持有，`earned_pinecones`＝累計賺到（排行榜、徽章用） |
| 防灌分 | 刊登不給松果；大額獎勵由被幫助者確認；每個任務限領一次；探索、簽到加成有上限 |
| 智慧財產 | 中大系列為原創設計，不使用官方校徽 |
