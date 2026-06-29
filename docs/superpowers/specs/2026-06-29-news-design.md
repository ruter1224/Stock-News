# Stock-News 新聞功能設計規格書

> 建立日期：2026-06-29
> 狀態：已批准待實作
> 版本：v1.0

---

## 一、概述

在現有的 Stock Tracker 系統中加入新聞功能，讓使用者可以在同一平台查看財經新聞與個股新聞。

### 專案名稱由來

專案名稱即為 **Stock-News**（股票交易帳本-新聞系統），新聞功能一直是核心目標之一。

### 開發階段

| 階段 | 功能 | 狀態 |
|------|------|------|
| **Phase 1** | 每日財經頭條 | 🔜 本次實作 |
| **Phase 2** | 個股新聞查詢 | ⏳ 後續 |
| **Phase 3** | 推播通知 | ⏳ 未來 |

---

## 二、需求規格

### 功能範圍（Phase 1）

1. 在 Web GUI 中新增第 6 個分頁「📰 新聞」
2. 顯示每日財經頭條新聞（從多個市場主要標的彙整）
3. 每頁顯示 20 則新聞，支援後端分頁
4. 手動重新整理按鈕，20 分鐘冷卻限制
5. 點擊新聞標題直接開啟外部連結（Yahoo Finance 原始來源）
6. 新聞資料快取 30 分鐘 TTL

### 使用者操作流程

```
使用者切換到「📰 新聞」分頁
  → GET /api/news?page=1 載入第一頁
  → 瀏覽新聞列表
  → 點擊分頁按鈕切頁（GET /api/news?page=2）
  → 點擊「🔄 重新整理」按鈕
     ├── 冷卻中 → 按鈕 disabled，顯示剩餘冷卻時間
     └── 可更新 → POST /api/news/refresh → 載入最新新聞
  → 點擊新聞標題 → 開啟外部瀏覽器連結
```

---

## 三、架構設計

### 模組架構

```
stock-tracker/
├── core/
│   └── news.py              ← 新增：新聞抓取、快取、分頁
├── web/
│   ├── api.py                ← 新增 API 路由
│   ├── templates/
│   │   └── base.html         ← 加入第 6 個 Tab
│   └── static/
│       └── app.js            ← 新聞分頁 UI 邏輯
└── data/
    └── news_cache.json       ← 新聞快取檔案
```

### 資料流

```
使用者操作 → app.js → REST API → core/news.py → Yahoo Finance API
                                    ↓
                              news_cache.json (快取)
```

### 資料來源策略

| 項目 | 內容 |
|------|------|
| 主要來源 | Yahoo Finance v1 API (`query1.finance.yahoo.com/v1/finance/news`) |
| 備援方案 | RSS Feed（Yahoo Finance RSS） |
| API Key | 不需要（與現有股價 API 同一來源） |
| 頭條策略 | 查詢多個台灣主要標的（^TWII, 2330, 2317 等）彙整為頭條 |

### API 設計

| 方法 | 路徑 | 參數 | 說明 |
|------|------|------|------|
| `GET` | `/api/news` | `page`(default=1), `per_page`(default=20) | 取得新聞列表（含分頁資訊） |
| `POST` | `/api/news/refresh` | - | 強制重新整理新聞（檢查 20 分鐘冷卻） |

#### GET /api/news 回應格式

```json
{
  "articles": [
    {
      "title": "台積電法說會釋放正面訊號...",
      "summary": "台積電今日召開法說會，第三季展望優於預期...",
      "url": "https://finance.yahoo.com/news/...",
      "source": "Yahoo Finance",
      "published": "2026-06-29T10:00:00Z",
      "related_stocks": ["2330"]
    }
  ],
  "total": 85,
  "page": 1,
  "per_page": 20,
  "total_pages": 5,
  "last_refresh_at": "2026-06-29T10:30:00Z",
  "cooldown_remaining": 0
}
```

#### POST /api/news/refresh 冷卻回應

```json
// 429 Too Early
{
  "error": "冷卻中，請於 12 分鐘後再試",
  "cooldown_remaining": 723
}
```

---

## 四、核心模組設計

### `core/news.py`

