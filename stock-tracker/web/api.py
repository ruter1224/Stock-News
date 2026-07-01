import os
from pathlib import Path
from flask import Blueprint, jsonify, request
from core.portfolio import Portfolio
from core.config import Config, is_etf_stock
from core.report import generate_report
from core.prices import init_cache as init_price_cache, fetch_prices, clear_cache as clear_price_cache
from data.store import save_portfolio, load_portfolio
from data.importer import parse_trades_csv, export_trades_csv
from core.models import Transaction
from core.history import init_history_dir, download_history, update_history, list_history_codes, history_exists
from core.backtest import single_stock_backtest, portfolio_backtest
from core.news import init_cache as init_news_cache, get_news_page, refresh_news

_data_dir_env = os.environ.get("STOCK_TRACKER_DATA_DIR")
if _data_dir_env:
    DATA_DIR = Path(_data_dir_env) / "data"
else:
    DATA_DIR = Path(__file__).parent.parent / "data"
STATE_FILE = str(DATA_DIR / "state.json")

if not DATA_DIR.exists():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
if not Path(STATE_FILE).exists():
    from core.portfolio import Portfolio as _P
    save_portfolio(_P(), STATE_FILE)

portfolio = load_portfolio(STATE_FILE)
cfg = Config()
init_history_dir(str(DATA_DIR))
init_news_cache(str(DATA_DIR))

api = Blueprint("api", __name__, url_prefix="/api")


def _save():
    save_portfolio(portfolio, STATE_FILE)


def _stock_summary(code):
    state = portfolio.get_state(code)
    price, name = _get_cached_price(code)
    rep = generate_report(state, current_price=price)
    return {
        "code": code,
        "name": name,
        "type": "ETF" if is_etf_stock(code) else "個股",
        "shares": state.shares,
        "total_cost": round(state.total_cost, 2),
        "avg_cost": round(state.avg_cost, 2),
        "current_price": price,
        "market_value": round((price or 0) * state.shares, 2) if price else 0,
        "unrealized_pl": round(rep.unrealized_pl, 2) if price else 0,
        "unrealized_pl_pct": round(rep.unrealized_pl_pct, 2) if rep.unrealized_pl_pct is not None else 0,
        "is_zero_cost": state.is_zero_cost,
        "archived": state.archived,
    }


def _get_cached_price(code):
    """Read price from cache without triggering a fetch."""
    from core.prices import _CACHE
    entry = _CACHE.get(code)
    if entry:
        return entry.get("price"), entry.get("name", "")
    return None, ""


def fetch_price_safe(code):
    try:
        result = fetch_prices([code]).get(code)
        if result is None:
            return None, ""
        return result
    except Exception:
        return None, ""


@api.route("/portfolio")
def get_portfolio():
    codes = sorted(portfolio.active_stock_codes)
    stocks = [_stock_summary(c) for c in codes]
    total_value = sum(s["market_value"] for s in stocks)
    total_cost = sum(s["total_cost"] for s in stocks)
    total_pl = total_value - total_cost
    roi = (total_pl / total_cost * 100) if total_cost > 0 else 0.0
    zc_count = sum(1 for s in stocks if s["is_zero_cost"])
    return jsonify({
        "stocks": stocks,
        "count": len(stocks),
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_pl": round(total_pl, 2),
        "total_roi": round(roi, 2),
        "zc_count": zc_count,
    })


@api.route("/portfolio/archived")
def get_archived_portfolio():
    codes = sorted(portfolio.archived_stock_codes)
    stocks = [_stock_summary(c) for c in codes]
    return jsonify({
        "stocks": stocks,
        "count": len(stocks),
    })


@api.route("/portfolio/<code>")
def get_stock_detail(code):
    state = portfolio.get_state(code)
    if not state or not state.history:
        return jsonify({"error": "找不到該股票"}), 404
    price, name = _get_cached_price(code)
    rep = generate_report(state, current_price=price)
    history = []
    for tx in state.history:
        labels = {"buy": "買入", "sell": "賣出", "dividend": "股利",
                  "dividend_reinvest": "再投資", "stock_dividend": "股票股利",
                  "init": "初始"}
        history.append({
            "date": tx.date,
            "action": labels.get(tx.action, tx.action),
            "price": tx.price,
            "shares": tx.shares,
            "total_amount": tx.total_amount,
            "fee": tx.fee,
            "tax": tx.tax,
            "remark": tx.remark,
        })
    return jsonify({
        "code": code,
        "name": name,
        "type": "ETF" if is_etf_stock(code) else "個股",
        "shares": state.shares,
        "total_cost": round(state.total_cost, 2),
        "avg_cost": round(state.avg_cost, 2),
        "current_price": price,
        "market_value": round((price or 0) * state.shares, 2) if price else 0,
        "unrealized_pl": round(rep.unrealized_pl, 2) if price else 0,
        "unrealized_pl_pct": round(rep.unrealized_pl_pct, 2) if rep.unrealized_pl_pct is not None else 0,
        "is_zero_cost": state.is_zero_cost,
        "history": history,
    })


