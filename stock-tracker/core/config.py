import re

DEFAULT_FEE_RATE = 0.001425
DEFAULT_TAX_RATE_LISTED = 0.003
DEFAULT_TAX_RATE_OTC = 0.003
DEFAULT_TAX_RATE_ETF = 0.001


def is_etf_stock(stock_code: str) -> bool:
    return bool(re.match(r"^00", stock_code))


class Config:
    def __init__(self):
        self.fee_rate = DEFAULT_FEE_RATE
        self.tax_rate_listed = DEFAULT_TAX_RATE_LISTED
        self.tax_rate_otc = DEFAULT_TAX_RATE_OTC
        self.tax_rate_etf = DEFAULT_TAX_RATE_ETF
        self.exchange = "listed"
        self.is_etf = False
        self.reinvest_mode = "direct"  # "direct" 或 "match"

    @property
    def tax_rate(self):
        if self.is_etf:
            return self.tax_rate_etf
        return self.tax_rate_listed if self.exchange == "listed" else self.tax_rate_otc

    def update_fee_rate(self, rate: float):
        self.fee_rate = rate

    def update_tax_rate(self, rate: float, exchange: str = "listed"):
        if exchange == "listed":
            self.tax_rate_listed = rate
        elif exchange == "otc":
            self.tax_rate_otc = rate
        elif exchange == "etf":
            self.tax_rate_etf = rate

    def reset_to_defaults(self):
        self.fee_rate = DEFAULT_FEE_RATE
        self.tax_rate_listed = DEFAULT_TAX_RATE_LISTED
        self.tax_rate_otc = DEFAULT_TAX_RATE_OTC
        self.tax_rate_etf = DEFAULT_TAX_RATE_ETF
        self.is_etf = False
        self.reinvest_mode = "direct"

    def to_dict(self):
        return {
            "fee_rate": self.fee_rate,
            "tax_rate_listed": self.tax_rate_listed,
            "tax_rate_otc": self.tax_rate_otc,
            "tax_rate_etf": self.tax_rate_etf,
            "exchange": self.exchange,
            "is_etf": self.is_etf,
            "reinvest_mode": self.reinvest_mode,
        }

    @classmethod
    def from_dict(cls, data: dict):
        cfg = cls()
        cfg.fee_rate = data.get("fee_rate", DEFAULT_FEE_RATE)
        cfg.tax_rate_listed = data.get("tax_rate_listed", DEFAULT_TAX_RATE_LISTED)
        cfg.tax_rate_otc = data.get("tax_rate_otc", DEFAULT_TAX_RATE_OTC)
        cfg.tax_rate_etf = data.get("tax_rate_etf", DEFAULT_TAX_RATE_ETF)
        cfg.exchange = data.get("exchange", "listed")
        cfg.is_etf = data.get("is_etf", False)
        cfg.reinvest_mode = data.get("reinvest_mode", "direct")
        return cfg
