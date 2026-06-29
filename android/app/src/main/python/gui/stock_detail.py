import tkinter as tk
from tkinter import ttk, messagebox
from core.config import is_etf_stock
from core.report import generate_report


class BaseDetailView(ttk.Frame):
    def __init__(self, parent, app, title, filter_etf=None):
        super().__init__(parent)
        self.app = app
        self.filter_etf = filter_etf
        self._stock_codes = []
        self.current_code = None

        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=15, pady=(10, 5))
        ttk.Label(header, text=title, font=("", 14, "bold")).pack(side=tk.LEFT)

        self.combo = ttk.Combobox(header, state="readonly", width=30, font=("", 11))
        self.combo.pack(side=tk.RIGHT, padx=(0, 5))
        self.combo.bind("<<ComboboxSelected>>", self.on_select)

        card_frame = ttk.Frame(self)
        card_frame.pack(fill=tk.X, padx=15, pady=5)
        self.lbl_shares = self._card(card_frame, 0, "股數")
        self.lbl_cost = self._card(card_frame, 1, "總成本")
        self.lbl_avg = self._card(card_frame, 2, "均價")
        self.lbl_price = self._card(card_frame, 3, "現價")
        self.lbl_mv = self._card(card_frame, 4, "市值")
        self.lbl_pl = self._card(card_frame, 5, "未實現損益")
        for i in range(6):
            card_frame.columnconfigure(i, weight=1)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=15, pady=5)

        self._add_action_button(btn_frame, "買入", self.on_buy)
        self._add_action_button(btn_frame, "賣出", self.on_sell)
        self._add_action_button(btn_frame, "現金股利", self.on_dividend)
        self._add_action_button(btn_frame, "股票股利", self.on_stock_dividend)
        self._add_action_button(btn_frame, "再投資", self.on_reinvest)
        self._add_action_button(btn_frame, "刪除此檔", self.on_remove)

        cols = ("日期", "類型", "價格", "股數", "金額", "手續費", "稅")
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=12)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=100, anchor="e" if c in ("價格", "股數", "金額", "手續費", "稅") else "w")
        self.tree.column("日期", width=100)
        self.tree.column("類型", width=100)
        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _card(self, parent, col, label):
        f = ttk.Frame(parent, relief="groove", borderwidth=1)
        f.grid(row=0, column=col, padx=2, pady=2, sticky="nsew")
        ttk.Label(f, text=label, font=("", 8)).pack(pady=(3, 0))
        lbl = ttk.Label(f, text="", font=("", 13, "bold"))
        lbl.pack(pady=(0, 3))
        return lbl

    def _add_action_button(self, parent, text, cmd):
        ttk.Button(parent, text=text, command=cmd).pack(side=tk.LEFT, padx=2)

    def refresh_stock_list(self, portfolio):
        self.combo.set("")
        self.combo["values"] = []
        self._stock_codes = sorted(portfolio.stock_codes)
        self.combo["values"] = self._get_visible_codes()
        if self.combo["values"]:
            self.combo.current(0)
            self.current_code = self.combo["values"][0]
            self._show_detail(portfolio)
        else:
            self.current_code = None

    def _get_visible_codes(self):
        if self.filter_etf is True:
            return [c for c in self._stock_codes if is_etf_stock(c)]
        elif self.filter_etf is False:
            return [c for c in self._stock_codes if not is_etf_stock(c)]
        return list(self._stock_codes)

    def _lookup_name(self, code):
        return code

    def on_select(self, event=None):
        sel = self.combo.get()
        if sel:
            self.current_code = sel.split()[0]
            self._show_detail(self.app.portfolio)

    def _show_detail(self, portfolio):
        code = self.current_code
        if not code:
            for w in (self.lbl_shares, self.lbl_cost, self.lbl_avg, self.lbl_price, self.lbl_mv, self.lbl_pl):
                w.configure(text="")
            for r in self.tree.get_children():
                self.tree.delete(r)
            return

        state = portfolio.get_state(code)
        rep = generate_report(state)

        self.lbl_shares.configure(text=f"{state.shares:,}")
        self.lbl_cost.configure(text=f"{state.total_cost:,.0f}")
        self.lbl_avg.configure(text=f"{state.avg_cost:,.2f}")
        self.lbl_price.configure(text=f"{rep.current_price:,.2f}" if rep.current_price is not None else "N/A")
        self.lbl_mv.configure(text=f"{rep.current_value:,.0f}")
        color = "#16a34a" if rep.total_pl >= 0 else "#dc2626"
        self.lbl_pl.configure(text=f"{rep.total_pl:+,.0f}", foreground=color)

        for r in self.tree.get_children():
            self.tree.delete(r)
        for txn in state.history:
            self.tree.insert("", tk.END, values=(
                txn.date,
                self._txn_label(txn.action),
                f"{txn.price:,.2f}",
                f"{txn.shares:,}",
                f"{txn.total_amount:,.0f}",
                f"{txn.fee:,.0f}" if txn.fee else "-",
                f"{txn.tax:,.0f}" if txn.tax else "-",
            ))

    @staticmethod
    def _txn_label(action):
        labels = {"buy": "買入", "sell": "賣出", "dividend": "股利",
                  "dividend_reinvest": "再投資", "stock_dividend": "股票股利",
                  "init": "初始"}
        return labels.get(action, action)

    def _get_code(self):
        sel = self.combo.get()
        if not sel:
            messagebox.showwarning("提示", "請先選擇股票")
            return None
        code = sel.split()[0]
        state = self.app.portfolio.get_state(code)
        if not state:
            messagebox.showerror("錯誤", f"找不到 {code}")
            return None
        return code

    def on_buy(self):
        code = self._get_code()
        if not code:
            return
        from gui.dialogs import TransactionDialog
        d = TransactionDialog(self, self.app.portfolio, code, "buy", self.app.cfg)
        self.wait_window(d)
        if d.result:
            self.app.save()
            self.app.refresh_all()
            self._show_detail(self.app.portfolio)

    def on_sell(self):
        code = self._get_code()
        if not code:
            return
        from gui.dialogs import TransactionDialog
        d = TransactionDialog(self, self.app.portfolio, code, "sell", self.app.cfg)
        self.wait_window(d)
        if d.result:
            self.app.save()
            self.app.refresh_all()
            self._show_detail(self.app.portfolio)

    def on_dividend(self):
        code = self._get_code()
        if not code:
            return
        from gui.dialogs import TransactionDialog
        d = TransactionDialog(self, self.app.portfolio, code, "dividend", self.app.cfg)
        self.wait_window(d)
        if d.result:
            self.app.save()
            self.app.refresh_all()
            self._show_detail(self.app.portfolio)

    def on_stock_dividend(self):
        code = self._get_code()
        if not code:
            return
        from gui.dialogs import TransactionDialog
        d = TransactionDialog(self, self.app.portfolio, code, "stock_dividend", self.app.cfg)
        self.wait_window(d)
        if d.result:
            self.app.save()
            self.app.refresh_all()
            self._show_detail(self.app.portfolio)

    def on_reinvest(self):
        code = self._get_code()
        if not code:
            return
        from gui.dialogs import TransactionDialog
        d = TransactionDialog(self, self.app.portfolio, code, "dividend_reinvest", self.app.cfg)
        self.wait_window(d)
        if d.result:
            self.app.save()
            self.app.refresh_all()
            self._show_detail(self.app.portfolio)

    def on_remove(self):
        code = self._get_code()
        if not code:
            return
        ok = messagebox.askyesno("確認", f"確定刪除 {code} 的所有資料？\n此動作無法復原。", icon="warning")
        if not ok:
            return
        self.app.portfolio.remove_stock(code)
        self.app.save()
        self.app.refresh_all()


class StockDetailView(BaseDetailView):
    def __init__(self, parent, app):
        super().__init__(parent, app, "個股管理", filter_etf=False)

    def _get_visible_codes(self):
        return [c for c in self._stock_codes if not is_etf_stock(c)]
