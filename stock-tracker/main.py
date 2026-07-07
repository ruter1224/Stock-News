import os
import sys
from pathlib import Path
from core.models import Transaction
from core.config import Config
from core.portfolio import Portfolio
from core.calculator import apply_transaction
from core.report import generate_report, export_report_csv, export_report_html
from data.store import save_portfolio, load_portfolio
from data.importer import parse_trades_csv, export_trades_csv
from core.prices import init_cache as init_price_cache, fetch_prices, clear_cache as clear_price_cache

_data_dir_env = os.environ.get("STOCK_TRACKER_DATA_DIR")
if _data_dir_env:
    DATA_DIR = Path(_data_dir_env) / "data"
else:
    DATA_DIR = Path(__file__).parent / "data"


def cmd_holding_add(args):
    filepath = args.filepath or str(DATA_DIR / "state.json")
    portfolio = load_portfolio(filepath)
    cfg = _load_config(args)
    try:
        new_state = portfolio.add_init_holding(
            stock_code=args.stock,
            shares=args.shares,
            total_cost=args.cost,
            config=cfg,
            date_str=args.date,
        )
    except ValueError as e:
        print(f"錯誤：{e}")
        return
    save_portfolio(portfolio, filepath)
    print(f"[{args.stock}] 已設定初始持倉")
    _print_state(new_state, args.stock)


def cmd_holding_list(args):
    filepath = args.filepath or str(DATA_DIR / "state.json")
    portfolio = load_portfolio(filepath)
    codes = [c for c in portfolio.stock_codes
             if portfolio.get_state(c).history and portfolio.get_state(c).history[0].action == "init"]
    if not codes:
        print("  目前沒有使用 init 設定的持倉")
        return
    print(f"\n===== 初始持倉列表 =====")
    for code in sorted(codes):
        st = portfolio.get_state(code)
        print(f"  {code} | {st.shares:>5} 股 | 成本 {st.total_cost:>10,.2f} | 均價 {st.avg_cost:>8,.2f}")


def cmd_holding_remove(args):
    filepath = args.filepath or str(DATA_DIR / "state.json")
    portfolio = load_portfolio(filepath)
    if not args.confirm:
        print("請加上 --confirm 確認刪除")
        return
    if args.stock not in portfolio.stocks:
        print(f"{args.stock} 不存在於投資組合中")
        return
    portfolio.remove_stock(args.stock)
    save_portfolio(portfolio, filepath)
    print(f"已刪除 {args.stock} 的持倉")


def cmd_init(args):
    filepath = args.filepath or str(DATA_DIR / "state.json")
    save_portfolio(Portfolio(), filepath)
    print(f"已初始化空投資組合 -> {filepath}")


def cmd_add(args):
    filepath = args.filepath or str(DATA_DIR / "state.json")
    portfolio = load_portfolio(filepath)
    cfg = _load_config(args)
    tx = _parse_transaction(args)
    if not tx:
        return
    stock = args.stock or "0000"
    new_state = portfolio.add_transaction(stock, tx, cfg)
    save_portfolio(portfolio, filepath)
    print(f"[{stock}] 已套用交易：{args.action}")
    _print_state(new_state, stock)


def cmd_status(args):
    filepath = args.filepath or str(DATA_DIR / "state.json")
    portfolio = load_portfolio(filepath)
    stock = args.stock
    if stock:
        _print_state(portfolio.get_state(stock), stock)
    else:
        if not portfolio.stock_codes:
            print("  投資組合為空")
            return
        print(f"\n===== 投資組合 ({len(portfolio.stock_codes)} 檔) =====\n")
        for code in sorted(portfolio.stock_codes):
            st = portfolio.get_state(code)
            zc = "O" if st.is_zero_cost else "X"
            print(f"  {code} | {st.shares:>5} 股 | 成本 {st.total_cost:>10,.2f} | 均價 {st.avg_cost:>8,.2f} | 零成本[{zc}]")


def cmd_report(args):
    filepath = args.filepath or str(DATA_DIR / "state.json")
    portfolio = load_portfolio(filepath)
    fmt = (args.format or "text").lower()
    stock = args.stock
    price = args.price

    if args.auto_price and price is None:
        init_price_cache(str(DATA_DIR))
        codes = [stock] if stock else portfolio.stock_codes
        prices = fetch_prices(codes)
        if stock:
            price = prices.get(stock)
        else:
            _print_portfolio_summary_with_prices(portfolio, prices)
            return

    if stock:
        state = portfolio.get_state(stock)
        rep = generate_report(state, current_price=price)
        _output_report(rep, state, fmt, args.output, stock)
    else:
        _print_portfolio_summary(portfolio)


