"""
Creates Gold layer tables.

The Gold ETL (etl/silver_to_gold.py) publishes business-ready datasets by
copying each curated Silver table into a matching Gold table
(INSERT INTO gold SELECT * FROM silver). For that `SELECT *` to line up, the
Gold table must have exactly the same schema and column order as its Silver
source, so each Gold table is created directly FROM its Silver counterpart
(CREATE TABLE AS SELECT ... WHERE 1=0) rather than by hand-written DDL that
could drift out of sync.
"""

from services.databricks_connection import databricks_connection


CATALOG = "finance_catalog"


# (silver_table, gold_table). The Gold historical-price table is named
# `stock_prices` while its Silver source is `historical_prices`.
TABLE_MIRRORS = [
    ("company_profile", "company_profile"),
    ("stock_price", "stock_price"),
    ("historical_prices", "stock_prices"),
    ("income_statement", "income_statement"),
    ("balance_sheet", "balance_sheet"),
    ("cash_flow", "cash_flow"),
    ("quarterly_income_statement", "quarterly_income_statement"),
    ("quarterly_balance_sheet", "quarterly_balance_sheet"),
    ("quarterly_cash_flow", "quarterly_cash_flow"),
]


def create_gold_tables():

    conn = databricks_connection.get_connection()

    cursor = conn.cursor()

    for silver_table, gold_table in TABLE_MIRRORS:

        # WHERE 1=0 copies the schema (and column order) with no rows, so the
        # Gold table mirrors Silver exactly and the ETL's SELECT * aligns.
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {CATALOG}.gold.{gold_table}
        AS SELECT * FROM {CATALOG}.silver.{silver_table} WHERE 1=0
        """)

        print(f"Created gold.{gold_table} (mirror of silver.{silver_table}).")

    conn.commit()

    cursor.close()

    print("Gold tables created (or already exist).")


if __name__ == "__main__":
    create_gold_tables()
