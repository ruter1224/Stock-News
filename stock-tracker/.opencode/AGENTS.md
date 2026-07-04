# Stock-News 專案設定

## 專案簡介
台股交易帳本 — Flask Web 架構的股票交易記錄與管理系統。
整合新聞模組、CSV roundtrip、資金池管理。

## 技術棧
- Python 3.10+ / Flask 3.x
- 資料儲存：JSON file（data/state.json）
- 測試：pytest
- Lint：ruff

## 目錄結構
```
stock-tracker/
├── core/           # 業務邏輯
│   ├── models.py   # Transaction, StockState
│   ├── portfolio.py# Portfolio 管理
│   ├── calculator.py# 交易計算（buy/sell/dividend...）
│   ├── config.py   # 手續費/稅率設定
│   ├── prices.py   # 股價擷取
│   ├── report.py   # 報表產生
│   ├── news.py     # 新聞模組
│   ├── backtest.py # 回測
│   └── history.py  # 歷史股價
├── data/           # 持久層
│   ├── store.py    # JSON 儲存
│   └── importer.py # CSV 匯入/匯出
├── web/            # Flask Web 介面
│   ├── api.py      # REST API
│   ├── app.py      # Flask 工廠
│   ├── static/     # 前端資源
│   └── templates/  # HTML 模板
├── gui/            # Tkinter GUI（舊版）
├── tests/          # 測試
└── main.py         # CLI 進入點
```

## 分支策略
- `master` — 穩定主線
- `feature/news` — 新聞模組分支（已合併至 master）
- `feature/fund-pool` — 資金池功能開發中

## 常用指令
```powershell
# 啟動 Web
.\venv\Scripts\Activate.ps1
python main.py web

# 測試
pytest

# Lint
ruff check .
```

## 資金池功能規劃
- 資金池模型：獨立於個股交易帳本的資金管理
- 包含入金、出金、資金餘額、池報酬率計算
- Web UI 新增資金池頁面與 API
