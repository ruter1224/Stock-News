import pytest
from core.calculator import init_holding, apply_transaction
from core.portfolio import Portfolio
from core.models import StockState, Transaction
from core.config import Config
from tests.fixtures import make_config, make_init, make_buy


class TestInitHolding:

    def test_init_basic(self):
        cfg = make_config()
        state = StockState()
        tx = make_init("2026-01-01", 250.0, 2000, 500000.0)
        new = init_holding(state, tx, cfg)
        assert new.shares == 2000
        assert new.total_cost == 500000.0
        assert new.avg_cost == 250.0
        assert not new.is_zero_cost
        assert len(new.history) == 1

    def test_init_zero_cost(self):
        cfg = make_config()
        state = StockState()
        tx = make_init("2026-01-01", 0.0, 1000, 0.0)
        new = init_holding(state, tx, cfg)
        assert new.shares == 1000
        assert new.total_cost == 0.0
        assert new.avg_cost == 0.0
        assert new.is_zero_cost
        assert len(new.history) == 1

    def test_init_ignores_wrong_action(self):
        cfg = make_config()
        state = StockState()
        tx = make_init("2026-01-01", 250.0, 2000, 500000.0)
        tx.action = "buy"
        new = init_holding(state, tx, cfg)
        assert new.shares == 0
        assert new.total_cost == 0.0

    def test_init_with_existing_state_uses_empty(self):
        cfg = make_config()
        existing = StockState(shares=100, total_cost=25000.0, avg_cost=250.0)
        tx = make_init("2026-01-01", 300.0, 500, 150000.0)
        new = init_holding(existing, tx, cfg)
        assert new.shares == 500
        assert new.total_cost == 150000.0
        assert new.avg_cost == 300.0


class TestPortfolioInitHolding:

    def test_add_init_holding(self):
        p = Portfolio()
        cfg = make_config()
        state = p.add_init_holding("2330", 2000, 500000.0, cfg, "2026-01-01")
        assert state.shares == 2000
        assert state.total_cost == 500000.0
        assert state.avg_cost == 250.0
        assert p.stocks["2330"] is state

    def test_add_init_holding_default_date(self):
        p = Portfolio()
        cfg = make_config()
        state = p.add_init_holding("2330", 1000, 300000.0, cfg)
        assert state.shares == 1000
        tx = state.history[0]
        assert tx.action == "init"
        assert tx.date is not None

    def test_add_init_holding_duplicate_rejected(self):
        p = Portfolio()
        cfg = make_config()
        p.add_init_holding("2330", 1000, 250000.0, cfg, "2026-01-01")
        with pytest.raises(ValueError, match="已有持倉"):
            p.add_init_holding("2330", 500, 100000.0, cfg, "2026-01-02")

    def test_init_then_buy(self):
        p = Portfolio()
        cfg = make_config()
        p.add_init_holding("2330", 1000, 250000.0, cfg, "2026-01-01")
        tx = make_buy("2026-06-01", 300.0, 500)
        p.add_transaction("2330", tx, cfg)
        state = p.get_state("2330")
        assert state.shares == 1500
        fee = round(150000.0 * cfg.fee_rate, 2)
        expected_cost = 250000.0 + 150000.0 + fee
        assert state.total_cost == expected_cost
        assert len(state.history) == 2

    def test_remove_init_holding(self):
        p = Portfolio()
        cfg = make_config()
        p.add_init_holding("2330", 1000, 250000.0, cfg, "2026-01-01")
        assert "2330" in p.stocks
        p.remove_stock("2330")
        assert "2330" not in p.stocks

    def test_add_init_holding_zero_cost(self):
        p = Portfolio()
        cfg = make_config()
        state = p.add_init_holding("0000", 1000, 0.0, cfg, "2026-01-01")
        assert state.shares == 1000
        assert state.total_cost == 0.0
        assert state.is_zero_cost

    def test_portfolio_serialization_with_init(self):
        p = Portfolio()
        cfg = make_config()
        p.add_init_holding("2330", 2000, 500000.0, cfg, "2026-01-01")
        data = p.to_dict()
        assert "2330" in data
        assert data["2330"]["shares"] == 2000
        assert data["2330"]["total_cost"] == 500000.0
        assert data["2330"]["history"][0]["action"] == "init"

        p2 = Portfolio.from_dict(data)
        assert p2.get_state("2330").shares == 2000
        assert p2.get_state("2330").total_cost == 500000.0


class TestInitInReport:

    def test_init_counts_in_total_invested(self):
        from core.report import generate_report
        cfg = make_config()
        p = Portfolio()
        p.add_init_holding("2330", 2000, 500000.0, cfg, "2026-01-01")
        state = p.get_state("2330")
        rep = generate_report(state)
        assert rep.total_invested == 500000.0

    def test_init_then_buy_invested(self):
        from core.report import generate_report
        cfg = make_config()
        p = Portfolio()
        p.add_init_holding("2330", 1000, 250000.0, cfg, "2026-01-01")
        tx = make_buy("2026-06-01", 300.0, 500)
        p.add_transaction("2330", tx, cfg)
        state = p.get_state("2330")
        rep = generate_report(state)
        fee = round(150000.0 * cfg.fee_rate, 2)
        assert rep.total_invested == 250000.0 + 150000.0 + fee
