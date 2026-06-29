import pytest
from core.calculator import buy, sell
from tests.fixtures import make_buy, make_sell, make_state, make_config


class TestZeroCostFullScenario:
    def test_full_scenario_from_spec(self):
        cfg = make_config(fee_rate=0, tax_rate=0)
        state = make_state(0, 0)

        tx1 = make_buy("2024-01-01", 100, 1000)
        state = buy(state, tx1, cfg)
        assert state.shares == 1000
        assert state.total_cost == 100000
        assert state.avg_cost == 100

        tx2 = make_sell("2024-02-01", 250, 500)
        state = sell(state, tx2, cfg)
        assert state.shares == 500
        assert state.total_cost == 0
        assert state.is_zero_cost
        assert state.avg_cost == 0
        assert tx2.zero_cost_triggered

        tx3 = make_buy("2024-03-01", 200, 500)
        state = buy(state, tx3, cfg)
        assert state.shares == 1000
        assert state.total_cost == 100000
        assert state.avg_cost == 100

    def test_multi_zero_cost(self):
        cfg = make_config(fee_rate=0, tax_rate=0)
        state = make_state(0, 0)

        tx1 = make_buy("2024-01-01", 100, 1000)
        state = buy(state, tx1, cfg)

        tx2 = make_sell("2024-02-01", 250, 500)
        state = sell(state, tx2, cfg)
        assert state.is_zero_cost

        tx3 = make_buy("2024-03-01", 200, 500)
        state = buy(state, tx3, cfg)
        assert not state.is_zero_cost

        tx4 = make_sell("2024-04-01", 300, 800)
        state = sell(state, tx4, cfg)
        assert state.shares == 200
        assert state.total_cost == 0
        assert state.is_zero_cost
        assert tx4.zero_cost_triggered
