from core.models import StockState


def buy(state, tx, config):
    if tx.action != "buy":
        return state

    new_shares = state.shares + tx.shares
    fee = round(tx.total_amount * config.fee_rate, 2) if tx.fee == 0 else tx.fee
    new_cost = state.total_cost + tx.total_amount + fee

    tx.fee = fee
    tx.total_amount = round(tx.price * tx.shares, 2)

    avg = new_cost / new_shares if new_shares > 0 else 0.0
    return StockState(
        shares=new_shares,
        total_cost=new_cost,
        avg_cost=avg,
        is_zero_cost=(new_shares > 0 and new_cost == 0),
        history=state.history + [tx],
    )


def sell(state, tx, config):
    if tx.action != "sell":
        return state

    if tx.shares > state.shares:
        raise ValueError("賣出股數不可大於持有股數")

    gross = tx.total_amount
    tax = round(gross * config.tax_rate, 2) if tx.tax == 0 else tx.tax
    net = gross - tax

    tx.tax = tax

    new_shares = state.shares - tx.shares
    if net >= state.total_cost:
        tx.zero_cost_triggered = True
        new_cost = 0.0
    else:
        tx.zero_cost_triggered = False
        new_cost = round(state.total_cost - net, 2)

    avg = new_cost / new_shares if new_shares > 0 else 0.0

    return StockState(
        shares=new_shares,
        total_cost=new_cost,
        avg_cost=avg,
        is_zero_cost=(new_shares > 0 and new_cost == 0),
        history=state.history + [tx],
    )


def dividend_reinvest(state, tx, config):
    if tx.action != "dividend_reinvest":
        return state

    fee = round(tx.total_amount * config.fee_rate, 2) if tx.fee == 0 else tx.fee
    total_amount = round(tx.price * tx.shares, 2)
    new_cost = state.total_cost + total_amount + fee

    tx.fee = fee
    tx.total_amount = total_amount

    new_shares = state.shares + tx.shares
    avg = new_cost / new_shares if new_shares > 0 else 0.0

    return StockState(
        shares=new_shares,
        total_cost=new_cost,
        avg_cost=avg,
        is_zero_cost=(new_shares > 0 and new_cost == 0),
        history=state.history + [tx],
    )


def stock_dividend(state, tx, config):
    if tx.action != "stock_dividend":
        return state

    new_shares = state.shares + tx.additional_shares
    avg = state.total_cost / new_shares if new_shares > 0 else 0.0

    return StockState(
        shares=new_shares,
        total_cost=state.total_cost,
        avg_cost=avg,
        is_zero_cost=(new_shares > 0 and state.total_cost == 0),
        history=state.history + [tx],
    )


def init_holding(state, tx, config):
    if tx.action != "init":
        return state
    new_shares = tx.shares
    new_cost = round(tx.total_amount, 2)
    avg = new_cost / new_shares if new_shares > 0 else 0.0
    return StockState(
        shares=new_shares,
        total_cost=new_cost,
        avg_cost=avg,
        is_zero_cost=(new_cost == 0),
        history=state.history + [tx],
    )


def dividend(state, tx, config):
    if tx.action != "dividend":
        return state
    return StockState(
        shares=state.shares,
        total_cost=state.total_cost,
        avg_cost=state.avg_cost,
        is_zero_cost=state.is_zero_cost,
        history=state.history + [tx],
    )


def apply_transaction(state, tx, config):
    dispatch = {
        "init": init_holding,
        "buy": buy,
        "sell": sell,
        "dividend_reinvest": dividend_reinvest,
        "stock_dividend": stock_dividend,
        "dividend": dividend,
    }
    handler = dispatch.get(tx.action)
    if handler is None:
        raise ValueError(f"不支援的交易類型: {tx.action}")
    return handler(state, tx, config)


