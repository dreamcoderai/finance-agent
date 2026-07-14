from services.databricks_connection import databricks_connection


class CreateGoldViews:

    CATALOG = "finance_catalog"

    def __init__(self):
        self.connection = databricks_connection.get_connection()

    def execute(self, sql: str):

        cursor = self.connection.cursor()
        cursor.execute(sql)
        self.connection.commit()
        cursor.close()

    ############################################################
    # Company Snapshot
    ############################################################

    def create_company_snapshot_view(self):

        self.execute(f"""
        CREATE OR REPLACE VIEW {self.CATALOG}.gold.v_company_snapshot AS

        SELECT
            cp.symbol,
            cp.company_name,
            cp.sector,
            cp.industry,
            cp.market_cap,
            cp.employees,
            cp.country,
            cp.website,
            cp.currency,
            cp.current_price,
            cp.previous_close,
            cp.open,
            cp.day_high,
            cp.day_low,
            cp.volume,
            cp.average_volume,
            cp.fifty_two_week_high,
            cp.fifty_two_week_low,
            cp.pe_ratio,
            cp.forward_pe,
            cp.eps,
            cp.dividend_yield,
            cp.beta
        FROM {self.CATALOG}.gold.company_profile cp
        """)

    ############################################################
    # Market Snapshot
    ############################################################

    def create_market_snapshot_view(self):

        self.execute(f"""
        CREATE OR REPLACE VIEW {self.CATALOG}.gold.v_market_snapshot AS

        SELECT

            sp.symbol,
            cp.company_name,
            cp.sector,
            sp.trade_date,
            sp.price,
            sp.previous_close,
            sp.open,
            sp.day_high,
            sp.day_low,
            sp.volume,
            sp.currency,
            cp.market_cap

        FROM {self.CATALOG}.gold.stock_price sp

        LEFT JOIN {self.CATALOG}.gold.company_profile cp

        ON sp.symbol = cp.symbol
        """)

    ############################################################
    # Financial Summary
    ############################################################

    def create_financial_summary_view(self):

        self.execute(f"""
        CREATE OR REPLACE VIEW {self.CATALOG}.gold.v_financial_summary AS

        SELECT

            symbol,

            fiscal_year,

            MAX(CASE WHEN metric='Total Revenue'
                     THEN value END) AS revenue,

            MAX(CASE WHEN metric='Net Income'
                     THEN value END) AS net_income,

            MAX(CASE WHEN metric='Operating Income'
                     THEN value END) AS operating_income,

            MAX(CASE WHEN metric='EBIT'
                     THEN value END) AS ebit,

            MAX(CASE WHEN metric='Diluted EPS'
                     THEN value END) AS diluted_eps

        FROM {self.CATALOG}.gold.income_statement

        GROUP BY symbol, fiscal_year
        """)

    ############################################################
    # Daily Returns
    ############################################################

    def create_daily_returns_view(self):

        self.execute(f"""
        CREATE OR REPLACE VIEW {self.CATALOG}.gold.v_daily_returns AS

        SELECT

            symbol,

            trade_date,

            close,

            LAG(close)
            OVER(
                PARTITION BY symbol
                ORDER BY trade_date
            ) previous_close,

            ROUND(

                (
                    close -
                    LAG(close)
                    OVER(
                        PARTITION BY symbol
                        ORDER BY trade_date
                    )
                )

                /

                LAG(close)
                OVER(
                    PARTITION BY symbol
                    ORDER BY trade_date
                )

                *100,

                4

            ) AS daily_return_pct

        FROM {self.CATALOG}.gold.stock_prices
        """)

    ############################################################
    # Largest Companies
    ############################################################

    def create_top_companies_view(self):

        self.execute(f"""
        CREATE OR REPLACE VIEW {self.CATALOG}.gold.v_top_companies AS

        SELECT *

        FROM {self.CATALOG}.gold.company_profile

        ORDER BY market_cap DESC
        """)

    ############################################################
    # Run
    ############################################################

    def run(self):

        self.create_company_snapshot_view()

        self.create_market_snapshot_view()

        self.create_financial_summary_view()

        self.create_daily_returns_view()

        self.create_top_companies_view()


if __name__ == "__main__":

    CreateGoldViews().run()