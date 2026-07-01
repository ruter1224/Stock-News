from dataclasses import dataclass, field


@dataclass
class Transaction:
    date: str
    action: str
    price: float
    shares: int
    fee: float = 0.0
    tax: float = 0.0
    total_amount: float = 0.0
    zero_cost_triggered: bool = False

    dividend_per_share: float = 0.0
    dividend_total: float = 0.0

    per_thousand_shares: int = 0
    additional_shares: int = 0

    remark: str = ""

    def __post_init__(self):
        if self.total_amount == 0.0 and self.price > 0 and self.shares > 0:
            self.total_amount = round(self.price * self.shares, 2)

    def to_dict(self):
        return {
            "date": self.date,
            "action": self.action,
            "price": self.price,
            "shares": self.shares,
            "fee": self.fee,
            "tax": self.tax,
            "total_amount": self.total_amount,
            "zero_cost_triggered": self.zero_cost_triggered,
            "dividend_per_share": self.dividend_per_share,
            "dividend_total": self.dividend_total,
            "per_thousand_shares": self.per_thousand_shares,
            "additional_shares": self.additional_shares,
            "remark": self.remark,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            date=data["date"],
            action=data["action"],
            price=data["price"],
            shares=data["shares"],
            fee=data.get("fee", 0.0),
            tax=data.get("tax", 0.0),
            total_amount=data.get("total_amount", 0.0),
            zero_cost_triggered=data.get("zero_cost_triggered", False),
            dividend_per_share=data.get("dividend_per_share", 0.0),
            dividend_total=data.get("dividend_total", 0.0),
            per_thousand_shares=data.get("per_thousand_shares", 0),
            additional_shares=data.get("additional_shares", 0),
            remark=data.get("remark", ""),
        )


@dataclass
class StockState:
    shares: int = 0
    total_cost: float = 0.0
    avg_cost: float = 0.0
    is_zero_cost: bool = False
    history: list[Transaction] = field(default_factory=list)
    total_dividend_received: float = 0.0
    dividend_offset_applied: float = 0.0
    archived: bool = False

    def to_dict(self):
        return {
            "shares": self.shares,
            "total_cost": self.total_cost,
            "avg_cost": self.avg_cost,
            "is_zero_cost": self.is_zero_cost,
            "history": [t.to_dict() for t in self.history],
            "total_dividend_received": self.total_dividend_received,
            "dividend_offset_applied": self.dividend_offset_applied,
            "archived": self.archived,
        }

    @classmethod
    def from_dict(cls, data: dict):
        state = cls(
            shares=data["shares"],
            total_cost=data["total_cost"],
            avg_cost=data["avg_cost"],
            is_zero_cost=data["is_zero_cost"],
            history=[Transaction.from_dict(t) for t in data.get("history", [])],
            total_dividend_received=data.get("total_dividend_received", 0.0),
            dividend_offset_applied=data.get("dividend_offset_applied", 0.0),
            archived=data.get("archived", False),
        )
        return state
