import math
from datetime import datetime, timedelta

from core.history import get_history_price_map, get_history


def _process_daily(transactions, price_map, benchmark_map):
    tx_by_date = {}
    for tx in transactions:
        tx_by_date.setdefault(tx.date, []).append(tx)

    sorted_dates = sorted(price_map.keys())
    if not sorted_dates:
        return [], [], [], [], [], []

    # Walk through first transaction to last available price date
    first_tx_date = min(tx.date for tx in transactions) if transactions else sorted_dates[0]
    start_idx = 0
    for i, d in enumerate(sorted_dates):
        if d >= first_tx_date:
            start_idx = i
            break

    dates_out = []
    values = []
    costs = []
    bench_vals = []
    rets = []
    dds = []

    shares = 0
    total_cost = 0.0
    peak_value = 0.0
    started = False

    for d in sorted_dates[start_idx:]:
        if d in tx_by_date:
            for tx in tx_by_date[d]:
                if tx.action == "init":
                    shares += tx.shares
                    total_cost += tx.total_amount
                elif tx.action == "buy":
                    shares += tx.shares
                    total_cost += tx.total_amount + tx.fee
                elif tx.action == "sell":
                    if shares > 0:
                        ratio = tx.shares / shares
                        total_cost -= total_cost * ratio
                    shares -= tx.shares
                elif tx.action == "dividend":
                    pass
                elif tx.action == "dividend_reinvest":
                    shares += tx.shares
                    total_cost += tx.total_amount
                elif tx.action == "stock_dividend":
                    shares += tx.additional_shares

        close = price_map.get(d)
        if close is None:
            continue

        if shares > 0:
            started = True
        if not started:
            continue

        market_value = round(shares * close, 2)
        if total_cost > 0:
            ret = round((market_value - total_cost) / total_cost * 100, 2)
        else:
            ret = 0.0

        if market_value > peak_value:
            peak_value = market_value
        dd = round((market_value - peak_value) / peak_value * 100, 2) if peak_value > 0 else 0.0

        bench_val = benchmark_map.get(d)
        dates_out.append(d)
        values.append(market_value)
        costs.append(round(total_cost, 2))
        rets.append(ret)
        dds.append(dd)
        bench_vals.append(bench_val)

    return dates_out, values, costs, rets, dds, bench_vals


def _normalize_benchmark(benchmark_vals):
    first = next((b for b in benchmark_vals if b is not None), None)
    if first is None or first == 0:
        return [None] * len(benchmark_vals)
    return [round(b / first * 100, 2) if b is not None else None for b in benchmark_vals]


def _align_benchmark(benchmark_vals, portfolio_vals):
    first_p = next((v for v in portfolio_vals if v and v > 0), None)
    first_b = next((b for b in benchmark_vals if b is not None and b > 0), None)
    if first_p is None or first_b is None:
        return benchmark_vals
    ratio = first_p / first_b
    return [round(b * ratio, 2) if b is not None else None for b in benchmark_vals]