def cmd_import(args):
    filepath = args.filepath or str(DATA_DIR / "state.json")
    portfolio = load_portfolio(filepath)
    cfg = _load_config(args)
    portfolio, n, _ = parse_trades_csv(args.csv, portfolio, cfg)
    save_portfolio(portfolio, filepath)
    print(f"已匯入 {n} 筆交易 -> {filepath}")
    for code in sorted(portfolio.stock_codes):
        st = portfolio.get_state(code)
        print(f"  {code}: {st.shares} 股, 成本 {st.total_cost:,.2f}")


def cmd_export(args):
    filepath = args.filepath or str(DATA_DIR / "state.json")
    portfolio = load_portfolio(filepath)
    out = args.output or str(DATA_DIR / "trades_export.csv")
    n = export_trades_csv(portfolio, out)
    print(f"已匯出 {n} 檔股票的交易記錄 -> {out}")


def cmd_refresh(args):
    filepath = args.filepath or str(DATA_DIR / "state.json")
    portfolio = load_portfolio(filepath)
    if not portfolio.stock_codes:
        print("  投資組合為空")
        return
    init_price_cache(str(DATA_DIR))
    clear_price_cache()
    codes = [args.stock] if args.stock else portfolio.stock_codes
    print(f"  正在重新抓取 {len(codes)} 檔股價...")
    prices = fetch_prices(codes)
    ok = sum(1 for v in prices.values() if v is not None)
    print(f"  完成：{ok}/{len(codes)} 成功")
    _print_portfolio_summary_with_prices(portfolio, prices)


def cmd_list(args):
    filepath = args.filepath or str(DATA_DIR / "state.json")
    portfolio = load_portfolio(filepath)
    codes = portfolio.stock_codes
    if not codes:
        print("  投資組合為空")
        return
    print("  目前持有的股票代碼：")
    for code in sorted(codes):
        st = portfolio.get_state(code)
        print(f"    {code}  ({st.shares} 股)")


def _output_report(rep, state, fmt, output_path, stock=""):
    tag = stock or "0000"
    if fmt == "csv":
        out = output_path or str(DATA_DIR / f"report_{tag}.csv")
        export_report_csv(rep, state, out)
        print(f"已匯出 CSV 報表 -> {out}")
    elif fmt == "html":
        out = output_path or str(DATA_DIR / f"report_{tag}.html")
        export_report_html(rep, state, out)
        print(f"已匯出 HTML 報表 -> {out}")
    else:
        _print_report(rep, tag)


def _print_portfolio_summary(portfolio):
    print(f"\n===== 投資組合總覽 =====")
    if not portfolio.stock_codes:
        print("  空")
        print()
        return
    print(f"  代碼  | 股數  | 總成本       | 均價       | 零成本 | 投入成本     ")
    print(f"  {'─'*5} | {'─'*4} | {'─'*12} | {'─'*10} | {'─'*6} | {'─'*12}")
    for code in sorted(portfolio.stock_codes):
        st = portfolio.get_state(code)
        rep = generate_report(st)
        zc = "O" if st.is_zero_cost else "X"
        print(f"  {code:>5} | {st.shares:>4} | {st.total_cost:>10,.2f}  | {st.avg_cost:>8,.2f}  |   {zc}    | {rep.total_invested:>10,.2f}")


def _print_portfolio_summary_with_prices(portfolio, prices):
    print(f"\n===== 投資組合總覽 (含即時股價) =====")
    if not portfolio.stock_codes:
        print("  空")
        print()
        return
    sep = "─" * 64
    print(f"  代碼  | 股數  | 總成本       | 現價       | 市值         | 未實現損益   ")
    print(f"  {sep}")
    total_value = 0.0
    for code in sorted(portfolio.stock_codes):
        st = portfolio.get_state(code)
        price = prices.get(code)
        if price:
            value = round(price * st.shares, 2)
            unrealized = round(value - st.total_cost, 2)
            total_value += value
            print(f"  {code:>5} | {st.shares:>4} | {st.total_cost:>10,.2f} | {price:>8,.2f} | {value:>10,.2f} | {unrealized:>+10,.2f}")
        else:
            print(f"  {code:>5} | {st.shares:>4} | {st.total_cost:>10,.2f} | {'N/A':>8} | {'N/A':>10} | {'N/A':>10}")
    print(f"  {sep}")
    print(f"  {'總市值':>33} | {total_value:>10,.2f} |")


