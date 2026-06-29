import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from core.models import StockState


@dataclass
class Report:
    shares: int = 0
    total_cost: float = 0.0
    avg_cost: float = 0.0
    is_zero_cost: bool = False
    total_invested: float = 0.0
    total_recovered: float = 0.0
    total_dividend_income: float = 0.0
    total_fees: float = 0.0
    total_taxes: float = 0.0
    realized_pl: float = 0.0
    unrealized_pl: float = 0.0
    unrealized_pl_pct: float | None = None
    total_pl: float = 0.0
    total_roi_pct: float = 0.0
    current_price: float | None = None
    current_value: float = 0.0


def generate_report(state: StockState, current_price: float | None = None) -> Report:
    total_invested = 0.0
    total_recovered = 0.0
    total_dividend = 0.0
    total_fees = 0.0
    total_taxes = 0.0

    for tx in state.history:
        if tx.action in ("init", "buy", "dividend_reinvest"):
            total_invested += tx.total_amount + tx.fee
            total_fees += tx.fee
        elif tx.action == "sell":
            net = tx.total_amount - tx.tax
            total_recovered += net
            total_taxes += tx.tax
            total_fees += tx.fee
        elif tx.action == "dividend":
            total_dividend += tx.dividend_total

    realized_pl = round(total_recovered + state.total_cost - total_invested, 2)

    rep = Report(
        shares=state.shares,
        total_cost=round(state.total_cost, 2),
        avg_cost=round(state.avg_cost, 2),
        is_zero_cost=state.is_zero_cost,
        total_invested=round(total_invested, 2),
        total_recovered=round(total_recovered, 2),
        total_dividend_income=round(total_dividend, 2),
        total_fees=round(total_fees, 2),
        total_taxes=round(total_taxes, 2),
        realized_pl=realized_pl,
    )

    if current_price is not None:
        rep.current_price = current_price
        rep.current_value = round(current_price * state.shares, 2)
        rep.unrealized_pl = round(rep.current_value - state.total_cost, 2)
        if state.total_cost > 0:
            rep.unrealized_pl_pct = round(
                (rep.unrealized_pl / state.total_cost) * 100, 2
            )
    else:
        rep.unrealized_pl = round(-state.total_cost, 2) if state.is_zero_cost else 0.0

    rep.total_pl = round(rep.realized_pl + rep.unrealized_pl, 2)
    if total_invested > 0:
        rep.total_roi_pct = round((rep.total_pl / total_invested) * 100, 2)

    return rep


