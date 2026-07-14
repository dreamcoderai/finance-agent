import pandas as pd

from services.databricks_connection import databricks_connection


class SymbolService:
    """
    Service for retrieving symbols from Databricks.

    This acts as the master source of symbols for all
    ingestion pipelines.
    """

    def __init__(self):
        self.connection = databricks_connection.get_connection()

    def execute_query(self, query: str) -> pd.DataFrame:

        cursor = self.connection.cursor()

        cursor.execute(query)

        rows = cursor.fetchall()

        columns = [col[0] for col in cursor.description]

        cursor.close()

        return pd.DataFrame(rows, columns=columns)

    #########################################################
    # Active Symbols
    #########################################################

    def get_active_symbols(self) -> list[str]:

        query = """
        SELECT symbol
        FROM finance_catalog.silver.symbols
        WHERE active = TRUE
        ORDER BY symbol
        """

        df = self.execute_query(query)

        if df.empty:
            return []

        return df["symbol"].tolist()

    #########################################################
    # Symbol Details
    #########################################################

    def get_symbol(self, symbol: str) -> dict:

        query = f"""
        SELECT *
        FROM finance_catalog.silver.symbols
        WHERE symbol = '{symbol.upper()}'
        LIMIT 1
        """

        df = self.execute_query(query)

        if df.empty:
            return {}

        return df.iloc[0].to_dict()

    #########################################################
    # All Symbols
    #########################################################

    def get_all_symbols(self) -> pd.DataFrame:

        query = """
        SELECT *
        FROM finance_catalog.silver.symbols
        ORDER BY symbol
        """

        return self.execute_query(query)