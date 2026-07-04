import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from core.models import Transaction, StockState
from core.config import is_etf_stock
from core.portfolio import Portfolio


class TransactionDialog(tk.Toplevel):
    def __init__(self, parent, portfolio, stock_code, action, cfg):
        super().__init__(parent)
        self.portfolio = portfolio
        self.stock_code = stock_code
        self.action = action
        self.cfg = cfg
        self.result = False

        action_labels = {
            "buy": "買入", "sell": "賣出", "dividend": "現金股利",
            "stock_dividend": "股票股利", "dividend_reinvest": "再投資",
        }
        self.title(f"{action_labels.get(action, action)} - {stock_code}")
        self.geometry("400x300")
        self.resizable(False, False)

        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        state = self.portfolio.get_state(stock_code)

        today = date.today().isoformat()
        rows = []

        if action in ("buy",):
            rows = [("date", "日期", today), ("price", "價格"), ("shares", "股數"), ("fee", "手續費", "0")]
        elif action == "sell":
            rows = [("date", "日期", today), ("price", "價格"), ("shares", "股數"), ("fee", "手續費", "0"), ("tax", "交易稅", "0")]
        elif action == "dividend":
            rows = [("date", "日期", today), ("total", "股利總額")]
        elif action == "dividend_reinvest":
            rows = [("date", "日期", today), ("price", "價格"), ("shares", "股數")]
        elif action == "stock_dividend":
            rows = [("date", "日期", today), ("shares", "增加股數")]

        self._entries = {}
        for i, row in enumerate(rows):
            key, label = row[0], row[1]
            default = row[2] if len(row) > 2 else ""
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky="e", padx=5, pady=4)
            e = ttk.Entry(frame, width=25)
            e.grid(row=i, column=1, sticky="w", padx=5, pady=4)
            e.insert(0, default)
            self._entries[key] = e

        if action in ("buy", "sell") and state:
            info = f"目前持有 {state.shares} 股，均價 {state.avg_cost:.2f}"
            ttk.Label(frame, text=info, font=("", 9)).grid(row=len(rows), column=0, columnspan=2, pady=5)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=len(rows) + (1 if action in ("buy", "sell") and state else 0) + 1,
                       column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="確定", command=self.on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.LEFT, padx=5)

        self.grab_set()

    def on_ok(self):
        try:
            date_str = self._entries["date"].get() or date.today().isoformat()
            action = self.action
            fee = float(self._entries["fee"].get() or "0") if "fee" in self._entries else 0.0
            tax = float(self._entries["tax"].get() or "0") if "tax" in self._entries else 0.0

            if action == "buy":
                price = float(self._entries["price"].get())
                shares = int(self._entries["shares"].get())
                total = round(price * shares, 2)
                txn = Transaction(date=date_str, action="buy", price=price, shares=shares,
                                  total_amount=total, fee=fee, tax=0.0)
            elif action == "sell":
                price = float(self._entries["price"].get())
                shares = int(self._entries["shares"].get())
                total = round(price * shares, 2)
                txn = Transaction(date=date_str, action="sell", price=price, shares=shares,
                                  total_amount=total, fee=fee, tax=tax)
            elif action == "dividend":
                ttl = float(self._entries["total"].get())
                txn = Transaction(date=date_str, action="dividend", price=0.0, shares=0,
                                  total_amount=ttl, dividend_total=ttl, fee=0.0, tax=0.0)
            elif action == "dividend_reinvest":
                price = float(self._entries["price"].get())
                shares = int(self._entries["shares"].get())
                total = round(price * shares, 2)
                txn = Transaction(date=date_str, action="dividend_reinvest", price=price, shares=shares,
                                  total_amount=total, fee=0.0, tax=0.0)
            elif action == "stock_dividend":
                shares = int(self._entries["shares"].get())
                txn = Transaction(date=date_str, action="stock_dividend", price=0.0, shares=shares,
                                  total_amount=0.0, fee=0.0, tax=0.0)
            else:
                return

            self.portfolio.add_transaction(self.stock_code, txn, self.cfg)
            self.result = True
            self.destroy()
        except ValueError:
            messagebox.showerror("錯誤", "請輸入有效的數值")


class HoldingDialog(tk.Toplevel):
    def __init__(self, parent, portfolio, cfg):
        super().__init__(parent)
        self.portfolio = portfolio
        self.cfg = cfg
        self.result = None

        self.title("新增初始持倉")
        self.geometry("350x250")
        self.resizable(False, False)

        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="股票代碼").grid(row=0, column=0, sticky="e", padx=5, pady=4)
        self.entry_code = ttk.Entry(frame, width=25)
        self.entry_code.grid(row=0, column=1, sticky="w", padx=5, pady=4)

        ttk.Label(frame, text="股數").grid(row=1, column=0, sticky="e", padx=5, pady=4)
        self.entry_shares = ttk.Entry(frame, width=25)
        self.entry_shares.grid(row=1, column=1, sticky="w", padx=5, pady=4)

        ttk.Label(frame, text="總成本 (含手續費)").grid(row=2, column=0, sticky="e", padx=5, pady=4)
        self.entry_cost = ttk.Entry(frame, width=25)
        self.entry_cost.grid(row=2, column=1, sticky="w", padx=5, pady=4)

        ttk.Label(frame, text="日期").grid(row=3, column=0, sticky="e", padx=5, pady=4)
        self.entry_date = ttk.Entry(frame, width=25)
        self.entry_date.grid(row=3, column=1, sticky="w", padx=5, pady=4)
        self.entry_date.insert(0, date.today().isoformat())

        ttk.Label(frame, text="附註").grid(row=4, column=0, sticky="e", padx=5, pady=4)
        self.entry_note = ttk.Entry(frame, width=25)
        self.entry_note.grid(row=4, column=1, sticky="w", padx=5, pady=4)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="確定", command=self.on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.LEFT, padx=5)

        self.grab_set()

    def on_ok(self):
        try:
            code = self.entry_code.get().strip()
            if not code:
                raise ValueError("請輸入股票代碼")
            shares = int(self.entry_shares.get())
            total_cost = float(self.entry_cost.get())
            date_str = self.entry_date.get().strip()
            note = self.entry_note.get().strip()

            if shares <= 0:
                raise ValueError("股數必須大於 0")
            if total_cost <= 0:
                raise ValueError("總成本必須大於 0")

            self.portfolio.add_init_holding(code, shares, total_cost, self.cfg, date_str=date_str if date_str else None)
            self.result = code
            self.destroy()
        except (ValueError, KeyError) as e:
            messagebox.showerror("錯誤", str(e))
