# Plan: Tkinter → Flask + HTML GUI 改造

> **狀態**: ✅ 已完成 (Web GUI 已取代 Tkinter)
> **更新 (2026-07-07)**: `gui/` 目錄保留原始碼，`main.py` 已移除 `gui` 子命令
> 設計模式萃取 → `../../docs/legacy-gui-patterns.md`

## 當前狀態（2026-06-29）

### 專案架構
```
stock-tracker/
├── main.py              # CLI + Tkinter GUI 入口
├── requirements.txt     # pytest>=7.0.0
├── core/                # 商業邏輯（不變）
│   ├── models.py        # Transaction, StockState
│   ├── config.py        # Config, is_etf_stock
│   ├── calculator.py    # buy/sell/dividend...
│   ├── portfolio.py     # Portfolio CRUD
│   ├── prices.py        # Yahoo Finance API
│   └── report.py        # 報表產生
├── data/                # 持久層（不變）
│   ├── store.py         # JSON save/load
│   ├── importer.py      # CSV import/export
│   ├── state.json       # 持倉資料
│   └── price_cache.json # 股價快取
├── gui/                 # Tkinter GUI（保留，未來由 web 取代）
│   ├── app.py           # App(tk.Tk) 主視窗
│   ├── dashboard.py     # 持有總覽 Tab
│   ├── stock_detail.py  # 個股管理 Tab
│   ├── etf_detail.py    # ETF 管理 Tab
│   ├── settings.py      # 設定 Tab
│   └── dialogs.py       # 交易/持倉對話框
│   └── sidebar.py       # (未使用)
└── tests/               # 測試（不變）
```

### 已知 Bug
- `gui/dialogs.py:167`：`add_init_holding()` 引數順序錯誤，`date_str` 與 `config` 對調，且傳入不存在的 `note` 參數

### 設計稿參考
- `.superpowers/brainstorm/gui2-20260629-080321/content/gui-tab-design.html`
- 配色：藍主色 #2563eb, 成功 #16a34a, 危險 #dc2626, 警告 #d97706, 紫色 #7c3aed
- 卡片：圓角 8px, 背景 #f8fafc, 邊框 #e5e7eb
- 類型標籤：個股藍底 #dbeafe/#2563eb, ETF 橘底 #fef3c7/#d97706

## 改造範圍

### 新增檔案
```
web/
├── __init__.py
├── app.py               # Flask 應用工廠
├── api.py               # REST API routes
├── templates/
│   ├── base.html        # 主版型（側邊 Tab 導航）
│   ├── dashboard.html   # 持有總覽
│   ├── stock_detail.html # 個股管理
│   ├── etf_detail.html  # ETF 管理
│   └── settings.html    # 設定
└── static/
    ├── style.css        # 完整 CSS 樣式（對齊設計稿）
    └── app.js           # 前端互動邏輯（API 呼叫、DOM 操作）
```

### 修改檔案
- `requirements.txt` → 追加 `flask`
- `main.py` → `gui` 指令改為啟動 Flask + 開瀏覽器

### 狀態管理策略（方案一）
- Flask global variable `portfolio` (process lifetime)
- 每次 API 操作後自動 `save_portfolio()` 寫入 `state.json`
- 重啟 Flask 時從 `state.json` 載入

## API 設計
```
GET    /api/portfolio              # 所有持股摘要
GET    /api/portfolio/<code>       # 單股詳細 + 交易歷史
POST   /api/holdings               # 新增初始持倉
POST   /api/transactions           # 買/賣/股利/再投資
DELETE /api/portfolio/<code>       # 刪除持股
POST   /api/prices/refresh         # 重新抓取股價
GET    /api/config                 # 讀取設定
PUT    /api/config                 # 更新設定
POST   /api/cache/clear            # 清除股價快取
```

## 實作順序
1. 安裝 Flask
2. web/api.py — REST API endpoints (wrap core logic)
3. web/static/style.css — 完整樣式表
4. web/templates/base.html — 骨架
5. web/templates/dashboard.html
6. web/static/app.js — 前端邏輯
7. web/templates/stock_detail.html + etf_detail.html
8. web/templates/settings.html
9. web/app.py — Flask server
10. main.py — gui 指令改造
11. 修正 dialogs.py bug