def export_report_csv(rep, state, filepath):
    p = Path(filepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)

        w.writerow(["項目", "數值"])
        w.writerow(["報告產生時間", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        w.writerow(["持有股數", rep.shares])
        w.writerow(["總成本", rep.total_cost])
        w.writerow(["平均成本", rep.avg_cost])
        w.writerow(["零成本狀態", "是" if rep.is_zero_cost else "否"])
        w.writerow([])
        w.writerow(["總投入成本", rep.total_invested])
        w.writerow(["總回收金額", rep.total_recovered])
        w.writerow(["股利收入總計", rep.total_dividend_income])
        w.writerow(["手續費合計", rep.total_fees])
        w.writerow(["交易稅合計", rep.total_taxes])
        w.writerow(["已實現損益", rep.realized_pl])
        if rep.current_price is not None:
            w.writerow(["目前市價", rep.current_price])
            w.writerow(["目前市值", rep.current_value])
            w.writerow(["未實現損益", rep.unrealized_pl])
            w.writerow(["未實現損益%", rep.unrealized_pl_pct if rep.unrealized_pl_pct is not None else "N/A"])
        w.writerow(["總損益", rep.total_pl])
        w.writerow(["總報酬率%", rep.total_roi_pct])

        w.writerow([])
        w.writerow([])
        w.writerow(["#", "日期", "類型", "價格", "股數", "金額", "手續費", "稅", "零成本觸發", "每股股利", "股利總額", "每千股配發", "額外股數"])
        for i, tx in enumerate(state.history, 1):
            w.writerow([
                i, tx.date, tx.action, tx.price, tx.shares,
                tx.total_amount, tx.fee, tx.tax, tx.zero_cost_triggered,
                tx.dividend_per_share, tx.dividend_total,
                tx.per_thousand_shares, tx.additional_shares,
            ])


def export_report_html(rep, state, filepath):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _tr(label, value):
        return f"      <tr><td>{label}</td><td>{value}</td></tr>"

    def _pl_row(label, value, pct=None):
        cls = "pos" if value > 0 else ("neg" if value < 0 else "")
        formatted = f"{value:+,.2f}"
        if pct is not None:
            formatted += f" ({pct:+.2f}%)"
        return f'      <tr><td>{label}</td><td class="{cls}">{formatted}</td></tr>'

    pl_rows = ""
    pl_rows += _tr("總投入成本", f"{rep.total_invested:,.2f}")
    pl_rows += _tr("總回收金額", f"{rep.total_recovered:,.2f}")
    pl_rows += _tr("股利收入總計", f"{rep.total_dividend_income:,.2f}")
    pl_rows += '<tr><td colspan="2"><hr></td></tr>'
    pl_rows += _tr("手續費合計", f"{rep.total_fees:,.2f}")
    pl_rows += _tr("交易稅合計", f"{rep.total_taxes:,.2f}")
    pl_rows += _pl_row("已實現損益", rep.realized_pl)
    if rep.current_price is not None:
        pl_rows += _tr("目前市價", f"{rep.current_price:,.2f}")
        pl_rows += _tr("目前市值", f"{rep.current_value:,.2f}")
        pl_rows += _pl_row("未實現損益", rep.unrealized_pl, rep.unrealized_pl_pct)
    pl_rows += '<tr><td colspan="2"><hr></td></tr>'
    pl_rows += _pl_row("總損益", rep.total_pl)
    pl_rows += _tr("總報酬率", f"{rep.total_roi_pct:+.2f}%")

    tx_rows = ""
    for i, tx in enumerate(state.history, 1):
        action_map = {
            "buy": "買入", "sell": "賣出", "dividend": "現金股利",
            "dividend_reinvest": "股利再投資", "stock_dividend": "股票股利",
        }
        tx_rows += f"""      <tr>
        <td>{i}</td>
        <td>{tx.date}</td>
        <td>{action_map.get(tx.action, tx.action)}</td>
        <td>{tx.price:,.2f}</td>
        <td>{tx.shares}</td>
        <td>{tx.total_amount:,.2f}</td>
        <td>{tx.fee if tx.fee else ""}</td>
        <td>{tx.tax if tx.tax else ""}</td>
      </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<title>股票損益報表</title>
<style>
  body {{ font-family: -apple-system, sans-serif; max-width: 800px; margin: 2em auto; padding: 0 1em; color: #333; }}
  h1 {{ font-size: 1.4em; border-bottom: 2px solid #2563eb; padding-bottom: .3em; }}
  h2 {{ font-size: 1.1em; color: #2563eb; margin-top: 1.5em; }}
  table {{ width: 100%; border-collapse: collapse; margin: .5em 0; }}
  th, td {{ padding: .4em .6em; text-align: left; border-bottom: 1px solid #eee; }}
  th {{ background: #f8fafc; font-weight: 600; }}
  td:last-child {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .pos {{ color: #16a34a; }}
  .neg {{ color: #dc2626; }}
  hr {{ border: none; border-top: 1px solid #ddd; margin: 0; }}
  .meta {{ color: #888; font-size: .85em; margin-bottom: 1em; }}
</style>
</head>
<body>
<h1>📊 股票損益報表</h1>
<p class="meta">產生時間：{now} | 持有股數：{rep.shares} 股</p>

<h2>📋 庫存概況</h2>
<table>
  <tr><th>項目</th><th>數值</th></tr>
  {_tr("持有股數", f"{rep.shares}")}
  {_tr("總成本", f"{rep.total_cost:,.2f}")}
  {_tr("平均成本", f"{rep.avg_cost:,.2f}")}
  {_tr("零成本狀態", "是" if rep.is_zero_cost else "否")}
</table>

<h2>💰 損益總覽</h2>
<table>
  <tr><th>項目</th><th>數值</th></tr>
  {pl_rows}
</table>

<h2>📝 交易明細</h2>
<table>
  <tr><th>#</th><th>日期</th><th>類型</th><th>價格</th><th>股數</th><th>金額</th><th>手續費</th><th>稅</th></tr>
  {tx_rows}
</table>
</body>
</html>"""

    p = Path(filepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
