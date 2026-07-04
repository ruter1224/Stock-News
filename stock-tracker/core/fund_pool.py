from dataclasses import dataclass, field


@dataclass
class FundTransaction:
    date: str
    type: str
    amount: float
    remark: str = ""

    def to_dict(self):
        return {
            "date": self.date,
            "type": self.type,
            "amount": self.amount,
            "remark": self.remark,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            date=data["date"],
            type=data["type"],
            amount=data["amount"],
            remark=data.get("remark", ""),
        )


@dataclass
class FundSnapshot:
    date: str
    total_value: float
    total_deposits: float
    growth_rate: float
    cash_balance: float
    period_label: str = ""

    def to_dict(self):
        return {
            "date": self.date,
            "total_value": self.total_value,
            "total_deposits": self.total_deposits,
            "growth_rate": self.growth_rate,
            "cash_balance": self.cash_balance,
            "period_label": self.period_label,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            date=data["date"],
            total_value=data["total_value"],
            total_deposits=data["total_deposits"],
            growth_rate=data["growth_rate"],
            cash_balance=data["cash_balance"],
            period_label=data.get("period_label", ""),
        )


@dataclass
class FundPool:
    initial_capital: float = 0.0
    transactions: list[FundTransaction] = field(default_factory=list)
    snapshots: list[FundSnapshot] = field(default_factory=list)

    def calculate_cash_balance(self, portfolio) -> float:
        total_deposits = self.initial_capital + sum(
            t.amount for t in self.transactions if t.type == "deposit"
        )
        total_withdrawals = sum(
            t.amount for t in self.transactions if t.type == "withdraw"
        )

        total_buy_cost = 0.0
        total_sell_proceeds = 0.0
        total_dividends = 0.0

        for code, state in portfolio.stocks.items():
            for tx in state.history:
                if tx.action == "buy":
                    total_buy_cost += tx.total_amount + tx.fee
                elif tx.action == "sell":
                    total_sell_proceeds += tx.total_amount - tx.tax
                elif tx.action == "dividend":
                    total_dividends += tx.dividend_total

        return (
            total_deposits
            - total_withdrawals
            - total_buy_cost
            + total_sell_proceeds
            + total_dividends
        )

    def get_current_value(self, portfolio, prices: dict) -> float:
        cash = self.calculate_cash_balance(portfolio)
        portfolio_value = sum(
            (prices.get(code, [None])[0] or 0) * state.shares
            for code, state in portfolio.stocks.items()
        )
        return cash + portfolio_value

    def get_growth_rate(self, portfolio, prices: dict) -> float:
        net_invested = self.initial_capital + sum(
            t.amount for t in self.transactions if t.type == "deposit"
        ) - sum(t.amount for t in self.transactions if t.type == "withdraw")
        if net_invested <= 0:
            return 0.0
        total_value = self.get_current_value(portfolio, prices)
        return (total_value / net_invested - 1) * 100

    def to_dict(self):
        return {
            "initial_capital": self.initial_capital,
            "transactions": [t.to_dict() for t in self.transactions],
            "snapshots": [s.to_dict() for s in self.snapshots],
        }

    @classmethod
    def from_dict(cls, data: dict):
        pool = cls(initial_capital=data.get("initial_capital", 0.0))
        pool.transactions = [
            FundTransaction.from_dict(t) for t in data.get("transactions", [])
        ]
        pool.snapshots = [FundSnapshot.from_dict(s) for s in data.get("snapshots", [])]
        return pool
