import csv
from pathlib import Path
from core.models import Transaction
from core.portfolio import Portfolio
from core.config import Config

COLUMN_MAP = {
    "date": ["date", "日期", "成交日期", "交易日期", "買賣日期"],
    "stock": ["stock", "股票代號", "證券代號", "代號", "股票代碼"],
    "action": ["action", "買進/賣出", "買賣別", "交易別", "方向", "買/賣"],
    "price": ["price", "單價", "成交價格", "價格", "成交單價"],
    "shares": ["shares", "股數", "數量", "成交股數", "股份"],
    "fee": ["fee", "手續費"],
    "tax": ["tax", "交易稅", "證券交易稅", "證交稅"],
    "total_amount": ["total_amount", "淨付金額", "淨收付", "金額", "成交金額"],
}

ACTION_MAP = {
    "買": "buy", "買進": "buy", "買入": "buy",
    "B": "buy", "b": "buy", "BUY": "buy", "buy": "buy",
    "賣": "sell", "賣出": "sell", "賣掉": "sell",
    "S": "sell", "s": "sell", "SELL": "sell", "sell": "sell",
}


def _detect_column(header, field):
    candidates = COLUMN_MAP.get(field, [field])
    for c in candidates:
        for h in header:
            if h.strip() == c:
                return h
    return None


def _normalize_action(val):
    val = val.strip()
    return ACTION_MAP.get(val, val)


def _parse_date(val):
    val = val.strip().replace("/", "-")
    parts = val.split("-")
    if len(parts) == 3 and len(parts[0]) == 3:
        parts[0] = str(int(parts[0]) + 1911)
        val = "-".join(parts)
    return val


def parse_trades_csv(filepath, portfolio=None, config=None):
    p = Path(filepath)
    if not p.exists():
        raise FileNotFoundError(f"找不到檔案：{filepath}")

    if portfolio is None:
        portfolio = Portfolio()
    if config is None:
        config = Config()

    rows = []
    with open(p, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = [h.strip() for h in next(reader)]

        cols = {}
        for field in ["date", "stock", "action", "price", "shares", "fee", "tax"]:
            match = _detect_column(header, field)
            if match:
                cols[field] = header.index(match)

        if "date" not in cols:
            raise ValueError("CSV 缺少日期欄位")
        if "action" not in cols:
            raise ValueError("CSV 缺少買賣別欄位")
        if "price" not in cols:
            raise ValueError("CSV 缺少價格欄位")
        if "shares" not in cols:
            raise ValueError("CSV 缺少股數欄位")

        for line_no, row in enumerate(reader, 2):
            if not any(cell.strip() for cell in row):
                continue

            def _g(field):
                idx = cols.get(field)
                return row[idx].strip() if idx is not None and idx < len(row) else ""

            date = _parse_date(_g("date"))
            action = _normalize_action(_g("action"))
            price = float(_g("price").replace(",", ""))
            shares = int(float(_g("shares").replace(",", "")))

            stock_code = _g("stock") if "stock" in cols else "0000"
            fee = float(_g("fee").replace(",", "")) if (_g("fee") and _g("fee") != "-") else 0.0
            tax = float(_g("tax").replace(",", "")) if (_g("tax") and _g("tax") != "-") else 0.0

            if action not in ("buy", "sell", "dividend", "dividend_reinvest", "stock_dividend"):
                raise ValueError(f"第 {line_no} 行無法識別的交易類型：{action}")

            total_amount = round(price * shares, 2)
            tx = Transaction(
                date=date, action=action, price=price, shares=shares,
                fee=fee, tax=tax, total_amount=total_amount,
            )
            rows.append((stock_code, tx))

    applied = 0
    for stock_code, tx in rows:
        portfolio.add_transaction(stock_code, tx, config)
        applied += 1

    return portfolio, applied


def export_trades_csv(portfolio, filepath):
    p = Path(filepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["日期", "股票代號", "買賣別", "價格", "股數", "手續費", "交易稅", "成交金額"])
        for code in sorted(portfolio.stock_codes):
            st = portfolio.get_state(code)
            for tx in st.history:
                action_map = {
                    "buy": "買進", "sell": "賣出", "dividend": "現金股利",
                    "dividend_reinvest": "股利再投資", "stock_dividend": "股票股利",
                }
                w.writerow([
                    tx.date, code, action_map.get(tx.action, tx.action),
                    tx.price, tx.shares, tx.fee, tx.tax, tx.total_amount,
                ])
    return len(portfolio.stock_codes)