def _load_config(args):
    cfg = Config()
    fee_rate = getattr(args, "fee_rate", None)
    tax_rate = getattr(args, "tax_rate", None)
    if fee_rate is not None:
        cfg.fee_rate = fee_rate
    if tax_rate is not None:
        cfg.tax_rate_listed = tax_rate
    return cfg


def _parse_transaction(args):
    if args.action in ("buy", "dividend_reinvest"):
        return Transaction(
            date=args.date,
            action=args.action,
            price=args.price,
            shares=args.shares,
            total_amount=round(args.price * args.shares, 2),
        )
    elif args.action == "sell":
        return Transaction(
            date=args.date,
            action=args.action,
            price=args.price,
            shares=args.shares,
            total_amount=round(args.price * args.shares, 2),
        )
    elif args.action == "dividend":
        total = round(args.dividend_per_share * args.shares, 2)
        return Transaction(
            date=args.date,
            action="dividend",
            price=0,
            shares=0,
            dividend_per_share=args.dividend_per_share,
            dividend_total=total,
        )
    elif args.action == "stock_dividend":
        return Transaction(
            date=args.date,
            action="stock_dividend",
            price=0,
            shares=0,
            per_thousand_shares=args.per_thousand,
            additional_shares=args.additional,
        )
    else:
        print(f"不支援的交易類型：{args.action}", file=sys.stderr)
        return None


def _print_state(state, stock=""):
    tag = f"[{stock}] " if stock else ""
    print(f"  {tag}持有股數：{state.shares}")
    print(f"  {tag}總成本：{state.total_cost:.2f}")
    print(f"  {tag}平均成本：{state.avg_cost:.2f}")
    print(f"  {tag}零成本狀態：{'是' if state.is_zero_cost else '否'}")
    if state.history:
        print(f"  {tag}交易筆數：{len(state.history)}")


def _print_report(rep, tag=""):
    sep = "─" * 36
    hdr = f" [{tag}]" if tag else ""

    print(f"\n===== 庫存狀態{hdr} =====")
    print(f"  持有股數：{rep.shares}")
    print(f"  總成本：{rep.total_cost:,.2f}")
    print(f"  平均成本：{rep.avg_cost:,.2f}")
    print(f"  零成本狀態：{'是' if rep.is_zero_cost else '否'}")

    print(f"\n===== 損益總覽{hdr} =====")
    print(f"  總投入成本：{rep.total_invested:,.2f}")
    print(f"  總回收金額：{rep.total_recovered:,.2f}")
    print(f"  股利收入總計：{rep.total_dividend_income:,.2f}")
    print(f"  {sep}")
    print(f"  手續費合計：{rep.total_fees:,.2f}")
    print(f"  交易稅合計：{rep.total_taxes:,.2f}")
    print(f"  已實現損益：{_fmt_pl(rep.realized_pl)}")
    if rep.current_price is not None:
        print(f"  目前市價：{rep.current_price:,.2f}")
        print(f"  目前市值：{rep.current_value:,.2f}")
        print(f"  未實現損益：{_fmt_pl(rep.unrealized_pl)}", end="")
        if rep.unrealized_pl_pct is not None:
            print(f" ({rep.unrealized_pl_pct:+.2f}%)")
        else:
            print(" (N/A)")
    else:
        print(f"  未實現損益：(需提供市價)")
    print(f"  {sep}")
    print(f"  總損益：{_fmt_pl(rep.total_pl)}")
    if rep.total_roi_pct != 0 or rep.total_invested > 0:
        print(f"  總報酬率：{rep.total_roi_pct:+.2f}%")
    print()


def cmd_web(args):
    import os
    import webbrowser
    from web.app import create_app
    app = create_app()
    port = args.port or 5000
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        webbrowser.open(f"http://localhost:{port}")
    app.run(host="127.0.0.1", port=port, debug=args.debug)


def _dispatch_holding(args):
    dispatch = {
        "add": cmd_holding_add,
        "list": cmd_holding_list,
        "remove": cmd_holding_remove,
    }
    dispatch[args.holding_command](args)


def _fmt_pl(value):
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:,.2f}"


