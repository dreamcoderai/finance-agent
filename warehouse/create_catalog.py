"""
Creates the Unity Catalog catalog.

Catalog
    finance_catalog
"""

from services.databricks_connection import databricks_connection


CATALOG_NAME = "finance_catalog"


def create_catalog():

    conn = databricks_connection.get_connection()

    cursor = conn.cursor()

    cursor.execute(
        f"""
        CREATE CATALOG IF NOT EXISTS {CATALOG_NAME}
        """
    )

    conn.commit()

    print(f"Catalog '{CATALOG_NAME}' created (or already exists).")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    create_catalog()