from pathlib import Path
from core.report import generate_report, export_report_csv, export_report_html
from core.calculator import buy, sell
from tests.fixtures import make_buy, make_sell, make_state, make_config


class TestReportExport:
    def setup_state(self):
        cfg = make_config(fee_rate=0, tax_rate=0)
        state = make_state(0, 0)
        tx1 = make_buy("2024-01-01", 100, 1000)
        state = buy(state, tx1, cfg)
        tx2 = make_sell("2024-02-01", 150, 500)
        state = sell(state, tx2, cfg)
        return state

    def test_export_csv(self, tmp_path):
        state = self.setup_state()
        rep = generate_report(state)
        out = tmp_path / "report.csv"
        export_report_csv(rep, state, str(out))

        content = out.read_text(encoding="utf-8-sig")
        assert "總投入成本" in content
        assert "持有股數" in content
        assert "買入" in content or "buy" in content
        assert "賣出" in content or "sell" in content
        assert "100000" in content

    def test_export_html(self, tmp_path):
        state = self.setup_state()
        rep = generate_report(state)
        out = tmp_path / "report.html"
        export_report_html(rep, state, str(out))

        content = out.read_text(encoding="utf-8")
        assert "<html" in content
        assert "股票損益報表" in content
        assert "庫存概況" in content
        assert "損益總覽" in content
        assert "交易明細" in content
        assert "100,000" in content

    def test_export_csv_with_current_price(self, tmp_path):
        state = self.setup_state()
        rep = generate_report(state, current_price=200)
        out = tmp_path / "report.csv"
        export_report_csv(rep, state, str(out))
        content = out.read_text(encoding="utf-8-sig")
        assert "目前市價" in content
        assert "未實現損益" in content

    def test_export_html_with_current_price(self, tmp_path):
        state = self.setup_state()
        rep = generate_report(state, current_price=200)
        out = tmp_path / "report.html"
        export_report_html(rep, state, str(out))
        content = out.read_text(encoding="utf-8")
        assert "200" in content
