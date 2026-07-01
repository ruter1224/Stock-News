# Changelog

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
