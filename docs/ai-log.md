# AI 協作紀錄

> 競賽要求說明 AI 在開發過程中的角色。每次用 AI（聊天 AI、GitHub Copilot）都記一筆。
> 重點寫「人做了什麼判斷」：哪些建議採用、哪些刪掉、為什麼。

| 日期 | 工具 | 我問了什麼／請它做什麼 | AI 給了什麼 | 我們的判斷與修改 | 負責人 |
|---|---|---|---|---|---|
| 2026-11-22 | Claude | 依 spec.md 與助教回饋產生 MVP 程式骨架 | 9 個 .py 檔、測試、示範資料 | 待全組逐檔 `/explain` 審查；確認函式介面差異（見 docs/spec-changes.md） | |
| 2026-11-23 | Claude | 增加校園地圖、松鼠角色、互動性 | 松鼠地圖元件、松果／徽章、首頁改版 | 待審查：地圖座標需依實際校園調整；松果規則是否合理需全組討論 | |
| 2026-11-23 | Claude | 增加任務系統、簽到、商店與更多服裝（含中大系列） | quests.py、shop.py、wardrobe.py、兩個新頁面 | 待討論：獎勵數字是否平衡；中大系列是否要向學校申請使用校徽 | |
| | | | | | |

## 審查檢查表（每個檔案看完打勾）

- [ ] storage.py　- [ ] auth.py　- [ ] lostfound.py　- [ ] tasks.py　- [ ] events.py
- [ ] chat.py　- [ ] ai_helper.py　- [ ] app.py　- [ ] seed_data.py　- [ ] tests/test_core.py
- [ ] wardrobe.py　- [ ] quests.py　- [ ] shop.py
- [ ] campus_map.py　- [ ] squirrel.py　- [ ] map_component.py　- [ ] components/squirrel_map/index.html

看不懂的段落，請在 VS Code 選取後用 Copilot Chat 輸入 `/explain`，把重點寫在這裡。
