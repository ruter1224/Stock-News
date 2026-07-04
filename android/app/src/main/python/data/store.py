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
    return Portfolio.from_dict(data)
