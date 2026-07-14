import hashlib
import json
from datetime import datetime
from typing import Any

import pandas as pd

from services.databricks_connection import databricks_connection


class BronzeLoader:

    TABLE = "finance_catalog.bronze.raw_api_data"

    # Rows per INSERT statement for batch loads (9 params each).
    INSERT_BATCH_SIZE = 500

    @staticmethod
    def serialize(payload: Any) -> str:

        if isinstance(payload, pd.DataFrame):
            # reset_index() first so the DataFrame index is preserved as a
            # column. yfinance frames carry meaningful indexes - the Date for
            # price history, the metric name for financial statements - and
            # orient="records" alone would silently drop them.
            return payload.reset_index().to_json(
                orient="records",
                date_format="iso"
            )

        return json.dumps(payload, default=str)

    @classmethod
    def hash_payload(cls, payload: Any) -> tuple[str, str]:
        """
        Serialize a payload and return (payload_str, sha256_hex_hash).
        """

        payload_str = cls.serialize(payload)
        payload_hash = hashlib.sha256(
            payload_str.encode("utf-8")
        ).hexdigest()

        return payload_str, payload_hash

    @classmethod
    def get_ingested_symbols(cls, source: str, endpoint: str) -> set[str]:
        """
        Return the set of symbols already present in Bronze for this
        (source, endpoint). Used to resume a batch job by skipping symbols
        that have already been ingested, before any API request is made.
        """

        conn = databricks_connection.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            f"""
            SELECT DISTINCT symbol
            FROM {cls.TABLE}
            WHERE source = ? AND endpoint = ?
            """,
            (source, endpoint),
        )

        symbols = {row[0] for row in cursor.fetchall()}

        cursor.close()

        return symbols

    @classmethod
    def insert_batch(cls, records: list[dict]) -> int:
        """
        Insert many already-serialized Bronze rows in batched multi-row
        INSERT statements (far faster than row-by-row against Delta).

        Each record must provide: source, endpoint, symbol, payload,
        payload_hash. ingest_time is stamped now; processing_status defaults
        to 'NEW'.

        Returns the number of rows inserted.
        """

        if not records:
            return 0

        now = datetime.utcnow()

        rows = [
            (
                r["source"],
                r["endpoint"],
                r["symbol"].upper(),
                now,
                r["payload"],
                r["payload_hash"],
                "NEW",
                None,
                None,
            )
            for r in records
        ]

        conn = databricks_connection.get_connection()
        cursor = conn.cursor()

        single_row = "(" + ", ".join(["?"] * 9) + ")"

        for start in range(0, len(rows), cls.INSERT_BATCH_SIZE):

            batch = rows[start:start + cls.INSERT_BATCH_SIZE]

            values_clause = ", ".join([single_row] * len(batch))
            params = [value for record in batch for value in record]

            cursor.execute(
                f"""
                INSERT INTO {cls.TABLE}
                (
                    source,
                    endpoint,
                    symbol,
                    ingest_time,
                    payload,
                    payload_hash,
                    processing_status,
                    processed_time,
                    error_message
                )
                VALUES {values_clause}
                """,
                params,
            )

        conn.commit()

        cursor.close()

        return len(rows)

    @classmethod
    def load(
        cls,
        source: str,
        endpoint: str,
        symbol: str,
        payload: Any,
    ) -> str:
        """
        Append the raw payload to the Bronze layer, retaining full history.

        Bronze is append-only: every change to a symbol/endpoint becomes a
        new row. To avoid storing redundant duplicates, a new row is only
        written when the payload differs from the most recent snapshot for
        the same (source, endpoint, symbol). Comparison is by SHA-256 of the
        serialized payload.

        Returns "inserted" when a new row was written, or "skipped" when the
        payload was identical to the latest snapshot.
        """

        symbol = symbol.upper()
        payload_str, payload_hash = cls.hash_payload(payload)

        conn = databricks_connection.get_connection()

        cursor = conn.cursor()

        # Compare against the most recent snapshot for this key. If the raw
        # payload is byte-identical, this is a redundant re-ingestion, so we
        # skip it rather than appending a duplicate historical row.
        cursor.execute(
            f"""
            SELECT payload_hash
            FROM {cls.TABLE}
            WHERE source = ? AND endpoint = ? AND symbol = ?
            ORDER BY ingest_time DESC
            LIMIT 1
            """,
            (source, endpoint, symbol),
        )
        latest = cursor.fetchone()

        if latest is not None and latest[0] == payload_hash:
            cursor.close()
            return "skipped"

        cursor.execute(
            f"""
            INSERT INTO {cls.TABLE}
            (
                source,
                endpoint,
                symbol,
                ingest_time,
                payload,
                payload_hash,
                processing_status,
                processed_time,
                error_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source,
                endpoint,
                symbol,
                datetime.utcnow(),
                payload_str,
                payload_hash,
                "NEW",
                None,
                None,
            ),
        )

        conn.commit()

        # Only close the cursor. The connection is a shared singleton
        # (services.databricks_connection) reused across every load call,
        # so closing it here would break all subsequent inserts.
        cursor.close()

        return "inserted"