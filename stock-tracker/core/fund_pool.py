from dataclasses import dataclass, field


@dataclass
class FundSnapshot:
    date: str
    total_value: float
    growth_rate: float
    cash_balance: float = 0.0
    market_value: float = 0.0

    def to_dict(self):
        return {
            "date": self.date,
            "total_value": self.total_value,
            "growth_rate": self.growth_rate,
            "cash_balance": self.cash_balance,
            "market_value": self.market_value,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            date=data["date"],
            total_value=data["total_value"],
            growth_rate=data["growth_rate"],
            cash_balance=data.get("cash_balance", 0.0),
            market_value=data.get("market_value", 0.0),
        )


@dataclass
class FundPool:
    snapshots: list[FundSnapshot] = field(default_factory=list)

    def to_dict(self):
        return {
            "snapshots": [s.to_dict() for s in self.snapshots],
        }

    @classmethod
    def from_dict(cls, data: dict):
        pool = cls()
        pool.snapshots = [FundSnapshot.from_dict(s) for s in data.get("snapshots", [])]
        return pool


def calculate_cash_balance(portfolio) -> float:
    """從 portfolio trading history 自動計算可用現金"""
    cash = 0.0

    for state in portfolio.stocks.values():
        for tx in state.history:
            if tx.action == "buy":
                cash -= tx.total_amount + tx.fee
            elif tx.action == "sell":
                cash += tx.total_amount - tx.tax
            elif tx.action == "dividend":
                cash += tx.dividend_total

    return cash