def single_stock_backtest(code, state, years=5):
    price_map = get_history_price_map(code)
    if not price_map:
        return {"error": f"無歷史資料 ({code})"}

    benchmark_map = get_history_price_map("^TWII")

    tx_list = sorted(state.history, key=lambda t: t.date)
    if not tx_list:
        return {"error": "無交易紀錄"}

    dates, values, costs, rets, dds, bench_raw = _process_daily(
        tx_list, price_map, benchmark_map
    )
    if not dates:
        return {"error": "回測無結果"}

    first_val = next((v for v in values if v > 0), None)
    last_val = values[-1] if values else 0
    first_cost = next((c for c in costs if c > 0), 0)
    last_cost = costs[-1] if costs else 0

    start_str = dates[0]
    end_str = dates[-1]
    days = (datetime.strptime(end_str, "%Y-%m-%d") - datetime.strptime(start_str, "%Y-%m-%d")).days
    years_span = max(days / 365.25, 0.5)

    total_return = round((last_val - first_cost) / first_cost * 100, 2) if first_cost > 0 else 0.0
    cagr = 0.0
    if first_cost > 0 and last_val > 0 and years_span >= 0.5:
        ratio = last_val / first_cost
        try:
            cagr = round((ratio ** (1 / years_span) - 1), 6) * 100
        except (OverflowError, ValueError):
            cagr = 0.0

    max_dd = round(min(dds), 2) if dds else 0.0

    daily_rets = []
    prev_v = None
    for v in values:
        if prev_v is not None and prev_v > 0:
            daily_rets.append((v - prev_v) / prev_v)
        prev_v = v
    if daily_rets:
        avg_daily_ret = sum(daily_rets) / len(daily_rets)
        variance = sum((r - avg_daily_ret) ** 2 for r in daily_rets) / len(daily_rets)
        daily_vol = math.sqrt(variance)
        annual_vol = round(daily_vol * math.sqrt(252) * 100, 2)
        annual_ret = round(((1 + avg_daily_ret) ** 252 - 1) * 100, 2)
        sharpe = round((annual_ret - 2.0) / annual_vol, 2) if annual_vol > 0 else 0.0
    else:
        annual_vol = 0.0
        annual_ret = 0.0
        sharpe = 0.0

    bench_aligned = _align_benchmark(bench_raw, values)
    bench_first = next((b for b in bench_aligned if b is not None), None)
    bench_last = next((b for b in reversed(bench_aligned) if b is not None), None)
    bench_return = round((bench_last - bench_first) / bench_first * 100, 2) if bench_first and bench_last else 0.0

    return {
        "dates": dates,
        "portfolio_values": values,
        "cost_basis": costs,
        "returns_pct": rets,
        "drawdowns": dds,
        "benchmark_values": bench_aligned,
        "metrics": {
            "start_date": start_str,
            "end_date": end_str,
            "start_value": first_cost,
            "end_value": last_val,
            "total_return": total_return,
            "cagr": cagr,
            "max_drawdown": max_dd,
            "annual_volatility": annual_vol,
            "sharpe_ratio": sharpe,
            "benchmark_return": bench_return,
        },
    }


