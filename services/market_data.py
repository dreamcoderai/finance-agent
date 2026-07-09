import yfinance as yf
import pandas as pd


class MarketDataService:
    """Service for retrieving market and company data from Yahoo Finance."""

    def _get_ticker(self, symbol: str):
        return yf.Ticker(symbol.upper())

    def get_company_info(self, symbol: str) -> dict:
        """Returns company profile and current market information."""
        ticker = self._get_ticker(symbol)
        info = ticker.info

        return {
            "symbol": symbol.upper(),
            "company": info.get("longName"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "market_cap": info.get("marketCap"),
            "employees": info.get("fullTimeEmployees"),
            "country": info.get("country"),
            "website": info.get("website"),
            "currency": info.get("currency"),
            "current_price": info.get("currentPrice"),
            "previous_close": info.get("previousClose"),
            "open": info.get("open"),
            "day_high": info.get("dayHigh"),
            "day_low": info.get("dayLow"),
            "volume": info.get("volume"),
            "average_volume": info.get("averageVolume"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "eps": info.get("trailingEps"),
            "dividend_yield": info.get("dividendYield"),
            "beta": info.get("beta"),
        }

    def get_stock_price(self, symbol: str) -> dict:
        """Returns current stock price information."""
        ticker = self._get_ticker(symbol)

        fast = ticker.fast_info

        return {
            "symbol": symbol.upper(),
            "price": fast.get("lastPrice"),
            "previous_close": fast.get("previousClose"),
            "open": fast.get("open"),
            "day_high": fast.get("dayHigh"),
            "day_low": fast.get("dayLow"),
            "volume": fast.get("lastVolume"),
            "currency": fast.get("currency"),
        }

    def get_income_statement(self, symbol: str) -> pd.DataFrame:
        """Returns annual income statement."""
        ticker = self._get_ticker(symbol)
        return ticker.financials

    def get_balance_sheet(self, symbol: str) -> pd.DataFrame:
        """Returns annual balance sheet."""
        ticker = self._get_ticker(symbol)
        return ticker.balance_sheet

    def get_cash_flow(self, symbol: str) -> pd.DataFrame:
        """Returns annual cash flow statement."""
        ticker = self._get_ticker(symbol)
        return ticker.cashflow

    def get_quarterly_income_statement(self, symbol: str) -> pd.DataFrame:
        """Returns quarterly income statement."""
        ticker = self._get_ticker(symbol)
        return ticker.quarterly_financials

    def get_quarterly_balance_sheet(self, symbol: str) -> pd.DataFrame:
        """Returns quarterly balance sheet."""
        ticker = self._get_ticker(symbol)
        return ticker.quarterly_balance_sheet

    def get_quarterly_cash_flow(self, symbol: str) -> pd.DataFrame:
        """Returns quarterly cash flow."""
        ticker = self._get_ticker(symbol)
        return ticker.quarterly_cashflow

    def get_historical_prices(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        period:
            1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max

        interval:
            1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo
        """
        ticker = self._get_ticker(symbol)
        return ticker.history(period=period, interval=interval)