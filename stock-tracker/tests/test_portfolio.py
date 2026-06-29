from core.portfolio import Portfolio
from core.calculator import buy, sell
from tests.fixtures import make_buy, make_sell, make_state, make_config


class TestPortfolio:
    def test_empty_portfolio(self):
        p = Portfolio()
        assert p.stock_codes == []
        st = p.get_state("2330")
        assert st.shares == 0

    def test_add_stock_transaction(self):
        p = Portfolio()
        cfg = make_config(fee_rate=0, tax_rate=0)
        tx = make_buy("2024-01-01", 100, 1000)

        st = p.add_transaction("2330", tx, cfg)
        assert st.shares == 1000
        assert p.stock_codes == ["2330"]

    def test_multiple_stocks(self):
        p = Portfolio()
        cfg = make_config(fee_rate=0, tax_rate=0)

        tx1 = make_buy("2024-01-01", 100, 1000)
        p.add_transaction("2330", tx1, cfg)

        tx2 = make_buy("2024-02-01", 50, 2000)
        p.add_transaction("2317", tx2, cfg)

        codes = sorted(p.stock_codes)
        assert codes == ["2317", "2330"]
        assert p.get_state("2330").shares == 1000
        assert p.get_state("2317").shares == 2000

    def test_stocks_are_independent(self):
        p = Portfolio()
        cfg = make_config(fee_rate=0, tax_rate=0)

        tx1 = make_buy("2024-01-01", 100, 1000)
        p.add_transaction("2330", tx1, cfg)
        tx2 = make_sell("2024-02-01", 250, 500)
        p.add_transaction("2330", tx2, cfg)

        tx3 = make_buy("2024-03-01", 50, 2000)
        p.add_transaction("2317", tx3, cfg)

        assert p.get_state("2330").is_zero_cost
        assert not p.get_state("2317").is_zero_cost

    def test_remove_stock(self):
        p = Portfolio()
        cfg = make_config()
        tx = make_buy("2024-01-01", 100, 1000)
        p.add_transaction("2330", tx, cfg)
        assert "2330" in p.stock_codes

        p.remove_stock("2330")
        assert "2330" not in p.stock_codes

    def test_to_dict_roundtrip(self):
        p = Portfolio()
        cfg = make_config(fee_rate=0, tax_rate=0)

        tx1 = make_buy("2024-01-01", 100, 1000)
        p.add_transaction("2330", tx1, cfg)
        tx2 = make_buy("2024-02-01", 50, 2000)
        p.add_transaction("2317", tx2, cfg)

        data = p.to_dict()
        p2 = Portfolio.from_dict(data)

        assert sorted(p2.stock_codes) == ["2317", "2330"]
        assert p2.get_state("2330").shares == 1000
        assert p2.get_state("2317").shares == 2000
        assert len(p2.get_state("2330").history) == 1
