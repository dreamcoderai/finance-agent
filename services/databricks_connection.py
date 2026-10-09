import logging
import os
import threading
import time

from dotenv import load_dotenv
from databricks import sql

load_dotenv()

logger = logging.getLogger(__name__)


class DatabricksUnavailable(RuntimeError):
    """The SQL warehouse can't be reached right now (stopped, quota, network)."""


class DatabricksConnection:
    """
    Lazy, self-healing singleton Databricks SQL connection.

    Nothing connects at import time, so the app starts even when the
    warehouse is down. After a failure Databricks is treated as unavailable
    for RETRY_AFTER_SECONDS (callers fall back to Yahoo Finance straight
    away), then the next request tries to connect again.
    """

    RETRY_AFTER_SECONDS = 60

    def __init__(self):
        self.connection = None
        self.last_error = None
        self._down_until = 0.0
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        return self.connection is not None or time.monotonic() >= self._down_until

    def get_connection(self):
        with self._lock:
            if self.connection is not None:
                return self.connection

            if time.monotonic() < self._down_until:
                raise DatabricksUnavailable(
                    f"Databricks unavailable, retrying shortly: {self.last_error}"
                )

            settings = {
                "server_hostname": os.getenv("DATABRICKS_SERVER_HOSTNAME"),
                "http_path": os.getenv("DATABRICKS_HTTP_PATH"),
                "access_token": os.getenv("DATABRICKS_ACCESS_TOKEN"),
            }
            missing = [k for k, v in settings.items() if not v]
            if missing:
                self._fail(f"missing settings: {', '.join(missing)}")
                raise DatabricksUnavailable(self.last_error)

            try:
                # Bounded retries: a warehouse that won't start should hand
                # over to Yahoo within seconds, not the connector's default
                # 15 minutes. 30s still covers a normal serverless cold start.
                self.connection = sql.connect(
                    **settings,
                    _retry_stop_after_attempts_count=3,
                    _retry_stop_after_attempts_duration=30,
                    _socket_timeout=30,
                )
            except Exception as ex:
                self._fail(ex)
                raise DatabricksUnavailable(self.last_error) from ex

            logger.info("Connected to Databricks SQL warehouse")
            return self.connection

    def mark_failed(self, error) -> None:
        """Drop the connection after a connection-level error (e.g. the warehouse stopped)."""
        with self._lock:
            self._fail(error)

    def _fail(self, error) -> None:
        if self.connection is not None:
            try:
                self.connection.close()
            except Exception:
                pass
        self.connection = None
        self.last_error = str(error)[:300]
        self._down_until = time.monotonic() + self.RETRY_AFTER_SECONDS
        logger.warning(
            "Databricks unavailable (%s); using fallback for %ss",
            self.last_error, self.RETRY_AFTER_SECONDS,
        )


# Singleton instance
databricks_connection = DatabricksConnection()
