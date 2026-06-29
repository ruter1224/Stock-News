import pytest
from core.calculator import stock_dividend
from tests.fixtures import (
    make_buy, make_sell, make_stock_dividend, make_state, make_config,
)


class TestStockDividend:
    def test_basic_stock_dividend(self):
        cfg = make_config(fee_rate=0, tax_rate=0)
        state = make_state(1000, 100000)

        tx = make_stock_dividend("2024-07-01", per_thousand=50, additional=50)
        new_state = stock_dividend(state, tx, cfg)

        assert new_state.shares == 1050
        assert new_state.total_cost == 100000
        assert new_state.avg_cost == pytest.approx(100000 / 1050, rel=1e-4)

    def test_stock_dividend_after_zero_cost(self):
        cfg = make_config(fee_rate=0, tax_rate=0)
        state = make_state(500, 0, is_zero_cost=True)

        tx = make_stock_dividend("2024-08-01", per_thousand=100, additional=50)
        new_state = stock_dividend(state, tx, cfg)

        assert new_state.shares == 550
        assert new_state.total_cost == 0
        assert new_state.avg_cost == 0
        assert new_state.is_zero_cost
