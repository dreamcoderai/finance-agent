"""
Creates Bronze layer tables.

Bronze contains raw API responses exactly as received.
"""

from services.databricks_connection import databricks_connection


CATALOG = "finance_catalog"
SCHEMA = "bronze"


def create_raw_api_data_table(cursor):

    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.raw_api_data
    (
        id BIGINT GENERATED ALWAYS AS IDENTITY,

        source STRING NOT NULL,

        endpoint STRING NOT NULL,

        symbol STRING NOT NULL,

        ingest_time TIMESTAMP NOT NULL,

        payload STRING NOT NULL,

        payload_hash STRING NOT NULL,

        processing_status STRING DEFAULT 'NEW',

        processed_time TIMESTAMP,

        error_message STRING
    )
    USING DELTA
    TBLPROPERTIES ('delta.feature.allowColumnDefaults' = 'supported')
    """)


def create_bronze_tables():

    conn = databricks_connection.get_connection()

    cursor = conn.cursor()

    create_raw_api_data_table(cursor)

    conn.commit()

    print(f"Bronze tables created in '{CATALOG}.{SCHEMA}' (or already exist).")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    create_bronze_tables()