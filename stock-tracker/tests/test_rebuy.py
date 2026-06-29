import pytest
from core.calculator import buy
from tests.fixtures import make_buy, make_sell, make_state, make_config


class TestRebuy:
    def test_rebuy_after_zero_cost(self):
        cfg = make_config(fee_rate=0, tax_rate=0)
        state = make_state(500, 0, is_zero_cost=True)

        tx = make_buy("2024-03-01", 200, 500)
        new_state = buy(state, tx, cfg)

        assert new_state.shares == 1000
        assert new_state.total_cost == 100000
        assert new_state.avg_cost == 100

    def test_rebuy_with_fee(self):
        cfg = make_config(fee_rate=0.001425, tax_rate=0)
        state = make_state(500, 0, is_zero_cost=True)

        fee = round(200 * 500 * 0.001425, 2)
        tx = make_buy("2024-03-01", 200, 500, fee=fee)
        new_state = buy(state, tx, cfg)

        assert new_state.shares == 1000
        expected_cost = 100000 + fee
        assert new_state.total_cost == pytest.approx(expected_cost, rel=1e-4)
        assert new_state.avg_cost == pytest.approx(expected_cost / 1000, rel=1e-4)