def main():
    import argparse

    parser = argparse.ArgumentParser(description="股票交易成本計算系統")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="初始化空投資組合")
    p_init.add_argument("--filepath", "-f", help="狀態檔案路徑")

    p_add = sub.add_parser("add", help="新增一筆交易")
    p_add.add_argument(
        "action",
        choices=["buy", "sell", "dividend", "dividend_reinvest", "stock_dividend"],
    )
    p_add.add_argument("--stock", required=True, help="股票代碼 (如 2330)")
    p_add.add_argument("--date", required=True, help="交易日期 (YYYY-MM-DD)")
    p_add.add_argument("--price", type=float, default=0, help="每股價格")
    p_add.add_argument("--shares", type=int, default=0, help="股數")
    p_add.add_argument("--dividend-per-share", type=float, help="每股股利 (現金股利)")
    p_add.add_argument("--per-thousand", type=int, help="股票股利每千股配發股數")
    p_add.add_argument("--additional", type=int, help="股票股利額外配發股數")
    p_add.add_argument("--fee-rate", type=float, help="手續費率 (覆寫預設)")
    p_add.add_argument("--tax-rate", type=float, help="交易稅率 (覆寫預設)")
    p_add.add_argument("--filepath", "-f", help="狀態檔案路徑")

    p_status = sub.add_parser("status", help="檢視庫存狀態")
    p_status.add_argument("--stock", "-s", help="股票代碼 (不指定則顯示全部)")
    p_status.add_argument("--filepath", "-f", help="狀態檔案路徑")

    p_report = sub.add_parser("report", help="產生損益報表")
    p_report.add_argument("--stock", "-s", help="股票代碼 (不指定則顯示投資組合總覽)")
    p_report.add_argument("--price", type=float, help="目前市價 (計算未實現損益)")
    p_report.add_argument("--auto-price", "-a", action="store_true", help="自動抓取即時股價 (需網路)")
    p_report.add_argument("--format", choices=["text", "csv", "html"], default="text", help="輸出格式")
    p_report.add_argument("--output", "-o", help="匯出檔案路徑")
    p_report.add_argument("--filepath", "-f", help="狀態檔案路徑")

    p_import = sub.add_parser("import", help="從 CSV 匯入交易記錄")
    p_import.add_argument("csv", help="CSV 檔案路徑")
    p_import.add_argument("--fee-rate", type=float, help="手續費率 (覆寫預設)")
    p_import.add_argument("--tax-rate", type=float, help="交易稅率 (覆寫預設)")
    p_import.add_argument("--filepath", "-f", help="狀態檔案路徑")

    p_export = sub.add_parser("export", help="匯出交易記錄為 CSV")
    p_export.add_argument("--output", "-o", help="CSV 輸出檔案路徑")
    p_export.add_argument("--filepath", "-f", help="狀態檔案路徑")

    p_refresh = sub.add_parser("refresh", help="重新抓取所有即時股價")
    p_refresh.add_argument("--stock", "-s", help="股票代碼 (不指定則全部重新抓取)")
    p_refresh.add_argument("--filepath", "-f", help="狀態檔案路徑")

    p_list = sub.add_parser("list", help="列出所有股票代碼")
    p_list.add_argument("--filepath", "-f", help="狀態檔案路徑")

    p_holding = sub.add_parser("holding", help="管理初始持倉")
    p_holding_sub = p_holding.add_subparsers(dest="holding_command", required=True)

    p_hold_add = p_holding_sub.add_parser("add", help="設定初始持倉")
    p_hold_add.add_argument("--stock", required=True, help="股票代碼 (如 2330)")
    p_hold_add.add_argument("--shares", required=True, type=int, help="持有股數")
    p_hold_add.add_argument("--cost", required=True, type=float, help="持有總成本")
    p_hold_add.add_argument("--date", help="初始日期 (YYYY-MM-DD，預設今天)")
    p_hold_add.add_argument("--filepath", "-f", help="狀態檔案路徑")

    p_hold_list = p_holding_sub.add_parser("list", help="列出所有初始持倉")
    p_hold_list.add_argument("--filepath", "-f", help="狀態檔案路徑")

    p_hold_remove = p_holding_sub.add_parser("remove", help="刪除初始持倉")
    p_hold_remove.add_argument("--stock", required=True, help="股票代碼")
    p_hold_remove.add_argument("--confirm", action="store_true", help="確認刪除")
    p_hold_remove.add_argument("--filepath", "-f", help="狀態檔案路徑")

    p_web = sub.add_parser("web", help="啟動網頁圖形介面 (Flask)")
    p_web.add_argument("--port", "-p", type=int, default=5000, help="監聽埠號 (預設 5000)")
    p_web.add_argument("--debug", "-d", action="store_true", help="除錯模式")

    args = parser.parse_args()
    dispatch = {
        "init": cmd_init,
        "add": cmd_add,
        "status": cmd_status,
        "report": cmd_report,
        "import": cmd_import,
        "export": cmd_export,
        "refresh": cmd_refresh,
        "list": cmd_list,
        "holding": _dispatch_holding,
        "web": cmd_web,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
