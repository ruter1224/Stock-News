import tkinter as tk
from tkinter import ttk, messagebox
from core.config import is_etf_stock


class SettingsView(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        ttk.Label(self, text="系統設定", font=("", 14, "bold")).pack(anchor="w", padx=15, pady=(10, 5))

        form = ttk.Frame(self)
        form.pack(padx=30, pady=10, anchor="w")

        self._entries = {}
        fields = [
            ("fee_rate", "手續費率"),
            ("tax_rate_listed", "個股交易稅 (上市)"),
            ("tax_rate_otc", "個股交易稅 (上櫃)"),
            ("tax_rate_etf", "ETF 交易稅"),
        ]
        for i, (key, label) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky="e", padx=5, pady=4)
            e = ttk.Entry(form, width=20)
            e.grid(row=i, column=1, sticky="w", padx=5, pady=4)
            self._entries[key] = e

        btn_frame = ttk.Frame(self)
        btn_frame.pack(padx=30, pady=10, anchor="w")
        ttk.Button(btn_frame, text="儲存", command=self.on_save).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="恢復預設", command=self.on_reset).pack(side=tk.LEFT, padx=2)

        sep = ttk.Separator(self, orient="horizontal")
        sep.pack(fill=tk.X, padx=15, pady=15)

        self._config_frame = ttk.LabelFrame(self, text="股價快取管理", padding=10)
        self._config_frame.pack(fill=tk.X, padx=30, pady=5)
        self.lbl_cache = ttk.Label(self._config_frame, text="")
        self.lbl_cache.pack(anchor="w")
        ttk.Button(self._config_frame, text="清除快取", command=self.on_clear_cache).pack(anchor="w", pady=3)

        self._etf_frame = ttk.LabelFrame(self, text="ETF 自動偵測設定", padding=10)
        self._etf_frame.pack(fill=tk.X, padx=30, pady=5)
        self.lbl_etf = ttk.Label(self._etf_frame, text="", wraplength=500)
        self.lbl_etf.pack(anchor="w")

        self.load_config()

    def load_config(self):
        cfg = self.app.cfg
        self._entries["fee_rate"].delete(0, tk.END)
        self._entries["fee_rate"].insert(0, str(cfg.fee_rate))
        self._entries["tax_rate_listed"].delete(0, tk.END)
        self._entries["tax_rate_listed"].insert(0, str(cfg.tax_rate_listed))
        self._entries["tax_rate_otc"].delete(0, tk.END)
        self._entries["tax_rate_otc"].insert(0, str(cfg.tax_rate_otc))
        self._entries["tax_rate_etf"].delete(0, tk.END)
        self._entries["tax_rate_etf"].insert(0, str(cfg.tax_rate_etf))
        self.lbl_cache.configure(text=f"快取目錄：data/cache/")
        self.lbl_etf.configure(text="股票代碼符合 00xx 或 008xxx、006xxx 模式，或已知 ETF 列表時自動視為 ETF。"
                                "可在 core/config.py 的 KNOWN_ETFS 中新增。")

    def on_save(self):
        try:
            cfg = self.app.cfg
            cfg.fee_rate = float(self._entries["fee_rate"].get())
            cfg.tax_rate_listed = float(self._entries["tax_rate_listed"].get())
            cfg.tax_rate_otc = float(self._entries["tax_rate_otc"].get())
            cfg.tax_rate_etf = float(self._entries["tax_rate_etf"].get())
            messagebox.showinfo("完成", "設定已儲存")
        except ValueError:
            messagebox.showerror("錯誤", "請輸入有效的數值")

    def on_reset(self):
        self.app.cfg = type(self.app.cfg)()
        self.load_config()
        messagebox.showinfo("完成", "已恢復預設值")

    def on_clear_cache(self):
        try:
            from core.prices import clear_cache
            clear_cache()
            messagebox.showinfo("完成", "股價快取已清除")
        except Exception as e:
            messagebox.showerror("錯誤", str(e))
