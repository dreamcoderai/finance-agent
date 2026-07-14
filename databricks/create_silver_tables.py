"""
Creates Silver layer tables.

Silver contains normalized data parsed from Bronze raw JSON.
For Phase 1, We just need the tables that support:

Yahoo Finance ingestion
SEC symbols
Bronze → Silver transformation
AI Agent queries
"""

from services.databricks_connection import databricks_connection


CATALOG = "finance_catalog"
SCHEMA = "silver"


###############################################################
# Symbols Master
###############################################################

def create_symbols_table(cursor):

    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.symbols
    (
        symbol STRING NOT NULL,

        company_name STRING,

        cik STRING,

        exchange STRING,

        exchange_short_name STRING,

        sector STRING,

        industry STRING,

        country STRING,

        currency STRING,

        isin STRING,

        cusip STRING,

        source STRING,

        active BOOLEAN,

        created_at TIMESTAMP,

        updated_at TIMESTAMP
    )
    USING DELTA
    """)


###############################################################
# Company Profile
###############################################################

def create_company_profile_table(cursor):

    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.company_profile
    (
        bronze_id BIGINT,

        symbol STRING NOT NULL,

        company_name STRING,

        sector STRING,

        industry STRING,

        market_cap BIGINT,

        employees INT,

        country STRING,

        website STRING,

        currency STRING,

        current_price DOUBLE,

        previous_close DOUBLE,

        open DOUBLE,

        day_high DOUBLE,

        day_low DOUBLE,

        volume BIGINT,

        average_volume BIGINT,

        fifty_two_week_high DOUBLE,

        fifty_two_week_low DOUBLE,

        pe_ratio DOUBLE,

        forward_pe DOUBLE,

        eps DOUBLE,

        dividend_yield DOUBLE,

        beta DOUBLE,

        created_at TIMESTAMP,

        updated_at TIMESTAMP
    )
    USING DELTA
    """)


###############################################################
# Current Stock Price
###############################################################

def create_stock_price_table(cursor):

    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.stock_price
    (
        symbol STRING NOT NULL,

        trade_date TIMESTAMP,

        price DOUBLE,

        previous_close DOUBLE,

        open DOUBLE,

        day_high DOUBLE,

        day_low DOUBLE,

        volume BIGINT,

        currency STRING,

        created_at TIMESTAMP
    )
    USING DELTA
    """)


###############################################################
# Historical Prices
###############################################################

def create_historical_prices_table(cursor):

    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.historical_prices
    (
        symbol STRING NOT NULL,

        trade_date DATE,

        open DOUBLE,

        high DOUBLE,

        low DOUBLE,

        close DOUBLE,

        volume BIGINT,

        dividends DOUBLE,

        stock_splits DOUBLE,

        created_at TIMESTAMP
    )
    USING DELTA
    """)


###############################################################
# Annual Income Statement
###############################################################

def create_income_statement_table(cursor):

    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.income_statement
    (
        symbol STRING NOT NULL,

        fiscal_year INT,

        metric STRING,

        value DOUBLE,

        created_at TIMESTAMP
    )
    USING DELTA
    """)


###############################################################
# Annual Balance Sheet
###############################################################

def create_balance_sheet_table(cursor):

    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.balance_sheet
    (
        symbol STRING NOT NULL,

        fiscal_year INT,

        metric STRING,

        value DOUBLE,

        created_at TIMESTAMP
    )
    USING DELTA
    """)


###############################################################
# Annual Cash Flow
###############################################################

def create_cash_flow_table(cursor):

    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.cash_flow
    (
        symbol STRING NOT NULL,

        fiscal_year INT,

        metric STRING,

        value DOUBLE,

        created_at TIMESTAMP
    )
    USING DELTA
    """)


###############################################################
# Quarterly Income Statement
###############################################################

def create_quarterly_income_statement_table(cursor):

    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.quarterly_income_statement
    (
        symbol STRING NOT NULL,

        fiscal_year INT,

        fiscal_quarter STRING,

        metric STRING,

        value DOUBLE,

        created_at TIMESTAMP
    )
    USING DELTA
    """)


###############################################################
# Quarterly Balance Sheet
###############################################################

def create_quarterly_balance_sheet_table(cursor):

    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.quarterly_balance_sheet
    (
        symbol STRING NOT NULL,

        fiscal_year INT,

        fiscal_quarter STRING,

        metric STRING,

        value DOUBLE,

        created_at TIMESTAMP
    )
    USING DELTA
    """)


###############################################################
# Quarterly Cash Flow
###############################################################

def create_quarterly_cash_flow_table(cursor):

    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.quarterly_cash_flow
    (
        symbol STRING NOT NULL,

        fiscal_year INT,

        fiscal_quarter STRING,

        metric STRING,

        value DOUBLE,

        created_at TIMESTAMP
    )
    USING DELTA
    """)


###############################################################
# Create All Silver Tables
###############################################################

def create_silver_tables():

    conn = databricks_connection.get_connection()
    cursor = conn.cursor()

    # Master
    create_symbols_table(cursor)

    # Company
    create_company_profile_table(cursor)

    # Prices
    create_stock_price_table(cursor)
    create_historical_prices_table(cursor)

    # Annual Financials
    create_income_statement_table(cursor)
    create_balance_sheet_table(cursor)
    create_cash_flow_table(cursor)

    # Quarterly Financials
    create_quarterly_income_statement_table(cursor)
    create_quarterly_balance_sheet_table(cursor)
    create_quarterly_cash_flow_table(cursor)

    conn.commit()

    cursor.close()
    conn.close()


if __name__ == "__main__":
    create_silver_tables()