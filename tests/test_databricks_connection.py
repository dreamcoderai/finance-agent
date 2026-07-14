from services.databricks_connection import databricks_connection


connection = databricks_connection.get_connection()

cursor = connection.cursor()

cursor.execute("SELECT current_catalog()")

print(cursor.fetchall())

cursor.close()