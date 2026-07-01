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

    # 自動解封：如果之前已封存，現在重新買入
    new_archived = state.archived
    if state.archived:
        new_archived = False
        tx.remark = "重新買入"

    return StockState(
        shares=new_shares,
        total_cost=new_cost,
        avg_cost=avg,
        is_zero_cost=(new_shares > 0 and new_cost == 0),
        history=state.history + [tx],
        total_dividend_received=state.total_dividend_received,
        dividend_offset_applied=state.dividend_offset_applied,
        archived=new_archived,
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

    # 自動封存：賣出後股數為 0
    new_archived = state.archived
    if new_shares == 0:
        new_archived = True
        tx.remark = "已出清"

    return StockState(
        shares=new_shares,
        total_cost=new_cost,
        avg_cost=avg,
        is_zero_cost=(new_shares > 0 and new_cost == 0),
        history=state.history + [tx],
        total_dividend_received=state.total_dividend_received,
        dividend_offset_applied=state.dividend_offset_applied,
        archived=new_archived,
    )


def dividend_reinvest(state, tx, config):
    if tx.action != "dividend_reinvest":
        return state

    fee = round(tx.total_amount * config.fee_rate, 2) if tx.fee == 0 else tx.fee
    total_amount = round(tx.price * tx.shares, 2)

    tx.fee = fee
    tx.total_amount = total_amount

    new_shares = state.shares + tx.shares
    
    # 取得再投資模式
    mode = getattr(config, 'reinvest_mode', 'direct')
    
    if mode == "direct":
        # 模式 A：直接扣成本，不管有沒有收過股利
        offset = min(total_amount, state.total_cost)
        excess = total_amount - offset
        new_cost = state.total_cost - offset + excess
        # 備註
        if state.total_dividend_received == 0:
            tx.remark = "無對應股利記錄"
        else:
            remaining = state.total_dividend_received - state.dividend_offset_applied - offset
            if remaining > 0:
                tx.remark = f"已對沖 {offset:,.0f}，剩餘 {remaining:,.0f}"
            else:
                tx.remark = f"已對沖 {offset:,.0f}"
    else:
        # 模式 B：需有股利才能扣，超過部分當一般買入
        available = state.total_dividend_received - state.dividend_offset_applied
        offset = min(total_amount, available, state.total_cost)
        excess = total_amount - offset
        new_cost = state.total_cost - offset + excess
        # 備註
        if offset == 0:
            tx.remark = f"無可用股利，全部 {total_amount:,.0f} 計入成本"
        else:
            remaining = available - offset
            if excess > 0:
                tx.remark = f"已對沖 {offset:,.0f}，超額 {excess:,.0f} 計入成本"
            elif remaining > 0:
                tx.remark = f"已對沖 {offset:,.0f}，剩餘 {remaining:,.0f}"
            else:
                tx.remark = f"已對沖 {offset:,.0f}"
    
    new_div_offset = state.dividend_offset_applied + offset
    
    avg = new_cost / new_shares if new_shares > 0 else 0.0

    return StockState(
        shares=new_shares,
        total_cost=new_cost,
        avg_cost=avg,
        is_zero_cost=(new_shares > 0 and new_cost == 0),
        history=state.history + [tx],
        total_dividend_received=state.total_dividend_received,
        dividend_offset_applied=new_div_offset,
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
        total_dividend_received=state.total_dividend_received,
        dividend_offset_applied=state.dividend_offset_applied,
    )


def init_holding(state, tx, config):
    if tx.action != "init":
        return state
    new_shares = tx.shares
    new_cost = round(tx.total_amount, 2)
    avg = new_cost / new_shares if new_shares > 0 else 0.0

    if state.archived:
        tx.remark = "重新買入"

    return StockState(
        shares=new_shares,
        total_cost=new_cost,
        avg_cost=avg,
        is_zero_cost=(new_cost == 0),
        history=state.history + [tx],
        total_dividend_received=0.0,
        dividend_offset_applied=0.0,
        archived=False,
    )


def dividend(state, tx, config):
    if tx.action != "dividend":
        return state
    new_div_total = state.total_dividend_received + tx.dividend_total
    return StockState(
        shares=state.shares,
        total_cost=state.total_cost,
        avg_cost=state.avg_cost,
        is_zero_cost=state.is_zero_cost,
        history=state.history + [tx],
        total_dividend_received=new_div_total,
        dividend_offset_applied=state.dividend_offset_applied,
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


