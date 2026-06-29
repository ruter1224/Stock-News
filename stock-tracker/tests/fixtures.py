from core.models import Transaction, StockState
from core.config import Config


def make_config(fee_rate=0.001425, tax_rate=0.003):
    cfg = Config()
    cfg.fee_rate = fee_rate
    cfg.tax_rate_listed = tax_rate
    return cfg


def make_state(shares=0, total_cost=0.0, is_zero_cost=None):
    if is_zero_cost is None:
        is_zero_cost = (shares > 0 and total_cost == 0)
    avg = total_cost / shares if shares > 0 else 0.0
    return StockState(
        shares=shares,
        total_cost=total_cost,
        avg_cost=avg,
        is_zero_cost=is_zero_cost,
    )


def make_buy(date: str, price: float, shares: int, fee: float = 0.0):
    tx = Transaction(
        date=date,
        action="buy",
        price=price,
        shares=shares,
        fee=fee,
        total_amount=round(price * shares, 2),
    )
    return tx


def make_sell(date: str, price: float, shares: int, tax: float = 0.0):
    tx = Transaction(
        date=date,
        action="sell",
        price=price,
        shares=shares,
        tax=tax,
        total_amount=round(price * shares, 2),
    )
    return tx


def make_dividend_reinvest(date: str, price: float, shares: int,
                           dividend_per_share: float, dividend_total: float,
                           fee: float = 0.0):
    tx = Transaction(
        date=date,
        action="dividend_reinvest",
        price=price,
        shares=shares,
        fee=fee,
        total_amount=round(price * shares, 2),
        dividend_per_share=dividend_per_share,
        dividend_total=dividend_total,
    )
    return tx


def make_init(date: str, price: float, shares: int, total_amount: float):
    tx = Transaction(
        date=date,
        action="init",
        price=price,
        shares=shares,
        total_amount=total_amount,
    )
    return tx


def make_stock_dividend(date: str, per_thousand: int, additional: int):
    tx = Transaction(
        date=date,
        action="stock_dividend",
        price=0,
        shares=0,
        per_thousand_shares=per_thousand,
        additional_shares=additional,
    )
    return tx
