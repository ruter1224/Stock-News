import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from core.config import Config
from core.prices import init_cache as init_price_cache, fetch_prices, clear_cache as clear_price_cache
from data.store import save_portfolio, load_portfolio
from gui.dashboard import DashboardView
from gui.stock_detail import StockDetailView
from gui.etf_detail import EtfDetailView
from gui.settings import SettingsView

DATA_DIR = Path(__file__).parent.parent / "data"
STATE_FILE = str(DATA_DIR / "state.json")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Stock Tracker - 股票成本計算系統")
        self.geometry("1200x750")
        self.minsize(900, 600)

        self.portfolio = load_portfolio(STATE_FILE)
        self.cfg = Config()

        self._build_menu()
        self._build_ui()
        self.refresh_all()

    def _build_menu(self):
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="匯入 CSV", command=self.import_csv)
        file_menu.add_command(label="匯出報表", command=self.export_report)
        file_menu.add_separator()
        file_menu.add_command(label="離開", command=self.quit)
        menubar.add_cascade(label="檔案", menu=file_menu)

        op_menu = tk.Menu(menubar, tearoff=0)
        op_menu.add_command(label="重新整理股價", command=self.refresh_prices)
        op_menu.add_command(label="設定初始持倉", command=self.show_holding_dialog)
        menubar.add_cascade(label="操作", menu=op_menu)

        self.configure(menu=menubar)

    def _build_ui(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.dashboard = DashboardView(self.notebook, self)
        self.stock_view = StockDetailView(self.notebook, self)
        self.etf_view = EtfDetailView(self.notebook, self)
        self.settings = SettingsView(self.notebook, self)

        self.notebook.add(self.dashboard, text="  持有總覽  ")
        self.notebook.add(self.stock_view, text="  個股管理  ")
        self.notebook.add(self.etf_view, text="  ETF管理  ")
        self.notebook.add(self.settings, text="  設定  ")

    def refresh_all(self):
        self.dashboard.refresh(self.portfolio)
        self.stock_view.refresh_stock_list(self.portfolio)
        self.etf_view.refresh_stock_list(self.portfolio)

    def refresh_prices(self):
        codes = self.portfolio.stock_codes
        if not codes:
            messagebox.showinfo("提示", "投資組合為空")
            return
        init_price_cache(str(DATA_DIR))
        clear_price_cache()
        prices = fetch_prices(codes)
        ok = sum(1 for v in prices.values() if v is not None)
        messagebox.showinfo("完成", f"成功更新 {ok}/{len(codes)} 檔股價")
        self.dashboard.refresh(self.portfolio, prices)

    def save(self):
        save_portfolio(self.portfolio, STATE_FILE)

    def import_csv(self):
        from tkinter import filedialog
        f = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not f:
            return
        try:
            from data.importer import parse_trades_csv
            self.portfolio, n, _ = parse_trades_csv(f, self.portfolio, self.cfg)
            self.save()
            messagebox.showinfo("完成", f"已匯入 {n} 筆交易")
            self.refresh_all()
        except Exception as e:
            messagebox.showerror("錯誤", str(e))

    def export_report(self):
        from tkinter import filedialog
        from core.report import generate_report, export_report_csv, export_report_html

        is_html = messagebox.askyesno("匯出格式", "匯出為 HTML 報表？\n(否=CSV)")
        ext = ".html" if is_html else ".csv"
        f = filedialog.asksaveasfilename(defaultextension=ext,
                                         filetypes=[("HTML files", "*.html"), ("CSV files", "*.csv")])
        if not f:
            return
        try:
            for code in self.portfolio.stock_codes:
                state = self.portfolio.get_state(code)
                rep = generate_report(state)
                if is_html:
                    export_report_html(rep, state, f)
                else:
                    export_report_csv(rep, state, f)
            messagebox.showinfo("完成", f"已匯出報表至 {f}")
        except Exception as e:
            messagebox.showerror("錯誤", str(e))

    def show_holding_dialog(self):
        from gui.dialogs import HoldingDialog
        d = HoldingDialog(self, self.portfolio, self.cfg)
        self.wait_window(d)
        if d.result:
            self.save()
            self.refresh_all()
            messagebox.showinfo("完成", f"已設定 {d.result} 的初始持倉")
