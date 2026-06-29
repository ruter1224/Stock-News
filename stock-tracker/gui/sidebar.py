import tkinter as tk
from tkinter import ttk
from core.config import is_etf_stock
from core.prices import fetch_price


class Sidebar(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, width=260)
        self.app = app
        self.pack_propagate(False)

        ttk.Label(self, text="庫存列表", font=("", 12, "bold")).pack(anchor="w", padx=8, pady=(8, 5))

        add_btn = tk.Button(self, text="+ 新增個股 / ETF", bg="#2563eb", fg="white",
                            font=("", 9), relief="flat", padx=10, pady=3,
                            command=app.show_holding_dialog)
        add_btn.pack(fill=tk.X, padx=8, pady=(0, 5))
        add_btn.bind("<Enter>", lambda e: add_btn.configure(bg="#1d4ed8"))
        add_btn.bind("<Leave>", lambda e: add_btn.configure(bg="#2563eb"))

        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *_: self._filter())
        search_entry = ttk.Entry(self, textvariable=self.search_var)
        search_entry.pack(fill=tk.X, padx=8, pady=(0, 5))
        search_entry.insert(0, "")
        search_entry.bind("<FocusIn>", lambda e: search_entry.selection_range(0, tk.END))

        self.listbox = tk.Listbox(self, font=("", 9), selectbackground="#dbeafe",
                                  selectforeground="black", borderwidth=1,
                                  relief="solid", activestyle="none",
                                  exportselection=False)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

    def refresh(self):
        self.listbox.delete(0, tk.END)
        codes = sorted(self.app.portfolio.stock_codes)
        search = self.search_var.get().strip().lower()
        for code in codes:
            if search and search not in code.lower():
                continue
            state = self.app.portfolio.get_state(code)
            price = fetch_price(code)
            stype = "ETF" if is_etf_stock(code) else "S"
            val = ""
            if price:
                total_val = price * state.shares
                cost = state.total_cost
                pl_pct = ((total_val - cost) / cost * 100) if cost > 0 else 0.0
                val = f"  {pl_pct:+.1f}%"
            zc = " ZC" if state.is_zero_cost else ""
            label = f"{code}  {stype}  {state.shares:,}{val}{zc}"
            self.listbox.insert(tk.END, label)

    def clear_selection(self):
        self.listbox.selection_clear(0, tk.END)

    def _filter(self):
        self.refresh()

    def _on_select(self, event):
        sel = self.listbox.curselection()
        if sel:
            text = self.listbox.get(sel[0])
            code = text.split()[0]
            self.app.show_stock_detail(code)