| 函數 | 功能 |
|------|------|
| `init_cache(cache_dir)` | 初始化快取目錄 |
| `fetch_market_news()` | 從 Yahoo Finance 抓取財經頭條 |
| `get_news_page(page, per_page)` | 取得分頁新聞（從快取或 Yahoo） |
| `refresh_news()` | 強制重新整理（檢查冷卻） |
| `_load_cache()` / `_save_cache()` | 快取讀寫 |
| `_is_cache_valid()` | 檢查快取是否過期（30分鐘） |
| `_is_cooldown()` | 檢查冷卻是否結束（20分鐘） |

### 快取格式

```json
{
  "articles": [
    {
      "title": "...",
      "summary": "...",
      "url": "...",
      "source": "Yahoo Finance",
      "published": "2026-06-29T10:00:00Z",
      "related_stocks": ["2330"]
    }
  ],
  "last_refresh_at": "2026-06-29T10:30:00Z",
  "cached_at": "2026-06-29T10:30:00Z"
}
```

---

## 五、前端設計

### 第 6 個分頁

在 `base.html` 的導覽列加入：

```
<button class="tab-btn" data-tab="news">
    <span class="icon">📰</span>新聞
</button>
```

### 新聞 Tab 版面

```
┌──────────────────────────────────────────────┐
│  📰 財經頭條                  [🔄 重新整理]     │
│  上次更新：2026-06-29 10:30                   │
├──────────────────────────────────────────────┤
│                                              │
│  📄 台積電法說會釋放正面訊號...     2026-06-29 │
│     台積電今日召開法說會，第三季展望優於預期...    │
│     📎 Yahoo Finance                          │
│  ───────────────────────────────────────────  │
│  📄 聯發科推出新旗艦晶片...         2026-06-29 │
│     聯發科宣布...                             │
│     📎 Yahoo Finance                          │
│  ───────────────────────────────────────────  │
│  ...（共 20 則）                              │
│                                              │
├──────────────────────────────────────────────┤
│  ← 上一頁     第 1 / 5 頁     下一頁 →        │
└──────────────────────────────────────────────┘
```

### 互動邏輯

- **分頁切換**：點擊「下一頁」/「上一頁」→ `GET /api/news?page=N` → 重新渲染列表
- **重新整理**：
  - 冷卻中：按鈕文字顯示「還剩 XX 分可更新」，disabled
  - 可更新：點擊 → `POST /api/news/refresh` → 更新列表
- **點擊新聞**：`window.open(article.url, '_blank')`

---

## 六、時間與快取策略

| 參數 | 值 | 說明 |
|------|-----|------|
| `CACHE_TTL` | 1800 秒 (30 分鐘) | 快取過期後自動重新抓取 |
| `REFRESH_COOLDOWN` | 1200 秒 (20 分鐘) | 手動重新整理的最小間隔 |
| `PER_PAGE` | 20 則 | 每頁顯示數量 |

### 行為組合

| 情境 | 行為 |
|------|------|
| 快取有效 + 進入分頁 | 直接回傳快取資料，不呼叫 Yahoo |
| 快取過期 + 進入分頁 | 自動重新抓取 Yahoo → 更新快取 → 回傳 |
| 手動整理 + 冷卻中 | 回傳 429，前端顯示冷卻時間 |
| 手動整理 + 可整理 | 強制抓取 Yahoo → 更新快取 → 回傳 |

---

## 七、階段計畫

### Phase 1：每日財經頭條（本次）

| 任務 | 檔案 |
|------|------|
| 建立 `core/news.py` | 新聞抓取 + 快取 + 分頁邏輯 |
| `api.py` 新增路由 | `GET /api/news`, `POST /api/news/refresh` |
| `base.html` 加入第 6 個 Tab | 導覽列 + 內容區塊 |
| `app.js` 新聞分頁邏輯 | 載入、分頁、重新整理、冷卻顯示 |

### Phase 2：個股新聞（後續）

- `GET /api/news/<code>` — 依股票代碼查詢新聞
- 在個股管理頁面加入新聞區塊

### Phase 3：推播（未來）

- WebSocket 或 Server-Sent Events
- 重要新聞即時通知
