from dataclasses import dataclass, field
from datetime import date as date_module
from core.models import StockState, Transaction
from core.config import Config, is_etf_stock
from core.calculator import apply_transaction


@dataclass
class Portfolio:
    stocks: dict[str, StockState] = field(default_factory=dict)

    def _set_etf_auto(self, stock_code: str, config: Config):
        config.is_etf = is_etf_stock(stock_code)

    def add_init_holding(self, stock_code: str, shares: int, total_cost: float,
                         config: Config, date_str: str | None = None) -> StockState:
        if stock_code in self.stocks and self.stocks[stock_code].shares > 0:
            raise ValueError(f"{stock_code} 已有持倉，請先 remove 再重新設定")
        if date_str is None:
            date_str = date_module.today().isoformat()
        tx = Transaction(
            date=date_str,
            action="init",
            price=round(total_cost / shares, 2) if shares > 0 else 0.0,
            shares=shares,
            total_amount=round(total_cost, 2),
        )
        self._set_etf_auto(stock_code, config)
        new_state = apply_transaction(StockState(), tx, config)
        self.stocks[stock_code] = new_state
        return new_state

    def add_transaction(self, stock_code: str, tx: Transaction, config: Config) -> StockState:
        self._set_etf_auto(stock_code, config)
        state = self.stocks.get(stock_code, StockState())
        new_state = apply_transaction(state, tx, config)
        self.stocks[stock_code] = new_state
        return new_state

    def get_state(self, stock_code: str) -> StockState:
        return self.stocks.get(stock_code, StockState())

    def remove_stock(self, stock_code: str):
        self.stocks.pop(stock_code, None)

    def remove_transaction(self, stock_code: str, index: int, config: Config) -> StockState:
        state = self.stocks.get(stock_code, StockState())
        if index < 0 or index >= len(state.history):
            raise ValueError(f"索引 {index} 超出範圍")
        new_history = state.history[:index] + state.history[index + 1:]
        rebuilt = StockState()
        for tx in new_history:
            rebuilt = apply_transaction(rebuilt, tx, config)
            if rebuilt.shares < 0:
                raise ValueError(
                    f"刪除此交易會導致 {tx.date} 持倉為負（{rebuilt.shares} 股），無法刪除"
                )
        self.stocks[stock_code] = rebuilt
        return rebuilt

    @property
    def stock_codes(self):
        return list(self.stocks.keys())

    def to_dict(self):
        return {code: state.to_dict() for code, state in self.stocks.items()}

    @classmethod
    def from_dict(cls, data):
        stocks = {code: StockState.from_dict(s) for code, s in data.items()}
        return cls(stocks=stocks)
