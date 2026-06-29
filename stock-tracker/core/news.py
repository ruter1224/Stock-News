import json
import time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError
from xml.etree import ElementTree as ET

CACHE_TTL = 1800
REFRESH_COOLDOWN = 1200
PER_PAGE = 20

_CACHE_PATH = None
_CACHE = None

# 台灣主要市場標的（用於 RSS 彙整頭條新聞）
_MARKET_SYMBOLS = [
    "2330.TW", "2317.TW", "2454.TW", "2308.TW",
    "2884.TW", "2881.TW", "2002.TW", "2412.TW",
    "1301.TW", "3008.TW",
]


def init_cache(cache_dir):
    global _CACHE_PATH, _CACHE
    _CACHE_PATH = Path(cache_dir) / "news_cache.json"
    _CACHE = {"articles": [], "last_refresh_at": 0, "cached_at": 0, "total": 0}
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if _CACHE_PATH.exists():
        try:
            data = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
            _CACHE.update(data)
        except (json.JSONDecodeError, OSError):
            pass


def _save_cache():
    if _CACHE_PATH:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_PATH.write_text(
            json.dumps(_CACHE, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _is_cache_valid():
    now = time.time()
    return (now - _CACHE.get("cached_at", 0)) < CACHE_TTL and len(_CACHE.get("articles", [])) > 0


def _is_cooldown():
    now = time.time()
    last = _CACHE.get("last_refresh_at", 0)
    return (now - last) < REFRESH_COOLDOWN


def _fetch_rss_news(symbol):
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
    req = Request(url, headers={
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    })
    try:
        with urlopen(req, timeout=10) as resp:
            root = ET.fromstring(resp.read().decode("utf-8"))
            articles = []
            for item in root.findall(".//item"):
                title = item.findtext("title", "")
                desc = item.findtext("description", "")
                link = item.findtext("link", "")
                pub_date = item.findtext("pubDate", "")
                articles.append({
                    "title": title,
                    "summary": desc,
                    "url": link,
                    "source": "Yahoo Finance",
                    "published": pub_date,
                    "related_stocks": [symbol.replace(".TW", "")],
                })
            return articles
    except (URLError, OSError, ET.ParseError):
        return []


def _fetch_market_news():
    seen = set()
    all_articles = []
    for symbol in _MARKET_SYMBOLS:
        articles = _fetch_rss_news(symbol)
        for a in articles:
            key = a["url"]
            if key not in seen:
                seen.add(key)
                all_articles.append(a)
    all_articles.sort(key=lambda a: a.get("published", ""), reverse=True)
    return all_articles


def fetch_market_news():
    if _is_cache_valid():
        return _CACHE.get("articles", [])
    articles = _fetch_market_news()
    _CACHE["articles"] = articles
    _CACHE["total"] = len(articles)
    _CACHE["cached_at"] = time.time()
    _save_cache()
    return articles


def get_news_page(page=1, per_page=20):
    articles = fetch_market_news()
    total = len(articles)
    total_pages = max(1, (total + per_page - 1) // per_page)
    start = (page - 1) * per_page
    end = start + per_page
    page_articles = articles[start:end]
    return {
        "articles": page_articles,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "last_refresh_at": _CACHE.get("last_refresh_at", 0),
        "cooldown_remaining": get_cooldown_remaining(),
    }


def get_cooldown_remaining():
    if not _is_cooldown():
        return 0
    last = _CACHE.get("last_refresh_at", 0)
    return int(REFRESH_COOLDOWN - (time.time() - last))


def refresh_news():
    if _is_cooldown():
        remaining = get_cooldown_remaining()
        return {"error": f"冷卻中，請於 {remaining // 60} 分鐘後再試", "cooldown_remaining": remaining}
    articles = _fetch_market_news()
    _CACHE["articles"] = articles
    _CACHE["total"] = len(articles)
    _CACHE["last_refresh_at"] = time.time()
    _CACHE["cached_at"] = time.time()
    _save_cache()
    return get_news_page(page=1)
