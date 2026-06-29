import pytest
from core.calculator import dividend_reinvest
from tests.fixtures import (
    make_buy, make_dividend_reinvest, make_state, make_config,
)


class TestDividendReinvest:
    def test_dividend_reinvest(self):
        cfg = make_config(fee_rate=0, tax_rate=0)
        state = make_state(1000, 100000)

        total_dividend = 1000 * 5.5
        shares_bought = int(total_dividend / 150)
        tx = make_dividend_reinvest(
            date="2024-07-01",
            price=150,
            shares=shares_bought,
            dividend_per_share=5.5,
            dividend_total=total_dividend,
        )
        new_state = dividend_reinvest(state, tx, cfg)

        expected_total_amount = round(150 * shares_bought, 2)
        expected_cost = 100000 + expected_total_amount
        expected_shares = 1000 + shares_bought

        assert new_state.shares == expected_shares
        assert new_state.total_cost == pytest.approx(expected_cost, rel=1e-4)
        assert new_state.avg_cost == pytest.approx(
            expected_cost / expected_shares, rel=1e-4
        )

    def test_dividend_reinvest_with_fee(self):
        cfg = make_config(fee_rate=0.001425, tax_rate=0)
        state = make_state(2000, 300000)

        total_dividend = 2000 * 3.0
        price = 100
        shares_bought = int(total_dividend / price)
        total_amount = round(price * shares_bought, 2)
        fee = round(total_amount * 0.001425, 2)
        tx = make_dividend_reinvest(
            date="2024-08-01",
            price=price,
            shares=shares_bought,
            dividend_per_share=3.0,
            dividend_total=total_dividend,
            fee=fee,
        )
        new_state = dividend_reinvest(state, tx, cfg)

        expected_cost = 300000 + total_amount + fee
        expected_shares = 2000 + shares_bought

        assert new_state.shares == expected_shares
        assert new_state.total_cost == pytest.approx(expected_cost, rel=1e-4)
