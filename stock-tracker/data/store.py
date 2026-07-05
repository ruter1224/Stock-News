import json
from pathlib import Path
from core.models import StockState
from core.portfolio import Portfolio


def save_portfolio(portfolio, path):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(portfolio.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_portfolio(path):
    p = Path(path)
    if not p.exists():
        return Portfolio()
    data = json.loads(p.read_text(encoding="utf-8"))
    if not data:
        return Portfolio()
    # 向後相容：舊格式是單一 StockState（有 shares key）
    if "shares" in data:
        state = StockState.from_dict(data)
        return Portfolio(stocks={"0000": state})
    portfolio = Portfolio.from_dict(data)
    # 自動遷移：清理孤兒記錄（shares=0 且 history=[]）
    cleaned = False
    for code in list(portfolio.stocks.keys()):
        state = portfolio.stocks[code]
        if state.shares == 0 and not state.history:
            del portfolio.stocks[code]
            cleaned = True
    if cleaned:
        save_portfolio(portfolio, path)
    # 自動遷移：將 shares == 0 的股票標記為已封存
    migrated = False
    for code, state in portfolio.stocks.items():
        if state.shares == 0 and not state.archived:
            state.archived = True
            migrated = True
    if migrated:
        save_portfolio(portfolio, path)
    return portfolio


def save_fund_pool(fund_pool, path):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(fund_pool.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_fund_pool(path):
    from core.fund_pool import FundPool
    p = Path(path)
    if not p.exists():
        return FundPool()
    data = json.loads(p.read_text(encoding="utf-8"))
    if not data:
        return FundPool()
    # 向後相容：忽略舊格式的 initial_capital 和 transactions
    return FundPool.from_dict(data)
