import pytest
import json
import time
from pathlib import Path
from core.news import (
    init_cache, fetch_market_news, get_news_page,
    refresh_news, get_cooldown_remaining, CACHE_TTL, REFRESH_COOLDOWN
)


def test_init_cache_creates_directory(tmp_path):
    cache_dir = str(tmp_path / "news")
    init_cache(cache_dir)
    assert Path(cache_dir).exists()


def test_get_news_page_returns_paginated_results(tmp_path):
    init_cache(str(tmp_path))
    page = get_news_page(page=1, per_page=10)
    assert "articles" in page
    assert "total" in page
    assert "page" in page
    assert "per_page" in page
    assert "total_pages" in page
    assert "last_refresh_at" in page
    assert "cooldown_remaining" in page
    assert len(page["articles"]) <= 10


def test_get_news_page_page_2(tmp_path):
    init_cache(str(tmp_path))
    page1 = get_news_page(page=1, per_page=20)
    page2 = get_news_page(page=2, per_page=20)
    assert page1["page"] == 1
    assert page2["page"] == 2
    if page1["total"] > 20:
        assert page2["articles"] != page1["articles"]


def test_refresh_news_cooldown(tmp_path):
    init_cache(str(tmp_path))
    result = refresh_news()
    assert "articles" in result or "error" in result
    result2 = refresh_news()
    if "articles" in result2:
        pass
    else:
        assert "error" in result2
        assert "cooldown_remaining" in result2


def test_get_cooldown_returns_zero_when_not_refreshed(tmp_path):
    init_cache(str(tmp_path))
    remaining = get_cooldown_remaining()
    assert remaining == 0


def test_cache_persists_articles(tmp_path):
    init_cache(str(tmp_path))
    page1 = get_news_page(page=1, per_page=100)
    total = page1["total"]
    page2 = get_news_page(page=1, per_page=100)
    assert page2["total"] == total
