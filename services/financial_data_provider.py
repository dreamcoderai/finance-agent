from enum import Enum

import pandas as pd

from services.databricks_service import DatabricksService
from services.market_data import MarketDataService


class DataSource(Enum):
    AUTO = "auto"
    DATABRICKS = "databricks"
    YAHOO = "yahoo"


class FinancialDataProvider:
    """
    Provides financial data from either Databricks or Yahoo Finance.

    Modes:
        AUTO        -> Databricks first, fallback to Yahoo
        DATABRICKS -> Only Databricks
        YAHOO       -> Only Yahoo Finance
    """

    def __init__(self, source=DataSource.AUTO):

        self.set_source(source)

        self.db = DatabricksService()
        self.yahoo = MarketDataService()

        # Per-request log of which backend actually served each call.
        self.source_log = []

    ####################################################################
    # Source selection & tracking
    ####################################################################

    def set_source(self, source):
        """
        Set the active data source. Accepts a DataSource enum or a string
        ("auto" | "databricks" | "yahoo").
        """

        if isinstance(source, DataSource):
            self.source = source
        else:
            self.source = DataSource(str(source).lower())

    def reset_tracking(self):
        """Clear the source log (call at the start of each request)."""
        self.source_log = []

    def _record(self, method_name: str, label, served, attempted: str):
        # served: the backend that returned data ("databricks"/"yahoo") or
        # None when no data was found. attempted: which backend(s) were
        # actually queried, so a miss can still name its source.
        self.source_log.append(
            {
                "method": method_name,
                "symbol": label,
                "source": served,
                "attempted": attempted,
            }
        )

    def sources_summary(self) -> dict:
        """
        Aggregate which backends served the calls since the last reset.

        Returns the raw log plus, per outcome, the symbols involved. Misses
        keep the `attempted` backend so the UI can still show the source.
        """

        databricks, yahoo, not_found = [], [], []

        for entry in self.source_log:
            if entry["source"] == "databricks":
                databricks.append(entry["symbol"])
            elif entry["source"] == "yahoo":
                yahoo.append(entry["symbol"])
            else:
                not_found.append(
                    {"symbol": entry["symbol"], "attempted": entry["attempted"]}
                )

        sources = []
        if databricks:
            sources.append("databricks")
        if yahoo:
            sources.append("yahoo")

        return {
            "log": list(self.source_log),
            "databricks": databricks,
            "yahoo": yahoo,
            "not_found": not_found,
            "sources": sources,
        }

    ####################################################################
    # Internal helper methods
    ####################################################################

    @staticmethod
    def _is_empty(data) -> bool:
        """
        Checks whether returned data is empty.
        """

        if data is None:
            return True

        if isinstance(data, dict):
            return len(data) == 0

        if isinstance(data, pd.DataFrame):
            return data.empty

        return False

    def _fetch(self, method_name: str, *args, **kwargs):
        """
        Generic fetch method.

        AUTO:
            Databricks -> Yahoo

        DATABRICKS:
            Databricks only

        YAHOO:
            Yahoo only
        """

        label = args[0] if args else None

        if self.source == DataSource.DATABRICKS:
            result = getattr(self.db, method_name)(*args, **kwargs)
            served = "databricks" if not self._is_empty(result) else None
            self._record(method_name, label, served, attempted="databricks")
            return result

        if self.source == DataSource.YAHOO:
            result = getattr(self.yahoo, method_name)(*args, **kwargs)
            served = "yahoo" if not self._is_empty(result) else None
            self._record(method_name, label, served, attempted="yahoo")
            return result

        # AUTO MODE: Databricks first, fall back to Yahoo.

        result = getattr(self.db, method_name)(*args, **kwargs)

        if not self._is_empty(result):
            self._record(
                method_name, label, "databricks", attempted="databricks"
            )
            return result

        result = getattr(self.yahoo, method_name)(*args, **kwargs)
        served = "yahoo" if not self._is_empty(result) else None
        self._record(
            method_name, label, served, attempted="databricks+yahoo"
        )
        return result

    ####################################################################
    # Company
    ####################################################################

    def get_company_info(self, symbol: str):
        return self._fetch("get_company_info", symbol)

    ####################################################################
    # Stock Price
    ####################################################################

    def get_stock_price(self, symbol: str):
        return self._fetch("get_stock_price", symbol)

    ####################################################################
    # Annual Financial Statements
    ####################################################################

    def get_income_statement(self, symbol: str):
        return self._fetch("get_income_statement", symbol)

    def get_balance_sheet(self, symbol: str):
        return self._fetch("get_balance_sheet", symbol)

    def get_cash_flow(self, symbol: str):
        return self._fetch("get_cash_flow", symbol)

    ####################################################################
    # Quarterly Financial Statements
    ####################################################################

    def get_quarterly_income_statement(self, symbol: str):
        return self._fetch("get_quarterly_income_statement", symbol)

    def get_quarterly_balance_sheet(self, symbol: str):
        return self._fetch("get_quarterly_balance_sheet", symbol)

    def get_quarterly_cash_flow(self, symbol: str):
        return self._fetch("get_quarterly_cash_flow", symbol)

    ####################################################################
    # Historical Prices
    ####################################################################

    def get_historical_prices(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1d",
    ):
        return self._fetch(
            "get_historical_prices",
            symbol,
            period,
            interval,
        )


# Shared singleton used by all tools and the agent, so mode selection and
# source tracking are centralized in one place.
financial_data_provider = FinancialDataProvider()