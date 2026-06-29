import json
from data.store import save_portfolio, load_portfolio
from core.portfolio import Portfolio
from core.models import StockState
from tests.fixtures import make_buy, make_config


class TestStore:
    def test_save_load_empty(self, tmp_path):
        p = Portfolio()
        fp = tmp_path / "state.json"
        save_portfolio(p, fp)
        loaded = load_portfolio(fp)
        assert loaded.stock_codes == []

    def test_save_load_with_stocks(self, tmp_path):
        p = Portfolio()
        cfg = make_config(fee_rate=0, tax_rate=0)
        tx = make_buy("2024-01-01", 100, 1000)
        p.add_transaction("2330", tx, cfg)

        fp = tmp_path / "state.json"
        save_portfolio(p, fp)
        loaded = load_portfolio(fp)
        assert "2330" in loaded.stock_codes
        assert loaded.get_state("2330").shares == 1000

    def test_backward_compat_old_format(self, tmp_path):
        fp = tmp_path / "state.json"
        old_data = {
            "shares": 500,
            "total_cost": 50000.0,
            "avg_cost": 100.0,
            "is_zero_cost": False,
            "history": [
                {
                    "date": "2024-01-01",
                    "action": "buy",
                    "price": 100.0,
                    "shares": 500,
                    "fee": 0.0,
                    "tax": 0.0,
                    "total_amount": 50000.0,
                    "zero_cost_triggered": False,
                    "dividend_per_share": 0.0,
                    "dividend_total": 0.0,
                    "per_thousand_shares": 0,
                    "additional_shares": 0,
                }
            ],
        }
        fp.write_text(json.dumps(old_data, ensure_ascii=False), encoding="utf-8")
        portfolio = load_portfolio(fp)
        assert "0000" in portfolio.stock_codes
        st = portfolio.get_state("0000")
        assert st.shares == 500
        assert st.total_cost == 50000.0
        assert len(st.history) == 1
