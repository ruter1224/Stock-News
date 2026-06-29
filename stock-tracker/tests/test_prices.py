import time
import json
from core.prices import init_cache, fetch_price, clear_cache, _CACHE, _CACHE_PATH, CACHE_TTL


class TestPriceCache:
    def setup_method(self):
        clear_cache()

    def test_cache_hit(self, tmp_path):
        init_cache(str(tmp_path))
        _CACHE["2330"] = {"price": 950.0, "timestamp": time.time()}
        price = fetch_price("2330")
        assert price[0] == 950.0

    def test_cache_expiry_refetches(self, tmp_path):
        init_cache(str(tmp_path))
        old = time.time() - CACHE_TTL - 10
        _CACHE["2330"] = {"price": 950.0, "timestamp": old}
        price = fetch_price("2330")
        assert price[0] is not None and price[0] != 950.0

    def test_cache_expiry_fallback_none(self, tmp_path):
        init_cache(str(tmp_path))
        old = time.time() - CACHE_TTL - 10
        _CACHE["999999"] = {"price": 100.0, "timestamp": old}
        price = fetch_price("999999")
        assert price[0] is None

    def test_cache_unknown_stock(self, tmp_path):
        init_cache(str(tmp_path))
        price = fetch_price("999999")
        assert price[0] is None

    def test_cache_persistence(self, tmp_path):
        init_cache(str(tmp_path))
        _CACHE["2330"] = {"price": 950.0, "timestamp": time.time()}
        from core.prices import _save_cache
        _save_cache()

        fp = tmp_path / "price_cache.json"
        assert fp.exists()
        data = json.loads(fp.read_text(encoding="utf-8"))
        assert data["2330"]["price"] == 950.0

    def test_cache_load_on_init(self, tmp_path):
        fp = tmp_path / "price_cache.json"
        fp.write_text(
            json.dumps({"2330": {"price": 950.0, "timestamp": time.time()}}),
            encoding="utf-8",
        )
        init_cache(str(tmp_path))
        assert _CACHE["2330"]["price"] == 950.0

    def test_clear_cache(self, tmp_path):
        init_cache(str(tmp_path))
        _CACHE["2330"] = {"price": 950.0, "timestamp": time.time()}
        from core.prices import _save_cache
        _save_cache()

        clear_cache()
        assert _CACHE == {}
        assert not (tmp_path / "price_cache.json").exists()

    def test_fetch_prices_mixed(self, tmp_path):
        init_cache(str(tmp_path))
        _CACHE["2330"] = {"price": 950.0, "timestamp": time.time()}
        from core.prices import fetch_prices
        prices = fetch_prices(["2330", "999999"])
        assert prices["2330"][0] == 950.0
        assert prices["999999"][0] is None
