from gui.stock_detail import BaseDetailView
from core.config import is_etf_stock


class EtfDetailView(BaseDetailView):
    def __init__(self, parent, app):
        super().__init__(parent, app, "ETF 管理", filter_etf=True)

    def _get_visible_codes(self):
        return [c for c in self._stock_codes if is_etf_stock(c)]
