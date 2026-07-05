from core.fund_pool import FundPool, FundSnapshot, calculate_cash_balance
from core.portfolio import Portfolio
from core.models import Transaction
from tests.fixtures import make_config


class TestCalculateCashBalance:
    def _make_portfolio(self, transactions):
        portfolio = Portfolio()
        cfg = make_config(fee_rate=0.001425, tax_rate=0.003)
        for code, tx in transactions:
            portfolio.add_transaction(code, tx, cfg)
        return portfolio

    def test_empty_portfolio(self):
        portfolio = Portfolio()
        assert calculate_cash_balance(portfolio) == 0.0

    def test_init_only(self):
        tx = Transaction(date="2024-01-01", action="init", price=100, shares=1000, total_amount=100000)
        portfolio = self._make_portfolio([("2330", tx)])
        assert calculate_cash_balance(portfolio) == 0.0

    def test_init_then_buy(self):
        tx1 = Transaction(date="2024-01-01", action="init", price=100, shares=1000, total_amount=100000)
        tx2 = Transaction(date="2024-02-01", action="buy", price=200, shares=500, total_amount=100000, fee=142.5)
        portfolio = self._make_portfolio([("2330", tx1), ("2330", tx2)])
        assert calculate_cash_balance(portfolio) == -100142.5

    def test_sell_returns_cash(self):
        tx1 = Transaction(date="2024-01-01", action="init", price=100, shares=1000, total_amount=100000)
        tx2 = Transaction(date="2024-06-01", action="sell", price=150, shares=500, total_amount=75000, tax=225)
        portfolio = self._make_portfolio([("2330", tx1), ("2330", tx2)])
        assert calculate_cash_balance(portfolio) == 75000 - 225

    def test_dividend_returns_cash(self):
        tx1 = Transaction(date="2024-01-01", action="init", price=100, shares=1000, total_amount=100000)
        tx2 = Transaction(date="2024-07-01", action="dividend", price=0, shares=0, total_amount=5500, dividend_total=5500)
        portfolio = self._make_portfolio([("2330", tx1), ("2330", tx2)])
        assert calculate_cash_balance(portfolio) == 5500.0

    def test_dividend_reinvest_no_cash_change(self):
        tx1 = Transaction(date="2024-01-01", action="init", price=100, shares=1000, total_amount=100000)
        tx2 = Transaction(date="2024-07-01", action="dividend_reinvest", price=150, shares=36, total_amount=5400, fee=7.7)
        portfolio = self._make_portfolio([("2330", tx1), ("2330", tx2)])
        assert calculate_cash_balance(portfolio) == 0.0

    def test_stock_dividend_no_cash_change(self):
        tx1 = Transaction(date="2024-01-01", action="init", price=100, shares=1000, total_amount=100000)
        tx2 = Transaction(date="2024-07-01", action="stock_dividend", price=0, shares=0, total_amount=0, additional_shares=100)
        portfolio = self._make_portfolio([("2330", tx1), ("2330", tx2)])
        assert calculate_cash_balance(portfolio) == 0.0

    def test_multiple_stocks(self):
        tx1 = Transaction(date="2024-01-01", action="init", price=100, shares=1000, total_amount=100000)
        tx2 = Transaction(date="2024-01-01", action="init", price=50, shares=2000, total_amount=100000)
        portfolio = self._make_portfolio([("2330", tx1), ("2317", tx2)])
        assert calculate_cash_balance(portfolio) == 0.0


class TestFundPool:
    def test_empty_pool(self):
        pool = FundPool()
        assert pool.snapshots == []
        assert pool.to_dict() == {"snapshots": []}

    def test_from_dict_empty(self):
        pool = FundPool.from_dict({})
        assert pool.snapshots == []

    def test_from_dict_backward_compat_old_format(self):
        old_data = {
            "initial_capital": 100000,
            "transactions": [
                {"date": "2024-01-01", "type": "deposit", "amount": 50000, "remark": ""}
            ],
            "snapshots": [
                {
                    "date": "2024-03-31",
                    "total_value": 115000,
                    "total_deposits": 150000,
                    "growth_rate": 15.0,
                    "cash_balance": 25000,
                    "period_label": "2024-Q1",
                }
            ],
        }
        pool = FundPool.from_dict(old_data)
        assert len(pool.snapshots) == 1
        assert pool.snapshots[0].date == "2024-03-31"
        assert pool.snapshots[0].total_value == 115000

    def test_to_dict_roundtrip(self):
        pool = FundPool(snapshots=[
            FundSnapshot(date="2024-03-31", total_value=115000, growth_rate=15.0, cash_balance=25000, market_value=90000),
        ])
        data = pool.to_dict()
        pool2 = FundPool.from_dict(data)
        assert len(pool2.snapshots) == 1
        assert pool2.snapshots[0].date == "2024-03-31"
        assert pool2.snapshots[0].total_value == 115000
        assert pool2.snapshots[0].cash_balance == 25000
        assert pool2.snapshots[0].market_value == 90000


class TestFundSnapshot:
    def test_to_dict(self):
        s = FundSnapshot(date="2024-03-31", total_value=115000, growth_rate=15.0, cash_balance=25000, market_value=90000)
        d = s.to_dict()
        assert d["date"] == "2024-03-31"
        assert d["total_value"] == 115000
        assert d["growth_rate"] == 15.0
        assert d["cash_balance"] == 25000
        assert d["market_value"] == 90000

    def test_from_dict_defaults(self):
        s = FundSnapshot.from_dict({"date": "2024-03-31", "total_value": 100, "growth_rate": 0})
        assert s.cash_balance == 0.0
        assert s.market_value == 0.0