@api.route("/holdings", methods=["POST"])
def add_holding():
    data = request.get_json()
    code = data.get("code", "").strip()
    if not code:
        return jsonify({"error": "請輸入股票代碼"}), 400
    try:
        shares = int(data["shares"])
        total_cost = float(data["total_cost"])
        date_str = data.get("date", "")
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "請輸入有效的數值"}), 400
    if shares <= 0 or total_cost <= 0:
        return jsonify({"error": "股數與成本必須大於 0"}), 400
    try:
        portfolio.add_init_holding(code, shares, total_cost, cfg, date_str=date_str or None)
        _save()
        return jsonify({"message": f"已設定 {code} 的初始持倉", "code": code})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@api.route("/transactions", methods=["POST"])
def add_transaction():
    data = request.get_json()
    code = data.get("code", "").strip()
    action = data.get("action", "")
    if not code or not action:
        return jsonify({"error": "缺少必要參數"}), 400
    try:
        date_str = data.get("date", "")
        if action == "buy":
            price = float(data["price"])
            shares = int(data["shares"])
            total = round(price * shares, 2)
            if "total_paid" in data:
                fee = round(float(data["total_paid"]) - total, 2)
            else:
                fee = float(data.get("fee", 0))
            tx = Transaction(date=date_str, action="buy", price=price, shares=shares,
                             total_amount=total, fee=fee, tax=0.0)
        elif action == "sell":
            price = float(data["price"])
            shares = int(data["shares"])
            total = round(price * shares, 2)
            if "total_received" in data:
                tax = round(total - float(data["total_received"]), 2)
                fee = 0.0
            else:
                fee = float(data.get("fee", 0))
                tax = float(data.get("tax", 0))
            tx = Transaction(date=date_str, action="sell", price=price, shares=shares,
                             total_amount=total, fee=fee, tax=tax)
        elif action == "dividend":
            ttl = float(data["total"])
            tx = Transaction(date=date_str, action="dividend", price=0.0, shares=0,
                             total_amount=ttl, dividend_total=ttl, fee=0.0, tax=0.0)
        elif action == "dividend_reinvest":
            price = float(data["price"])
            shares = int(data["shares"])
            total = round(price * shares, 2)
            if "total_paid" in data:
                fee = round(float(data["total_paid"]) - total, 2)
            else:
                fee = 0.0
            tx = Transaction(date=date_str, action="dividend_reinvest", price=price,
                             shares=shares, total_amount=total, fee=fee, tax=0.0)
        elif action == "stock_dividend":
            shares = int(data["shares"])
            tx = Transaction(date=date_str, action="stock_dividend", price=0.0,
                             shares=0, total_amount=0.0, fee=0.0, tax=0.0,
                             additional_shares=shares)
        else:
            return jsonify({"error": f"不支援的交易類型: {action}"}), 400
    except (KeyError, ValueError, TypeError) as e:
        return jsonify({"error": f"請輸入有效的數值: {e}"}), 400

    try:
        portfolio.add_transaction(code, tx, cfg)
        _save()
        return jsonify({"message": f"{code} 已套用 {action}", "code": code})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@api.route("/portfolio/<code>", methods=["DELETE"])
def delete_stock(code):
    if code not in portfolio.stocks:
        return jsonify({"error": f"找不到 {code}"}), 404
    portfolio.remove_stock(code)
    _save()
    return jsonify({"message": f"已刪除 {code}"})


