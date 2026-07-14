"""
Creates all schemas inside finance_catalog.
"""

from services.databricks_connection import databricks_connection


CATALOG = "finance_catalog"

SCHEMAS = [
    "reference",
    "bronze",
    "silver",
    "gold",
    "analytics",
]


def create_schemas():

    conn = databricks_connection.get_connection()

    cursor = conn.cursor()

    for schema in SCHEMAS:

        cursor.execute(
            f"""
            CREATE SCHEMA IF NOT EXISTS
            {CATALOG}.{schema}
            """
        )

    conn.commit()

    print(f"Schemas created in '{CATALOG}': {', '.join(SCHEMAS)} (or already exist).")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    create_schemas()