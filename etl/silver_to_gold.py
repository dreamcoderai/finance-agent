from services.databricks_connection import databricks_connection


class SilverToGoldETL:
    """
    ETL process to populate Gold tables from Silver.

    Gold contains business-ready, AI-ready datasets.
    """

    CATALOG = "finance_catalog"

    def __init__(self):
        self.connection = databricks_connection.get_connection()

    ############################################################
    # Generic Refresh
    ############################################################

    def refresh_table(
        self,
        silver_table: str,
        gold_table: str
    ):

        cursor = self.connection.cursor()

        print(f"Refreshing {gold_table}...")

        cursor.execute(f"""
        DELETE FROM {gold_table}
        """)

        cursor.execute(f"""
        INSERT INTO {gold_table}
        SELECT *
        FROM {silver_table}
        """)

        self.connection.commit()

        cursor.close()

    ############################################################
    # Company Profile
    ############################################################

    def load_company_profile(self):

        self.refresh_table(
            f"{self.CATALOG}.silver.company_profile",
            f"{self.CATALOG}.gold.company_profile"
        )

    ############################################################
    # Current Stock Price
    ############################################################

    def load_stock_price(self):

        self.refresh_table(
            f"{self.CATALOG}.silver.stock_price",
            f"{self.CATALOG}.gold.stock_price"
        )

    ############################################################
    # Historical Prices
    ############################################################

    def load_stock_prices(self):

        self.refresh_table(
            f"{self.CATALOG}.silver.historical_prices",
            f"{self.CATALOG}.gold.stock_prices"
        )

    ############################################################
    # Annual Financial Statements
    ############################################################

    def load_income_statement(self):

        self.refresh_table(
            f"{self.CATALOG}.silver.income_statement",
            f"{self.CATALOG}.gold.income_statement"
        )

    def load_balance_sheet(self):

        self.refresh_table(
            f"{self.CATALOG}.silver.balance_sheet",
            f"{self.CATALOG}.gold.balance_sheet"
        )

    def load_cash_flow(self):

        self.refresh_table(
            f"{self.CATALOG}.silver.cash_flow",
            f"{self.CATALOG}.gold.cash_flow"
        )

    ############################################################
    # Quarterly Financial Statements
    ############################################################

    def load_quarterly_income_statement(self):

        self.refresh_table(
            f"{self.CATALOG}.silver.quarterly_income_statement",
            f"{self.CATALOG}.gold.quarterly_income_statement"
        )

    def load_quarterly_balance_sheet(self):

        self.refresh_table(
            f"{self.CATALOG}.silver.quarterly_balance_sheet",
            f"{self.CATALOG}.gold.quarterly_balance_sheet"
        )

    def load_quarterly_cash_flow(self):

        self.refresh_table(
            f"{self.CATALOG}.silver.quarterly_cash_flow",
            f"{self.CATALOG}.gold.quarterly_cash_flow"
        )

    ############################################################
    # Run
    ############################################################

    def run(self):

        self.load_company_profile()

        self.load_stock_price()

        self.load_stock_prices()

        self.load_income_statement()
        self.load_balance_sheet()
        self.load_cash_flow()

        self.load_quarterly_income_statement()
        self.load_quarterly_balance_sheet()
        self.load_quarterly_cash_flow()


if __name__ == "__main__":

    SilverToGoldETL().run()