# Legacy GUI Patterns (Tkinter) — 參考用

> **來源**: `stock-tracker/gui/` (已保留，不再開發)
> **用途**: 未來專案開發對話框/表單時可參考的設計模式
> **日期**: 2026-07-07

---

## 1. Modal Dialog 模式

交易對話框 (`gui/dialogs.py:TransactionDialog`) 是標準表單對話框的範例：

```python
class TransactionDialog(tk.Toplevel):
    def __init__(self, parent, portfolio, stock_code, action, cfg):
        super().__init__(parent)
        self.result = False                     # 儲存結果供呼叫者讀取
        self.title(f"{label} - {stock_code}")
        self.geometry("400x300")
        self.resizable(False, False)

        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        # 根據 action 類型動態產生表單欄位
        rows = [...]  # (key, label, default)
        self._entries = {}
        for i, row in enumerate(rows):
            key, label = row[0], row[1]
            default = row[2] if len(row) > 2 else ""
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky="e", padx=5, pady=4)
            e = ttk.Entry(frame, width=25)
            e.grid(row=i, column=1, sticky="w", padx=5, pady=4)
            e.insert(0, default)
            self._entries[key] = e

        # 確認/取消按鈕
        ttk.Button(frame, text="確定", command=self.on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame, text="取消", command=self.destroy).pack(side=tk.LEFT, padx=5)

        self.grab_set()  # 模態鎖定

    def on_ok(self):
        try:
            # 取值 + 校驗
            # 呼叫 business logic
            # self.result = True / self.destroy()
        except ValueError:
            messagebox.showerror("錯誤", "請輸入有效的數值")
```

**模式要點**:
- `tk.Toplevel` + `grab_set()` 實現模態對話框
- `self.result` 讓 `wait_window()` 後可取回結果
- `grid()` 佈局：左標籤右輸入
- 統一錯誤處理用 `try/except ValueError` + `messagebox`

---

## 2. 呼叫端模式 (`gui/stock_detail.py`)

```python
def on_buy(self):
    code = self._get_code()
    if not code: return
    from gui.dialogs import TransactionDialog
    d = TransactionDialog(self, self.app.portfolio, code, "buy", self.app.cfg)
    self.wait_window(d)       # 等待對話框關閉
    if d.result:
        self.app.save()       # 持久化
        self.app.refresh_all()  # 刷新 UI
```

**模式要點**: `wait_window()` + 檢查 `result` + `save()` + `refresh()`

---

## 3. View 模式 (BaseDetailView)

```python
class BaseDetailView(ttk.Frame):
    def __init__(self, parent, app, title, filter_etf=None):
        super().__init__(parent)
        self.app = app                    # 持有 App 引用
        self.current_code = None

        # 頂部：標題 + 下拉選單
        ttk.Label(header, text=title, font=("", 14, "bold"))

        # 卡片區：6 格關鍵指標
        for i in range(6):
            card_frame.columnconfigure(i, weight=1)

        # 操作按鈕列
        ttk.Button(...)

        # 歷史紀錄表格 (Treeview)
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
        scroll = ttk.Scrollbar(...)
```

**模式要點**:
- `ttk.Frame` 作為基礎 class
- 持有 `app` 引用取用 portfolio/save/refresh
- `BaseDetailView` 加上 `filter_etf` 參數控制個股/ETF 分頁（透過 `_get_visible_codes()`）
- `refresh_stock_list()` → `on_select()` → `_show_detail()` 三階段更新流程

---

## 4. Dashboard 模式 (`gui/dashboard.py`)

```python
class DashboardView(ttk.Frame):
    def refresh(self, portfolio, prices=None):
        # 1. 清空表格
        # 2. 走訪 portfolio.stock_codes
        # 3. 用 generate_report() + prices 計算
        # 4. 更新卡片 + Treeview
```

**模式要點**: 批量走訪 + 報表產生 + 顏色標記（紅漲綠跌）

---

## 5. App 主控器模式 (`gui/app.py`)

```python
class App(tk.Tk):
    def __init__(self):
        self.portfolio = load_portfolio(STATE_FILE)
        self.cfg = Config()
        self._build_menu()
        self._build_ui()  # Notebook + Views

    def save(self):
        save_portfolio(self.portfolio, STATE_FILE)

    def refresh_all(self):
        self.dashboard.refresh(self.portfolio)
        self.stock_view.refresh_stock_list(self.portfolio)
```

**模式要點**:
- App 即 `tk.Tk`，作為中央控制器
- `portfolio` 作為 shared state（類似 Redux store 概念）
- `save()` + `refresh_all()` 為統一的持久化/刷新接口
- `Notebook` 實現 Tab 切換

---

> 此檔案為 `stock-tracker/gui/` 的設計萃取，保留作為未來桌面應用開發的參考。
