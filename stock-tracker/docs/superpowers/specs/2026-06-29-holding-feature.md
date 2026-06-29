# 持倉初始化功能設計

## 目的

讓使用者可以直接輸入目前各股票的持有股數與總成本，跳過逐筆輸入歷史交易，便能開始使用庫存管理與報表功能。

## 功能

### `holding add`

```
python main.py holding add --stock 2330 --shares 2000 --cost 500000
```

- 為指定股票建立初始持倉狀態
- 內部建立一筆 `init` 類型的 `Transaction`，記錄於 history
- 自動計算平均成本：`avg_cost = cost / shares`
- 若已存在該股票的狀態，則拒絕執行（需先 remove 再 add）

### `holding list`

顯示所有以 `init` 方式設定的持倉股票狀態（同現有 `list` 功能格式）。

### `holding remove`

```
python main.py holding remove --stock 2330
```

- 刪除指定股票的持倉狀態
- 需要確認參數 `--confirm`

## 實作細節

### core/models.py

- `Transaction` 新增 action 類型 `"init"`
- 不需要新的欄位，使用現有 shares / total_amount / price

### core/calculator.py

- 新增 `init_holding()` handler
- 直接設定 shares 與 total_cost，無手續費/稅
- avg_cost = total_cost / shares
- price = avg_cost, 記錄於 Transaction

### core/report.py

- `generate_report()` 的 `total_invested` 計算加入 `"init"` 動作（與 buy/dividend_reinvest 同等對待）

### core/portfolio.py

- `add_init_holding(stock_code, shares, total_cost, config)` 方法
- 檢查該股票是否已有狀態，若有則拋錯

### main.py

- 新增 `holding` 子命令（使用 `holding.add_parser` subparser group）
- 支援 `holding add`, `holding list`, `holding remove`

### 測試

- `test_holding.py`: 測試 init 狀態建立、平均成本計算、覆蓋拒絕、remove 等

## 與現有功能相容性

- 初始化後可用 `add buy/sell` 繼續正常交易
- `status`、`report`、`export`、`refresh` 等命令完全相容
- `init` 交易類型會在 export 中正確顯示
