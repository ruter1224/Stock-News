import csv
import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

HISTORY_DIR = None


def init_history_dir(data_dir):
    global HISTORY_DIR
    HISTORY_DIR = Path(data_dir) / "history"
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def _history_path(code):
    return HISTORY_DIR / f"{code}.csv"


def _yahoo_symbols(code):
    if code == "^TWII":
        return ["^TWII"]
    return [f"{code}.TW", f"{code}.TWO"]


def _fetch_yahoo_chart(code, period="5y", interval="1d"):
    last_err = None
    for symbol in _yahoo_symbols(code):
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={period}&interval={interval}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError) as e:
            last_err = e
            continue

        result = data.get("chart", {}).get("result")
        if not result:
            last_err = RuntimeError(f"Yahoo API 無資料 ({symbol})")
            continue

        timestamps = result[0].get("timestamp", [])
        closes = result[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
        if not timestamps or not closes:
            last_err = RuntimeError(f"Yahoo API 回傳空資料 ({symbol})")
            continue

        rows = []
        for ts, close in zip(timestamps, closes):
            if close is None:
                continue
            dt = datetime.fromtimestamp(ts)
            date_str = dt.strftime("%Y-%m-%d")
            rows.append((date_str, round(float(close), 2)))

        rows.sort(key=lambda r: r[0])
        return rows

    raise RuntimeError(f"Yahoo API 請求失敗 ({code}): {last_err}")


def _period_from_years(years):
    if years <= 0.25:
        return "1mo"
    if years <= 1:
        return "1y"
    if years <= 2:
        return "2y"
    if years <= 5:
        return "5y"
    if years <= 10:
        return "10y"
    return "max"


def download_history(code, years=5):
    period = _period_from_years(years)
    rows = _fetch_yahoo_chart(code, period=period)
    path = _history_path(code)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["date", "close"])
        w.writerows(rows)
    return len(rows)


def update_history(code):
    path = _history_path(code)
    if not path.exists():
        return download_history(code, years=5)

    with open(path, "r", encoding="utf-8-sig") as f:
        reader = list(csv.DictReader(f))
    if not reader:
        return download_history(code, years=5)

    last_date_str = reader[-1]["date"]
    last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
    days_since = (datetime.now() - last_date).days + 5

    if days_since <= 1:
        return len(reader)

    if days_since <= 90:
        period = "3mo"
    elif days_since <= 365:
        period = "1y"
    else:
        period = "5y"

    new_rows = _fetch_yahoo_chart(code, period=period)
    merged = {row[0]: row[1] for row in reader}
    last_ts = last_date_str
    for date_str, close in new_rows:
        if date_str > last_ts:
            merged[date_str] = close

    sorted_rows = sorted(merged.items(), key=lambda x: x[0])
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["date", "close"])
        w.writerows(sorted_rows)
    return len(sorted_rows)


def get_history(code, start=None, end=None):
    path = _history_path(code)
    if not path.exists():
        return []
    rows = []
    with open(path, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            d = row["date"]
            if start and d < start:
                continue
            if end and d > end:
                continue
            rows.append({"date": d, "close": float(row["close"])})
    return rows


def get_history_price_map(code):
    return {r["date"]: r["close"] for r in get_history(code)}


def list_history_codes():
    if not HISTORY_DIR or not HISTORY_DIR.exists():
        return []
    return sorted(
        p.stem for p in HISTORY_DIR.iterdir() if p.suffix == ".csv"
    )


def history_exists(code):
    path = _history_path(code)
    return path.exists()
