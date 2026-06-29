from core.calculator import dividend
from core.models import Transaction
from tests.fixtures import make_state, make_config


def make_cash_dividend(date: str, per_share: float, shares: int):
    return Transaction(
        date=date,
        action="dividend",
        price=0,
        shares=0,
        dividend_per_share=per_share,
        dividend_total=round(per_share * shares, 2),
    )


class TestDividendCash:
    def test_cash_dividend_no_impact(self):
        cfg = make_config()
        state = make_state(1000, 100000)
        tx = make_cash_dividend("2024-07-01", 5.5, 1000)

        new_state = dividend(state, tx, cfg)

        assert new_state.shares == 1000
        assert new_state.total_cost == 100000
        assert new_state.avg_cost == 100

    def test_cash_dividend_appends_history(self):
        cfg = make_config()
        state = make_state(1000, 100000)
        tx = make_cash_dividend("2024-07-01", 5.5, 1000)

        new_state = dividend(state, tx, cfg)

        assert len(new_state.history) == 1
        assert new_state.history[0].action == "dividend"
        assert new_state.history[0].dividend_total == 5500

    def test_cash_dividend_zero_cost(self):
        cfg = make_config()
        state = make_state(500, 0, is_zero_cost=True)
        tx = make_cash_dividend("2024-08-01", 3.0, 500)

        new_state = dividend(state, tx, cfg)

        assert new_state.is_zero_cost
        assert new_state.total_cost == 0