@api.route("/portfolio/<code>/transactions/<int:index>", methods=["DELETE"])
def delete_transaction(code, index):
    state = portfolio.get_state(code)
    if not state.history:
        return jsonify({"error": "找不到該股票或無交易紀錄"}), 404
    try:
        portfolio.remove_transaction(code, index, cfg)
        _save()
        return jsonify({"message": f"已刪除第 {index} 筆交易"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@api.route("/prices/refresh", methods=["POST"])
def refresh_prices():
    codes = portfolio.stock_codes
    if not codes:
        return jsonify({"error": "投資組合為空"}), 400
    init_price_cache(str(DATA_DIR))
    prices = fetch_prices(codes)
    ok = sum(1 for v in prices.values() if v[0] is not None)
    return jsonify({"message": f"成功更新 {ok}/{len(codes)} 檔股價", "ok": ok, "total": len(codes)})


@api.route("/config")
def get_config():
    return jsonify({
        "fee_rate": cfg.fee_rate,
        "tax_rate_listed": cfg.tax_rate_listed,
        "tax_rate_otc": cfg.tax_rate_otc,
        "tax_rate_etf": cfg.tax_rate_etf,
        "reinvest_mode": cfg.reinvest_mode,
    })


@api.route("/config", methods=["PUT"])
def update_config():
    data = request.get_json()
    try:
        cfg.fee_rate = float(data.get("fee_rate", cfg.fee_rate))
        cfg.tax_rate_listed = float(data.get("tax_rate_listed", cfg.tax_rate_listed))
        cfg.tax_rate_otc = float(data.get("tax_rate_otc", cfg.tax_rate_otc))
        cfg.tax_rate_etf = float(data.get("tax_rate_etf", cfg.tax_rate_etf))
        if "reinvest_mode" in data:
            cfg.reinvest_mode = data["reinvest_mode"]
        return jsonify({"message": "設定已更新"})
    except ValueError:
        return jsonify({"error": "請輸入有效的數值"}), 400


@api.route("/cache/clear", methods=["POST"])
def clear_cache():
    try:
        clear_price_cache()
        return jsonify({"message": "股價快取已清除"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route("/import/csv", methods=["POST"])
def import_csv():
    if "file" not in request.files:
        return jsonify({"error": "請上傳 CSV 檔案"}), 400
    file = request.files["file"]
    if not file.filename.endswith(".csv"):
        return jsonify({"error": "僅支援 CSV 格式"}), 400
    try:
        csv_path = str(DATA_DIR / "_upload_temp.csv")
        file.save(csv_path)
        global portfolio
        portfolio, n = parse_trades_csv(csv_path, portfolio, cfg)
        Path(csv_path).unlink(missing_ok=True)
        _save()
        return jsonify({"message": f"已匯入 {n} 筆交易"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route("/export/csv", methods=["GET"])
def export_csv():
    try:
        out = str(DATA_DIR / "trades_export.csv")
        n = export_trades_csv(portfolio, out)
        return jsonify({"message": f"已匯出 {n} 檔股票", "path": out})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route("/portfolio/summary")
def get_summary():
    codes = sorted(portfolio.stock_codes)
    items = []
    for code in codes:
        state = portfolio.get_state(code)
        price, _ = fetch_price_safe(code)
        val = (price or 0) * state.shares if price else 0
        items.append({
            "code": code,
            "type": "ETF" if is_etf_stock(code) else "stock",
            "label": "ETF" if is_etf_stock(code) else "個股",
            "shares": state.shares,
            "market_value": round(val, 2),
            "zero_cost": state.is_zero_cost,
        })
    return jsonify(items)


# ====== News ======

@api.route("/news")
def get_news():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    per_page = min(per_page, 50)
    return jsonify(get_news_page(page=page, per_page=per_page))


@api.route("/news/refresh", methods=["POST"])
def refresh_news_api():
    result = refresh_news()
    if "error" in result:
        return jsonify(result), 429
    return jsonify(result)


# ====== Backtest ======

@api.route("/backtest/download-history", methods=["POST"])
def backtest_download_history():
    codes = portfolio.stock_codes
    if not codes:
        return jsonify({"error": "投資組合為空"}), 400
    codes.append("^TWII")
    results = {}
    for code in codes:
        try:
            n = download_history(code, years=5)
            results[code] = f"{n} 筆"
        except Exception as e:
            results[code] = f"錯誤: {e}"
    return jsonify({"message": f"已下載 {len(codes)} 檔歷史資料", "results": results})


@api.route("/backtest/history-status")
def backtest_history_status():
    codes = portfolio.stock_codes
    status = {}
    for code in codes:
        status[code] = history_exists(code)
    status["^TWII"] = history_exists("^TWII")
    return jsonify(status)


@api.route("/backtest/stock/<code>")
def backtest_single(code):
    years = request.args.get("years", 5, type=int)
    state = portfolio.get_state(code)
    if not state or not state.history:
        return jsonify({"error": "找不到該股票或無交易紀錄"}), 404
    if not history_exists(code):
        try:
            download_history(code, years=years)
        except Exception as e:
            return jsonify({"error": f"下載歷史資料失敗: {e}"}), 500
    if not history_exists("^TWII"):
        try:
            download_history("^TWII", years=years)
        except Exception as e:
            pass
    result = single_stock_backtest(code, state, years=years)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@api.route("/backtest/portfolio")
def backtest_portfolio():
    years = request.args.get("years", 5, type=int)
    if not portfolio.stock_codes:
        return jsonify({"error": "投資組合為空"}), 400
    missing = [c for c in portfolio.stock_codes if not history_exists(c)]
    if missing:
        return jsonify({"error": f"以下股票尚無歷史資料，請先下載: {', '.join(missing)}", "missing": missing}), 400
    if not history_exists("^TWII"):
        try:
            download_history("^TWII", years=years)
        except Exception:
            pass
    result = portfolio_backtest(portfolio, years=years)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)
