import pytest
from core.calculator import buy, sell
from tests.fixtures import make_buy, make_sell, make_state, make_config


class TestBuy:
    def test_basic_buy(self):
        state = make_state(0, 0)
        tx = make_buy("2024-01-01", 100, 1000, fee=142.5)
        cfg = make_config()
        new_state = buy(state, tx, cfg)
        assert new_state.shares == 1000
        assert new_state.total_cost == 100000 + 142.5
        assert new_state.avg_cost == pytest.approx(100.1425, rel=1e-4)

    def test_buy_multiple(self):
        state = make_state(500, 50000)
        tx = make_buy("2024-02-01", 200, 500, fee=142.5)
        cfg = make_config()
        new_state = buy(state, tx, cfg)
        assert new_state.shares == 1000
        assert new_state.total_cost == 50000 + 100000 + 142.5
        assert new_state.avg_cost == pytest.approx(150.1425, rel=1e-4)


class TestSell:
    def test_sell_no_zero_cost(self):
        state = make_state(1000, 100000)
        tx = make_sell("2024-02-01", 80, 500, tax=120)
        cfg = make_config()
        new_state = sell(state, tx, cfg)
        net = 80 * 500 - 120
        assert new_state.shares == 500
        assert new_state.total_cost == pytest.approx(100000 - net, rel=1e-4)
        assert not new_state.is_zero_cost
        assert not tx.zero_cost_triggered

    def test_sell_trigger_zero_cost(self):
        state = make_state(1000, 100000)
        tx = make_sell("2024-02-01", 250, 500, tax=375)
        cfg = make_config()
        new_state = sell(state, tx, cfg)
        assert new_state.shares == 500
        assert new_state.total_cost == 0
        assert new_state.is_zero_cost
        assert new_state.avg_cost == 0
        assert tx.zero_cost_triggered

    def test_sell_equal_zero_cost(self):
        state = make_state(1000, 100000)
        total_sell = 100375
        shares_sold = round(total_sell / 200)
        tax = round(total_sell * 0.003, 2)
        net = total_sell - tax
        tx = make_sell("2024-02-01", 200, shares_sold, tax=tax)
        cfg = make_config()
        new_state = sell(state, tx, cfg)
        assert new_state.shares == 1000 - shares_sold
        assert new_state.total_cost == 0
        assert new_state.is_zero_cost
        assert tx.zero_cost_triggered
