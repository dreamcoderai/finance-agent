import pandas as pd
from databricks.sql.exc import ServerOperationError

from services.databricks_connection import DatabricksUnavailable, databricks_connection


class DatabricksService:
    """
    Service for retrieving financial market data from Databricks Unity Catalog.
    """

    def execute_query(self, query: str) -> pd.DataFrame:
        """
        Executes a SQL query and returns a pandas DataFrame.

        Raises DatabricksUnavailable when the warehouse can't be reached, so
        the provider can fall back to Yahoo Finance.
        """

        # Connects on first use (never at import), raises when unavailable.
        connection = databricks_connection.get_connection()

        try:
            cursor = connection.cursor()
            try:
                cursor.execute(query)
                rows = cursor.fetchall()
                columns = [col[0] for col in cursor.description]
            finally:
                cursor.close()
        except ServerOperationError:
            # The query itself failed (e.g. a missing table); the warehouse is fine.
            raise
        except Exception as ex:
            # Connection-level failure: the warehouse stopped or the session expired.
            databricks_connection.mark_failed(ex)
            raise DatabricksUnavailable(str(ex)[:300]) from ex

        return pd.DataFrame(rows, columns=columns)

    #########################################################
    # Company Information
    #########################################################

    def get_company_info(self, symbol: str) -> dict:

        query = f"""
        SELECT *
        FROM finance_catalog.gold.company_profile
        WHERE symbol = '{symbol.upper()}'
        LIMIT 1
        """

        df = self.execute_query(query)

        if df.empty:
            return {}

        return df.iloc[0].to_dict()

    #########################################################
    # Current Stock Price
    #########################################################

    def get_stock_price(self, symbol: str) -> dict:

        query = f"""
        SELECT *
        FROM finance_catalog.gold.stock_price
        WHERE symbol = '{symbol.upper()}'
        ORDER BY trade_date DESC
        LIMIT 1
        """

        df = self.execute_query(query)

        if df.empty:
            return {}

        return df.iloc[0].to_dict()

    #########################################################
    # Annual Financial Statements
    #########################################################

    def get_income_statement(self, symbol: str) -> pd.DataFrame:

        query = f"""
        SELECT *
        FROM finance_catalog.gold.income_statement
        WHERE symbol = '{symbol.upper()}'
        ORDER BY fiscal_year DESC
        """

        return self.execute_query(query)

    def get_balance_sheet(self, symbol: str) -> pd.DataFrame:

        query = f"""
        SELECT *
        FROM finance_catalog.gold.balance_sheet
        WHERE symbol = '{symbol.upper()}'
        ORDER BY fiscal_year DESC
        """

        return self.execute_query(query)

    def get_cash_flow(self, symbol: str) -> pd.DataFrame:

        query = f"""
        SELECT *
        FROM finance_catalog.gold.cash_flow
        WHERE symbol = '{symbol.upper()}'
        ORDER BY fiscal_year DESC
        """

        return self.execute_query(query)

    #########################################################
    # Quarterly Financial Statements
    #########################################################

    def get_quarterly_income_statement(self, symbol: str) -> pd.DataFrame:

        query = f"""
        SELECT *
        FROM finance_catalog.gold.quarterly_income_statement
        WHERE symbol = '{symbol.upper()}'
        ORDER BY fiscal_year DESC, fiscal_quarter DESC
        """

        return self.execute_query(query)

    def get_quarterly_balance_sheet(self, symbol: str) -> pd.DataFrame:

        query = f"""
        SELECT *
        FROM finance_catalog.gold.quarterly_balance_sheet
        WHERE symbol = '{symbol.upper()}'
        ORDER BY fiscal_year DESC, fiscal_quarter DESC
        """

        return self.execute_query(query)

    def get_quarterly_cash_flow(self, symbol: str) -> pd.DataFrame:

        query = f"""
        SELECT *
        FROM finance_catalog.gold.quarterly_cash_flow
        WHERE symbol = '{symbol.upper()}'
        ORDER BY fiscal_year DESC, fiscal_quarter DESC
        """

        return self.execute_query(query)

    #########################################################
    # Historical Prices
    #########################################################

    def get_historical_prices(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1d"
    ) -> pd.DataFrame:

        query = f"""
        SELECT *
        FROM finance_catalog.gold.stock_prices
        WHERE symbol = '{symbol.upper()}'
        ORDER BY trade_date
        """

        return self.execute_query(query)