import os

from dotenv import load_dotenv
from databricks import sql

load_dotenv()


class DatabricksConnection:
    """
    Singleton Databricks SQL connection.
    """

    def __init__(self):

        self.connection = sql.connect(
            server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
            http_path=os.getenv("DATABRICKS_HTTP_PATH"),
            access_token=os.getenv("DATABRICKS_ACCESS_TOKEN")
        )

    def get_connection(self):
        return self.connection


# Singleton instance
databricks_connection = DatabricksConnection()