def portfolio_backtest(portfolio, years=5):
    codes = sorted(portfolio.stock_codes)
    if not codes:
        return {"error": "投資組合為空"}

    benchmark_map = get_history_price_map("^TWII")

    all_price_maps = {}
    for code in codes:
        pm = get_history_price_map(code)
        if pm:
            all_price_maps[code] = pm

    if not all_price_maps:
        return {"error": "無歷史資料，請先下載"}

    all_dates = sorted(set(
        d for pm in all_price_maps.values() for d in pm.keys()
    ))
    if not all_dates:
        return {"error": "無歷史資料"}

    tx_by_code = {}
    for code in codes:
        state = portfolio.get_state(code)
        if state.history:
            tx_by_code[code] = list(state.history)

    earliest_tx = None
    for code, txs in tx_by_code.items():
        for tx in txs:
            if earliest_tx is None or tx.date < earliest_tx:
                earliest_tx = tx.date

    if earliest_tx is None:
        return {"error": "無交易紀錄"}

    start_idx = 0
    for i, d in enumerate(all_dates):
        if d >= earliest_tx:
            start_idx = i
            break

    dates_out = []
    values = []
    costs = []
    dds = []
    rets = []
    bench_vals = []

    shares = {code: 0 for code in codes}
    total_cost = {code: 0.0 for code in codes}
    peak_value = 0.0
    started = False

    tx_by_date_code = {}
    for code, txs in tx_by_code.items():
        for tx in txs:
            tx_by_date_code.setdefault(tx.date, {}).setdefault(code, []).append(tx)

    for d in all_dates[start_idx:]:
        if d in tx_by_date_code:
            for code, txs in tx_by_date_code[d].items():
                for tx in txs:
                    s = shares[code]
                    if tx.action == "init":
                        shares[code] = s + tx.shares
                        total_cost[code] += tx.total_amount
                    elif tx.action == "buy":
                        shares[code] = s + tx.shares
                        total_cost[code] += tx.total_amount + tx.fee
                    elif tx.action == "sell":
                        if s > 0:
                            ratio = tx.shares / s
                            total_cost[code] -= total_cost[code] * ratio
                        shares[code] = s - tx.shares
                    elif tx.action == "dividend_reinvest":
                        shares[code] = s + tx.shares
                        total_cost[code] += tx.total_amount
                    elif tx.action == "stock_dividend":
                        shares[code] = s + tx.additional_shares

        total_shares = sum(shares.values())
        if total_shares > 0:
            started = True
        if not started:
            continue

        market_value = 0.0
        total_cost_sum = 0.0
        for code in codes:
            close = all_price_maps[code].get(d)
            if close is not None:
                market_value += shares[code] * close
            total_cost_sum += total_cost[code]
        market_value = round(market_value, 2)

        if market_value > peak_value:
            peak_value = market_value
        dd = round((market_value - peak_value) / peak_value * 100, 2) if peak_value > 0 else 0.0

        ret = round((market_value - total_cost_sum) / total_cost_sum * 100, 2) if total_cost_sum > 0 else 0.0

        bench_val = benchmark_map.get(d)
        dates_out.append(d)
        values.append(market_value)
        costs.append(round(total_cost_sum, 2))
        dds.append(dd)
        rets.append(ret)
        bench_vals.append(bench_val)

    if not dates_out:
        return {"error": "回測無結果"}

    first_cost = next((c for c in costs if c > 0), 0)
    last_val = values[-1]

    start_str = dates_out[0]
    end_str = dates_out[-1]
    days = (datetime.strptime(end_str, "%Y-%m-%d") - datetime.strptime(start_str, "%Y-%m-%d")).days
    years_span = max(days / 365.25, 0.5)

    total_return = round((last_val - first_cost) / first_cost * 100, 2) if first_cost > 0 else 0.0
    cagr = 0.0
    if first_cost > 0 and last_val > 0 and years_span >= 0.5:
        ratio = last_val / first_cost
        try:
            cagr = round((ratio ** (1 / years_span) - 1), 6) * 100
        except (OverflowError, ValueError):
            cagr = 0.0
    max_dd = round(min(dds), 2) if dds else 0.0

    daily_rets = []
    prev_v = None
    for v in values:
        if prev_v is not None and prev_v > 0:
            daily_rets.append((v - prev_v) / prev_v)
        prev_v = v
    if daily_rets:
        avg = sum(daily_rets) / len(daily_rets)
        variance = sum((r - avg) ** 2 for r in daily_rets) / len(daily_rets)
        daily_vol = math.sqrt(variance)
        annual_vol = round(daily_vol * math.sqrt(252) * 100, 2)
        annual_ret = round(((1 + avg) ** 252 - 1) * 100, 2)
        sharpe = round((annual_ret - 2.0) / annual_vol, 2) if annual_vol > 0 else 0.0
    else:
        annual_vol = 0.0
        sharpe = 0.0

    bench_aligned = _align_benchmark(bench_vals, values)
    bench_first = next((b for b in bench_aligned if b is not None), None)
    bench_last = next((b for b in reversed(bench_aligned) if b is not None), None)
    bench_return = round((bench_last - bench_first) / bench_first * 100, 2) if bench_first and bench_last else 0.0

    positions = []
    total_mv = sum(
        shares[c] * next((v for d, v in all_price_maps[c].items() if d == dates_out[-1]), 0)
        for c in codes
    )
    for c in codes:
        last_close = all_price_maps[c].get(dates_out[-1])
        if last_close and total_mv > 0:
            mv = shares[c] * last_close
            positions.append({
                "code": c,
                "weight_pct": round(mv / total_mv * 100, 1),
            })

    return {
        "dates": dates_out,
        "portfolio_values": values,
        "cost_basis": costs,
        "returns_pct": rets,
        "drawdowns": dds,
        "benchmark_values": bench_aligned,
        "metrics": {
            "start_date": start_str,
            "end_date": end_str,
            "start_value": first_cost,
            "end_value": last_val,
            "total_return": total_return,
            "cagr": cagr,
            "max_drawdown": max_dd,
            "annual_volatility": annual_vol,
            "sharpe_ratio": sharpe,
            "benchmark_return": bench_return,
        },
        "positions": positions,
    }
