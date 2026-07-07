# Changelog

## v2.0 - 2026-07-07

### Breaking
- **移除 Tkinter GUI 子命令**: `main.py` 不再提供 `gui` 指令，請改用 `web` 指令啟動 Web GUI
- **Android 路線封存**: Android APK 相關工作暫停，`docs/android-todo.md` 標記為已封存

### New Features
- **新聞功能 (Phase 1)**: Yahoo Finance RSS 新聞抓取，中文新聞優先排序、分頁顯示、20 分鐘冷卻 (`core/news.py`)
- **資金池功能**: 自動推算現金餘額、入金/出金記錄、成長率計算、定期快照 (`core/fund_pool.py`)
- **資金池儀表板摘要**: 總覽頁面顯示資金池摘要卡片 + 迷你成長率圖表
- **CSV 匯出優化**: 瀏覽器下載模式、日期格式檔名、支援資金池同步匯出
- **CSV 匯入強化**: 支援股利/再投資/初始持倉辨識、狀態欄位導入、重複提交過濾
- **自動封存**: 完全賣出的股票自動移至「已封存」分頁
- **資料遷移**: 新增 `status` 欄位支援匯出/匯入封存狀態
- **OTC 上櫃股票**: 中文名稱正確解析、孤兒資料清理

### UI Improvements
- **總覽頁面重新設計**: 簡化卡片佈局，移除重複資訊
- **字體加大**: 提升可讀性
- **連線狀態指示器**: 顯示與 Yahoo Finance 的連線狀態
- **資金池標籤**: 統一命名為「資金池」
- **錯誤畫面**: WebView 錯誤時顯示錯誤訊息與重試按鈕

### Bug Fixes
- **CSV roundtrip**: 非 init 開頭的股票匯出再匯入不再報錯 (`data/importer.py`)
- **重複提交**: 防止同一交易重複送出 (`web/api.py`)
- **None 報酬率處理**: 完全賣出時 `unrealized_pl_pct` 為 None 不再 crash
- **基金測試修正**: `test_dividend_reinvest` 補上 `dividend()` 呼叫

### Chores
- **PyInstaller**: 加入 `core.news` 至 hidden imports
- **launcher 穩定**: `DATA_DIR` 路徑修正 (`launcher.py`)
- **Legacy GUI 紀錄**: 萃取 Tkinter 對話框模式至 `docs/legacy-gui-patterns.md`
- **資金池計畫結案**: `docs/fund-pool/plan.md` 狀態更新為已完成
- **Android 封存**: `docs/android-todo.md` 標記為已封存

### Full Changelog
- `core/news.py`: 新增 — Yahoo Finance RSS 新聞模組
- `core/fund_pool.py`: 新增 — 資金池資料模型與自動推算
- `core/prices.py`: OTC 中文名稱查詢、快取初始化修正
- `data/importer.py`: 支援股利/再投資/初始 CSV 解析、狀態欄位
- `data/store.py`: 資金池持久化
- `web/api.py`: 新聞、資金池、CSV 匯入/匯出強化、重複提交過濾
- `web/app.py`: 保留
- `web/static/app.js`: 資金池 UI、新聞 UI、總覽重新設計、連線狀態
- `web/static/style.css`: 字體加大、佈局調整
- `web/templates/dashboard.html`: 總覽簡化、資金池摘要
- `web/templates/news.html`: 新增 — 新聞頁面
- `web/templates/fund_pool.html`: 新增 — 資金池頁面
- `web/templates/base.html`: 導航加入新聞/資金池分頁
- `main.py`: 移除 `gui` 子命令
- `launcher.py`: DATA_DIR 路徑修正
- `StockTracker.spec`: 加入 `core.news` hidden import
- `gui/`: 保留原始碼（不再使用）
- `docs/legacy-gui-patterns.md`: 新增 — Tkinter 對話框模式參考
- `docs/android-todo.md`: 封存

---

## v1.2 - 2026-07-01

### Bug Fixes
- **CSV 匯出/匯入 Roundtrip 修復**: 先匯出再匯入同一檔案不再出現「賣出股數不可大於持有股數」錯誤
- **重複匯入不再累積**: 同一 CSV 多次匯入不會累積重複的 init 記錄 (`data/importer.py`)
- **init_holding 保留歷史記錄**: 恢復保留所有 init 記錄，確保匯出/匯入 roundtrip 時間順序正確 (`core/calculator.py`)

### Improvements
- **Flask 伺服器可直接啟動**: `web/app.py` 加入 sys.path 設定，支援 `python web/app.py` 直接執行
- **state.json 自動清空**: 匯入 CSV 前先清空有 init 記錄的股票狀態，防止重複累積

### Full Changelog
- `core/calculator.py`: init_holding() 移除記錄剝離邏輯，保持所有歷史記錄
- `data/importer.py`: parse_trades_csv() 匯入前先清空有 init 的股票
- `web/app.py`: 加入 sys.path 修正，支援直接執行
