from core.report import generate_report
from core.calculator import buy, sell, dividend_reinvest, stock_dividend, dividend
from tests.fixtures import make_buy, make_sell, make_state, make_config
from tests.test_dividend_cash import make_cash_dividend


class TestReportBasic:
    def test_empty_state(self):
        state = make_state(0, 0)
        rep = generate_report(state)
        assert rep.shares == 0
        assert rep.total_invested == 0
        assert rep.total_roi_pct == 0

    def test_simple_buy(self):
        cfg = make_config(fee_rate=0, tax_rate=0)
        state = make_state(0, 0)
        tx = make_buy("2024-01-01", 100, 1000)
        state = buy(state, tx, cfg)

        rep = generate_report(state)
        assert rep.total_invested == 100000
        assert rep.total_recovered == 0
        # 沒賣出過，已實現損益 = 0
        assert rep.realized_pl == 0

    def test_simple_buy_sell(self):
        cfg = make_config(fee_rate=0, tax_rate=0)
        state = make_state(0, 0)

        tx1 = make_buy("2024-01-01", 100, 1000)
        state = buy(state, tx1, cfg)
        tx2 = make_sell("2024-02-01", 150, 1000)
        state = sell(state, tx2, cfg)

        rep = generate_report(state)
        assert rep.total_invested == 100000
        assert rep.total_recovered == 150000
        # realized_pl = total_recovered + remaining_cost - total_invested
        # remaining_cost = 0 (zero-cost triggered since 150000 >= 100000)
        assert rep.realized_pl == 50000
        assert rep.total_roi_pct == 50.0

    def test_sell_with_loss(self):
        cfg = make_config(fee_rate=0, tax_rate=0)
        state = make_state(0, 0)

        tx1 = make_buy("2024-01-01", 100, 1000)
        state = buy(state, tx1, cfg)
        tx2 = make_sell("2024-02-01", 80, 500)
        state = sell(state, tx2, cfg)

        rep = generate_report(state)
        # net=40000, cost_before=100000, loss rolled in
        # remaining_cost = 60000
        # realized_pl = 40000 + 60000 - 100000 = 0
        assert rep.realized_pl == 0
        assert rep.total_invested == 100000
        assert rep.total_recovered == 40000

    def test_with_current_price(self):
        cfg = make_config(fee_rate=0, tax_rate=0)
        state = make_state(0, 0)

        tx1 = make_buy("2024-01-01", 100, 1000)
        state = buy(state, tx1, cfg)

        rep = generate_report(state, current_price=120)
        assert rep.current_price == 120
        assert rep.current_value == 120000
        assert rep.unrealized_pl == 20000
        assert rep.unrealized_pl_pct == 20.0
        # realized=0 (沒賣出), unrealized=20000
        assert rep.total_pl == 20000

    def test_with_current_price_zero_cost(self):
        cfg = make_config(fee_rate=0, tax_rate=0)
        state = make_state(0, 0)

        tx1 = make_buy("2024-01-01", 100, 1000)
        state = buy(state, tx1, cfg)
        tx2 = make_sell("2024-02-01", 250, 500)
        state = sell(state, tx2, cfg)

        rep = generate_report(state, current_price=200)
        assert rep.is_zero_cost
        assert rep.current_value == 100000
        assert rep.unrealized_pl == 100000  # 100000 - 0
        assert rep.unrealized_pl_pct is None  # can't divide by zero
        assert rep.total_pl == 125000  # 25000 realized + 100000 unrealized
        assert rep.total_roi_pct == 125.0

    def test_dividend_income_in_report(self):
        cfg = make_config(fee_rate=0, tax_rate=0)
        state = make_state(0, 0)

        tx1 = make_buy("2024-01-01", 100, 1000)
        state = buy(state, tx1, cfg)
        tx2 = make_cash_dividend("2024-07-01", 5.5, 1000)
        state = dividend(state, tx2, cfg)

        rep = generate_report(state)
        assert rep.total_dividend_income == 5500
        assert rep.total_invested == 100000
