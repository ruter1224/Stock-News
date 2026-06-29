import tkinter as tk
from tkinter import ttk
from core.config import is_etf_stock
from core.report import generate_report


class DashboardView(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        ttk.Label(self, text="持有總覽", font=("", 14, "bold")).pack(anchor="w", padx=15, pady=(10, 5))

        card_frame = ttk.Frame(self)
        card_frame.pack(fill=tk.X, padx=15, pady=5)

        self.lbl_count = self._card(card_frame, 0, "持股檔數")
        self.lbl_value = self._card(card_frame, 1, "總市值")
        self.lbl_pl = self._card(card_frame, 2, "總損益")
        self.lbl_roi = self._card(card_frame, 3, "總報酬率")

        for i in range(4):
            card_frame.columnconfigure(i, weight=1)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=15, pady=5)
        ttk.Button(btn_frame, text="重新整理股價", command=app.refresh_prices).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="新增個股/ETF", command=app.show_holding_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="匯入 CSV", command=app.import_csv).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="匯出報表", command=app.export_report).pack(side=tk.LEFT, padx=2)

        stats_frame = ttk.Frame(self)
        stats_frame.pack(fill=tk.X, padx=15, pady=5)

        zc_frame = ttk.LabelFrame(stats_frame, text="零成本統計", padding=8)
        zc_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.lbl_zc = ttk.Label(zc_frame, text="")
        self.lbl_zc.pack()

        cols = ("代碼", "類型", "股數", "均價", "現價", "市值", "未實現損益", "報酬率", "零成本")
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=20)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=90, anchor="e" if c not in ("代碼", "類型", "零成本") else "w")
        self.tree.column("代碼", width=70)
        self.tree.column("類型", width=55)
        self.tree.column("零成本", width=70)

        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _card(self, parent, col, label):
        f = ttk.Frame(parent, relief="groove", borderwidth=1)
        f.grid(row=0, column=col, padx=3, pady=2, sticky="nsew")
        ttk.Label(f, text=label, font=("", 9)).pack(pady=(5, 0))
        lbl = ttk.Label(f, text="", font=("", 18, "bold"))
        lbl.pack(pady=(0, 5))
        return lbl

    def refresh(self, portfolio, prices=None):
        for row in self.tree.get_children():
            self.tree.delete(row)

        if not portfolio.stock_codes:
            self.lbl_count.configure(text="0")
            self.lbl_value.configure(text="$0")
            self.lbl_pl.configure(text="$0")
            self.lbl_roi.configure(text="0%")
            self.lbl_zc.configure(text="尚無持股")
            return

        if prices is None:
            prices = {}

        codes = sorted(portfolio.stock_codes)
        total_value = 0.0
        total_cost = 0.0
        zc_count = 0

        for code in codes:
            state = portfolio.get_state(code)
            price = prices.get(code)
            rep = generate_report(state, current_price=price)

            total_cost += rep.total_invested
            val = (price or 0) * state.shares if price else rep.current_value
            total_value += val

            if state.is_zero_cost:
                zc_count += 1

            stype = "ETF" if is_etf_stock(code) else "個股"
            self.tree.insert("", tk.END, values=(
                code,
                stype,
                f"{state.shares:,}",
                f"{state.avg_cost:,.2f}",
                f"{price:,.2f}" if price else "N/A",
                f"{val:,.0f}",
                f"{rep.total_pl:+,.0f}",
                f"{rep.total_roi_pct:+.2f}%",
                "O" if state.is_zero_cost else "X",
            ))

        total_pl = total_value - total_cost
        roi = (total_pl / total_cost * 100) if total_cost > 0 else 0.0
        color = "#16a34a" if total_pl >= 0 else "#dc2626"

        self.lbl_count.configure(text=str(len(codes)))
        self.lbl_value.configure(text=f"${total_value:,.0f}")
        self.lbl_pl.configure(text=f"${total_pl:+,.0f}", foreground=color)
        self.lbl_roi.configure(text=f"{roi:+.2f}%", foreground=color)
        self.lbl_zc.configure(text=f"已達成零成本：{zc_count} 檔   未達成：{len(codes)-zc_count} 檔")
