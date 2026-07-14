import json
from datetime import datetime

import pandas as pd

from services.databricks_connection import databricks_connection


class BronzeToSilverETL:
    """
    ETL process to transform Bronze raw JSON into normalized Silver tables.

    Bronze is append-only and keeps history (a new row per change), so every
    transform takes only the LATEST bronze snapshot per symbol and does a
    full refresh (DELETE + batched insert) of its Silver table.
    """

    CATALOG = "finance_catalog"
    BRONZE = "finance_catalog.bronze.raw_api_data"

    # Rows per INSERT statement for batch loads.
    INSERT_BATCH_SIZE = 300

    def __init__(self):
        self.connection = databricks_connection.get_connection()

    ############################################################
    # Generic helpers
    ############################################################

    def execute_query(self, query: str) -> pd.DataFrame:

        cursor = self.connection.cursor()

        cursor.execute(query)

        rows = cursor.fetchall()

        columns = [col[0] for col in cursor.description]

        cursor.close()

        return pd.DataFrame(rows, columns=columns)

    def _latest_bronze(self, endpoint: str = None,
                       endpoint_like: str = None) -> pd.DataFrame:
        """
        Return the latest bronze row per symbol for an endpoint, as a
        DataFrame with columns: id, symbol, payload, ingest_time.

        Pass either an exact `endpoint` or an `endpoint_like` pattern
        (used for historical prices, whose endpoint encodes period/interval).
        """

        if endpoint is not None:
            where = f"endpoint = '{endpoint}'"
        else:
            where = f"endpoint LIKE '{endpoint_like}'"

        query = f"""
        SELECT id, symbol, payload, ingest_time
        FROM (
            SELECT
                id,
                symbol,
                payload,
                ingest_time,
                ROW_NUMBER() OVER (
                    PARTITION BY symbol
                    ORDER BY ingest_time DESC, id DESC
                ) AS rn
            FROM {self.BRONZE}
            WHERE {where}
        )
        WHERE rn = 1
        """

        return self.execute_query(query)

    def _refresh_table(self, table: str, columns: list,
                      column_types: list, rows: list) -> int:
        """
        Full-refresh a Silver table: DELETE all rows, then insert `rows` in
        batched multi-row INSERT statements.

        Each placeholder is cast to its target column type explicitly: in a
        multi-row VALUES inline table Spark infers one common type per column
        across all rows, which fails when numeric columns mix int/float/None.
        """

        cursor = self.connection.cursor()

        cursor.execute(f"DELETE FROM {table}")

        cols_clause = "(" + ", ".join(columns) + ")"
        single_row = (
            "(" + ", ".join(f"CAST(? AS {t})" for t in column_types) + ")"
        )

        total = len(rows)

        for start in range(0, total, self.INSERT_BATCH_SIZE):

            batch = rows[start:start + self.INSERT_BATCH_SIZE]

            values_clause = ", ".join([single_row] * len(batch))
            params = [value for record in batch for value in record]

            cursor.execute(
                f"""
                INSERT INTO {table} {cols_clause}
                VALUES {values_clause}
                """,
                params,
            )

        self.connection.commit()

        cursor.close()

        return total

    @staticmethod
    def _fiscal_year(period_key: str) -> int:
        # period_key looks like "2025-09-30T00:00:00.000"
        return int(period_key[:4])

    @staticmethod
    def _fiscal_quarter(period_key: str) -> str:
        month = int(period_key[5:7])
        return f"Q{(month - 1) // 3 + 1}"

    ############################################################
    # Company Profile  (snapshot -> one row per symbol)
    ############################################################

    def load_company_profiles(self):

        print("Loading company profiles...")

        bronze_df = self._latest_bronze(endpoint="company_profile")

        if bronze_df.empty:
            print("No company profiles found.")
            return

        now = datetime.utcnow()

        rows = []
        for _, row in bronze_df.iterrows():

            p = json.loads(row["payload"])

            rows.append((
                row["id"],
                row["symbol"],
                p.get("company"),
                p.get("sector"),
                p.get("industry"),
                p.get("market_cap"),
                p.get("employees"),
                p.get("country"),
                p.get("website"),
                p.get("currency"),
                p.get("current_price"),
                p.get("previous_close"),
                p.get("open"),
                p.get("day_high"),
                p.get("day_low"),
                p.get("volume"),
                p.get("average_volume"),
                p.get("fifty_two_week_high"),
                p.get("fifty_two_week_low"),
                p.get("pe_ratio"),
                p.get("forward_pe"),
                p.get("eps"),
                p.get("dividend_yield"),
                p.get("beta"),
                now,
                now,
            ))

        columns = [
            "bronze_id", "symbol", "company_name", "sector", "industry",
            "market_cap", "employees", "country", "website", "currency",
            "current_price", "previous_close", "open", "day_high", "day_low",
            "volume", "average_volume", "fifty_two_week_high",
            "fifty_two_week_low", "pe_ratio", "forward_pe", "eps",
            "dividend_yield", "beta", "created_at", "updated_at",
        ]
        column_types = [
            "BIGINT", "STRING", "STRING", "STRING", "STRING",
            "BIGINT", "INT", "STRING", "STRING", "STRING",
            "DOUBLE", "DOUBLE", "DOUBLE", "DOUBLE", "DOUBLE",
            "BIGINT", "BIGINT", "DOUBLE",
            "DOUBLE", "DOUBLE", "DOUBLE", "DOUBLE",
            "DOUBLE", "DOUBLE", "TIMESTAMP", "TIMESTAMP",
        ]

        n = self._refresh_table(
            f"{self.CATALOG}.silver.company_profile",
            columns, column_types, rows,
        )
        print(f"Loaded {n} company profiles.")

    ############################################################
    # Current Stock Price  (snapshot -> one row per symbol)
    ############################################################

    def load_stock_prices(self):

        print("Loading stock prices...")

        bronze_df = self._latest_bronze(endpoint="stock_price")

        if bronze_df.empty:
            print("No stock prices found.")
            return

        now = datetime.utcnow()

        rows = []
        for _, row in bronze_df.iterrows():

            p = json.loads(row["payload"])

            # The stock_price payload has no date; use the bronze ingest_time
            # as the trade timestamp.
            trade_date = pd.Timestamp(row["ingest_time"]).to_pydatetime()

            rows.append((
                row["symbol"],
                trade_date,
                p.get("price"),
                p.get("previous_close"),
                p.get("open"),
                p.get("day_high"),
                p.get("day_low"),
                p.get("volume"),
                p.get("currency"),
                now,
            ))

        columns = [
            "symbol", "trade_date", "price", "previous_close", "open",
            "day_high", "day_low", "volume", "currency", "created_at",
        ]
        column_types = [
            "STRING", "TIMESTAMP", "DOUBLE", "DOUBLE", "DOUBLE",
            "DOUBLE", "DOUBLE", "BIGINT", "STRING", "TIMESTAMP",
        ]

        n = self._refresh_table(
            f"{self.CATALOG}.silver.stock_price",
            columns, column_types, rows,
        )
        print(f"Loaded {n} stock prices.")

    ############################################################
    # Historical Prices  (time-series -> one row per symbol/day)
    ############################################################

    def load_historical_prices(self):

        print("Loading historical prices...")

        # The endpoint encodes period/interval (e.g. historical_prices_1y_1d).
        bronze_df = self._latest_bronze(endpoint_like="historical_prices%")

        if bronze_df.empty:
            print("No historical prices found.")
            return

        now = datetime.utcnow()

        rows = []
        for _, row in bronze_df.iterrows():

            symbol = row["symbol"]

            for bar in json.loads(row["payload"]):

                date_str = bar.get("Date")
                if not date_str:
                    continue

                rows.append((
                    symbol,
                    date_str[:10],            # DATE part of the ISO timestamp
                    bar.get("Open"),
                    bar.get("High"),
                    bar.get("Low"),
                    bar.get("Close"),
                    bar.get("Volume"),
                    bar.get("Dividends"),
                    bar.get("Stock Splits"),
                    now,
                ))

        columns = [
            "symbol", "trade_date", "open", "high", "low", "close",
            "volume", "dividends", "stock_splits", "created_at",
        ]
        column_types = [
            "STRING", "DATE", "DOUBLE", "DOUBLE", "DOUBLE", "DOUBLE",
            "BIGINT", "DOUBLE", "DOUBLE", "TIMESTAMP",
        ]

        n = self._refresh_table(
            f"{self.CATALOG}.silver.historical_prices",
            columns, column_types, rows,
        )
        print(f"Loaded {n} historical price rows.")

    ############################################################
    # Financial statements (long format: metric per fiscal period)
    ############################################################

    def _load_annual_financial(self, endpoint: str, table: str, label: str):

        print(f"Loading {label}...")

        bronze_df = self._latest_bronze(endpoint=endpoint)

        if bronze_df.empty:
            print(f"No {label} found.")
            return

        now = datetime.utcnow()

        rows = []
        for _, row in bronze_df.iterrows():

            symbol = row["symbol"]

            for record in json.loads(row["payload"]):

                metric = record.get("index")
                if metric is None:
                    continue

                for key, value in record.items():
                    if key == "index" or value is None:
                        continue

                    rows.append((
                        symbol,
                        self._fiscal_year(key),
                        metric,
                        value,
                        now,
                    ))

        columns = ["symbol", "fiscal_year", "metric", "value", "created_at"]
        column_types = ["STRING", "INT", "STRING", "DOUBLE", "TIMESTAMP"]

        n = self._refresh_table(table, columns, column_types, rows)
        print(f"Loaded {n} {label} rows.")

    def _load_quarterly_financial(self, endpoint: str, table: str,
                                 label: str):

        print(f"Loading {label}...")

        bronze_df = self._latest_bronze(endpoint=endpoint)

        if bronze_df.empty:
            print(f"No {label} found.")
            return

        now = datetime.utcnow()

        rows = []
        for _, row in bronze_df.iterrows():

            symbol = row["symbol"]

            for record in json.loads(row["payload"]):

                metric = record.get("index")
                if metric is None:
                    continue

                for key, value in record.items():
                    if key == "index" or value is None:
                        continue

                    rows.append((
                        symbol,
                        self._fiscal_year(key),
                        self._fiscal_quarter(key),
                        metric,
                        value,
                        now,
                    ))

        columns = [
            "symbol", "fiscal_year", "fiscal_quarter",
            "metric", "value", "created_at",
        ]
        column_types = [
            "STRING", "INT", "STRING", "STRING", "DOUBLE", "TIMESTAMP",
        ]

        n = self._refresh_table(table, columns, column_types, rows)
        print(f"Loaded {n} {label} rows.")

    # Annual
    def load_income_statement(self):
        self._load_annual_financial(
            "income_statement",
            f"{self.CATALOG}.silver.income_statement",
            "income statement",
        )

    def load_balance_sheet(self):
        self._load_annual_financial(
            "balance_sheet",
            f"{self.CATALOG}.silver.balance_sheet",
            "balance sheet",
        )

    def load_cash_flow(self):
        self._load_annual_financial(
            "cash_flow",
            f"{self.CATALOG}.silver.cash_flow",
            "cash flow",
        )

    # Quarterly
    def load_quarterly_income_statement(self):
        self._load_quarterly_financial(
            "quarterly_income_statement",
            f"{self.CATALOG}.silver.quarterly_income_statement",
            "quarterly income statement",
        )

    def load_quarterly_balance_sheet(self):
        self._load_quarterly_financial(
            "quarterly_balance_sheet",
            f"{self.CATALOG}.silver.quarterly_balance_sheet",
            "quarterly balance sheet",
        )

    def load_quarterly_cash_flow(self):
        self._load_quarterly_financial(
            "quarterly_cash_flow",
            f"{self.CATALOG}.silver.quarterly_cash_flow",
            "quarterly cash flow",
        )

    ############################################################
    # Run
    ############################################################

    def run(self):

        self.load_company_profiles()
        self.load_stock_prices()
        self.load_historical_prices()

        self.load_income_statement()
        self.load_balance_sheet()
        self.load_cash_flow()

        self.load_quarterly_income_statement()
        self.load_quarterly_balance_sheet()
        self.load_quarterly_cash_flow()


if __name__ == "__main__":

    BronzeToSilverETL().run()
