from pathlib import Path
from data.importer import parse_trades_csv, export_trades_csv
from core.portfolio import Portfolio
from tests.fixtures import make_config


class TestParseTrades:
    def _write_csv(self, tmp_path, filename, rows, header):
        p = tmp_path / filename
        with open(p, "w", newline="", encoding="utf-8-sig") as f:
            f.write(",".join(header) + "\n")
            for r in rows:
                f.write(",".join(str(v) for v in r) + "\n")
        return p

    def test_basic_buy_sell(self, tmp_path):
        csv = self._write_csv(tmp_path, "trades.csv", [
            ["2024-01-01", "2330", "買進", 100, 1000, 142.5, 0],
            ["2024-06-01", "2330", "賣出", 150, 500, 0, 225],
        ], header=["日期", "股票代號", "買賣別", "價格", "股數", "手續費", "交易稅"])

        portfolio, n, _ = parse_trades_csv(csv)
        assert n == 2
        st = portfolio.get_state("2330")
        assert st.shares == 500
        assert len(st.history) == 2

    def test_no_stock_column_uses_default(self, tmp_path):
        csv = self._write_csv(tmp_path, "trades.csv", [
            ["2024-01-01", "買進", 100, 1000],
        ], header=["日期", "買賣別", "價格", "股數"])

        portfolio, n, _ = parse_trades_csv(csv)
        assert n == 1
        st = portfolio.get_state("0000")
        assert st.shares == 1000

    def test_english_headers(self, tmp_path):
        csv = self._write_csv(tmp_path, "trades.csv", [
            ["2024-01-01", "2330", "buy", 100, 1000],
        ], header=["date", "stock", "action", "price", "shares"])

        portfolio, n, _ = parse_trades_csv(csv)
        assert n == 1
        assert portfolio.get_state("2330").shares == 1000

    def test_taiwan_date_format(self, tmp_path):
        csv = self._write_csv(tmp_path, "trades.csv", [
            ["113/01/01", "2330", "B", 100, 1000],
        ], header=["日期", "股票代號", "買賣別", "價格", "股數"])

        portfolio, n, _ = parse_trades_csv(csv)
        assert n == 1
        tx = portfolio.get_state("2330").history[0]
        assert tx.date == "2024-01-01"

    def test_existing_portfolio(self, tmp_path):
        csv = self._write_csv(tmp_path, "trades.csv", [
            ["2024-06-01", "2330", "買進", 200, 500],
        ], header=["日期", "股票代號", "買賣別", "價格", "股數"])

        portfolio = Portfolio()
        cfg = make_config(fee_rate=0, tax_rate=0)
        from tests.fixtures import make_buy
        tx = make_buy("2024-01-01", 100, 1000)
        portfolio.add_transaction("2330", tx, cfg)

        portfolio, n, _ = parse_trades_csv(csv, portfolio, cfg)
        assert n == 1
        st = portfolio.get_state("2330")
        assert st.shares == 1500
        assert len(st.history) == 2

    def test_multiple_stocks(self, tmp_path):
        csv = self._write_csv(tmp_path, "trades.csv", [
            ["2024-01-01", "2330", "買進", 100, 1000],
            ["2024-02-01", "2317", "買進", 50, 2000],
            ["2024-06-01", "2330", "賣出", 250, 500],
        ], header=["日期", "股票代號", "買賣別", "價格", "股數"])

        portfolio, n, _ = parse_trades_csv(csv)
        assert n == 3
        assert sorted(portfolio.stock_codes) == ["2317", "2330"]
        assert portfolio.get_state("2330").shares == 500
        assert portfolio.get_state("2317").shares == 2000

    def test_export_trades_csv(self, tmp_path):
        portfolio = Portfolio()
        cfg = make_config(fee_rate=0, tax_rate=0)
        from tests.fixtures import make_buy
        tx = make_buy("2024-01-01", 100, 1000)
        portfolio.add_transaction("2330", tx, cfg)

        out = tmp_path / "export.csv"
        n = export_trades_csv(portfolio, out)
        assert n == 1
        content = out.read_text(encoding="utf-8-sig")
        assert "2330" in content
        assert "買進" in content

    def test_import_then_export(self, tmp_path):
        src = self._write_csv(tmp_path, "src.csv", [
            ["2024-01-01", "2330", "買進", 100, 1000, 142.5, 0],
        ], header=["日期", "股票代號", "買賣別", "價格", "股數", "手續費", "交易稅"])

        portfolio, n, _ = parse_trades_csv(src)
        assert n == 1

        out = tmp_path / "out.csv"
        export_trades_csv(portfolio, out)

        portfolio2, n2, _ = parse_trades_csv(out)
        assert n2 == 1
        st = portfolio2.get_state("2330")
        assert st.shares == 1000

    def test_empty_rows_skipped(self, tmp_path):
        csv = self._write_csv(tmp_path, "trades.csv", [
            ["2024-01-01", "2330", "買進", 100, 1000],
            [],
            ["2024-06-01", "2330", "賣出", 150, 500],
        ], header=["日期", "股票代號", "買賣別", "價格", "股數"])

        portfolio, n, _ = parse_trades_csv(csv)
        assert n == 2
        assert portfolio.get_state("2330").shares == 500

    def test_file_not_found(self):
        import pytest
        with pytest.raises(FileNotFoundError):
            parse_trades_csv("nonexistent.csv")
