from datetime import datetime

from services.sec_service import SECService
from services.databricks_connection import databricks_connection


class SECIngestion:
    """
    Loads SEC company tickers into finance_catalog.silver.symbols.
    """

    CATALOG = "finance_catalog"
    SCHEMA = "silver"
    TABLE = "symbols"

    # Rows per INSERT statement (15 params each -> ~7.5k bound params).
    BATCH_SIZE = 500

    def __init__(self):
        self.sec = SECService()
        self.connection = databricks_connection.get_connection()

    def ingest_symbols(self):

        print("Fetching symbols from SEC...")

        df = self.sec.get_company_tickers()

        print(f"Retrieved {len(df)} symbols.")

        cursor = self.connection.cursor()

        # Initial load: clear table
        cursor.execute(f"""
            DELETE FROM {self.CATALOG}.{self.SCHEMA}.{self.TABLE}
        """)

        now = datetime.utcnow()

        # Build one row of parameters per symbol. Columns not provided by
        # SEC are left NULL and enriched later by other sources.
        rows = [
            (
                row["symbol"],
                row["company_name"],
                row["cik"],
                None,   # exchange
                None,   # exchange_short_name
                None,   # sector
                None,   # industry
                None,   # country
                None,   # currency
                None,   # isin
                None,   # cusip
                "SEC",
                True,
                now,
                now,
            )
            for _, row in df.iterrows()
        ]

        total = len(rows)

        # Insert in batches. Row-by-row inserts against a Delta table are
        # extremely slow (one query + commit + small file each), so we send
        # many rows per INSERT statement instead.
        columns = """
        (
            symbol,
            company_name,
            cik,
            exchange,
            exchange_short_name,
            sector,
            industry,
            country,
            currency,
            isin,
            cusip,
            source,
            active,
            created_at,
            updated_at
        )
        """

        single_row = "(" + ", ".join(["?"] * 15) + ")"

        for start in range(0, total, self.BATCH_SIZE):

            batch = rows[start:start + self.BATCH_SIZE]

            values_clause = ", ".join([single_row] * len(batch))
            params = [value for record in batch for value in record]

            cursor.execute(
                f"""
                INSERT INTO {self.CATALOG}.{self.SCHEMA}.{self.TABLE}
                {columns}
                VALUES {values_clause}
                """,
                params,
            )

            print(f"Inserted {min(start + self.BATCH_SIZE, total)}/{total}")

        self.connection.commit()

        # Only close the cursor. The connection is a shared singleton
        # (services.databricks_connection) reused by later ingestion steps
        # (e.g. Yahoo), so closing it here would break them.
        cursor.close()

        print(f"\nSuccessfully loaded {total} symbols into silver.symbols.")