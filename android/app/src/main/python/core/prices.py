import json
import re
import ssl
import time
import urllib.request
import urllib.error
from pathlib import Path

CACHE_TTL = 300
_CACHE = {}
_CACHE_PATH = None


def init_cache(cache_dir):
    global _CACHE_PATH, _CACHE
    _CACHE_PATH = Path(cache_dir) / "price_cache.json"
    _CACHE.clear()
    if _CACHE_PATH.exists():
        try:
            _CACHE.update(json.loads(_CACHE_PATH.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass


def _save_cache():
    if _CACHE_PATH:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_PATH.write_text(
            json.dumps(_CACHE, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _is_cache_valid(stock_code):
    entry = _CACHE.get(stock_code)
    if not entry:
        return False
    age = time.time() - entry.get("timestamp", 0)
    return age < CACHE_TTL


def _fetch_yahoo(stock_code):
    suffixes = [".TW", ".TWO"]
    for suffix in suffixes:
        symbol = f"{stock_code}{suffix}"
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
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
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError):
            continue
        try:
            result = data["chart"]["result"]
            if not result:
                continue
            meta = result[0]["meta"]
            price = meta["regularMarketPrice"]
            name = meta.get("longName") or meta.get("shortName") or ""
            return round(float(price), 2), name
        except (KeyError, IndexError, TypeError, ValueError):
            continue
    return None, None


def _resolve_name(stock_code):
    ctx = ssl.create_default_context()
    try:
        url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date=20260601&stockNo={stock_code}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        title = data.get("title", "")
        m = re.match(r"\d+年\d+月\s+\d+\s+(.+)", title)
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    try:
        ctx_noverify = ssl.create_default_context()
        ctx_noverify.check_hostname = False
        ctx_noverify.verify_mode = ssl.CERT_NONE
        url = f"https://goodinfo.tw/tw/ShowK_Chart.asp?STOCK_ID={stock_code}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10, context=ctx_noverify) as resp:
            html = resp.read().decode("utf-8")
        m = re.search(re.escape(stock_code) + r"\s+(.+?)\s*-\s*技術分析", html)
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    return ""


def fetch_price(stock_code):
    entry = _CACHE.get(stock_code)

    if _is_cache_valid(stock_code):
        name = entry.get("name", "")
        if name and not name.isascii():
            return entry["price"], name
        cn = _resolve_name(stock_code)
        if cn:
            _CACHE[stock_code]["name"] = cn
            _save_cache()
            return entry["price"], cn
        return entry["price"], name or ""

    cached_name = entry.get("name", "") if entry else ""
    price, yahoo_name = _fetch_yahoo(stock_code)
    if price is not None:
        name = cached_name
        if not name or name.isascii():
            cn = _resolve_name(stock_code)
            name = cn or yahoo_name
        _CACHE[stock_code] = {"price": price, "name": name, "timestamp": time.time()}
        _save_cache()
        return price, name
    return None, ""


def fetch_prices(stock_codes):
    return {code: fetch_price(code) for code in stock_codes}


def clear_cache():
    _CACHE.clear()
    if _CACHE_PATH and _CACHE_PATH.exists():
        _CACHE_PATH.unlink(missing_ok=True)
