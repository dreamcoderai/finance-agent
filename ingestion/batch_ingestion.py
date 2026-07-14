"""
Resumable, throttled, batched ingestion of ALL Yahoo endpoints for every
active symbol in finance_catalog.silver.symbols.

Run:
    python -m ingestion.batch_ingestion

This is the "ingest everything in one shot" runner used by the pipeline
(ingestion_manager). It is safe to stop and re-run: each endpoint skips the
symbols already present in Bronze before making any Yahoo request, so a
re-run only fetches what is still missing and drains failures.

Properties (see also ingestion/bronze_loader.py):
  * Resumable  - skip-before-fetch per endpoint.
  * Throttled  - small thread pool + per-request delay + retry/backoff.
  * Efficient  - successful payloads written to Bronze in batched inserts.
  * Observable - per-chunk progress and a per-endpoint failure log.
"""

import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from ingestion.bronze_loader import BronzeLoader
from services.market_data import MarketDataService
from services.symbol_service import SymbolService


SOURCE = "YahooFinance"

# --- Balanced fetch profile (tune here) ----------------------------------
MAX_WORKERS = 4          # concurrent Yahoo requests
CHUNK_SIZE = 500         # symbols fetched + written per chunk
REQUEST_DELAY = 0.3      # polite delay before each request (seconds)
MAX_RETRIES = 3          # attempts per symbol before giving up
BACKOFF_BASE = 2.0       # exponential backoff base (seconds)
WRITE_RETRIES = 4        # retries for a batch write (Delta metadata conflicts)
# -------------------------------------------------------------------------

# Historical price window used for the historical endpoint.
HISTORY_PERIOD = "1y"
HISTORY_INTERVAL = "1d"


class BatchIngestor:

    def __init__(self):
        self.market = MarketDataService()
        self.symbols_service = SymbolService()

    ####################################################
    # Endpoint catalog: (endpoint_name, fetch(symbol))
    ####################################################

    def endpoints(self) -> list[tuple]:
        m = self.market
        return [
            ("company_profile", m.get_company_info),
            ("stock_price", m.get_stock_price),
            ("income_statement", m.get_income_statement),
            ("balance_sheet", m.get_balance_sheet),
            ("cash_flow", m.get_cash_flow),
            ("quarterly_income_statement", m.get_quarterly_income_statement),
            ("quarterly_balance_sheet", m.get_quarterly_balance_sheet),
            ("quarterly_cash_flow", m.get_quarterly_cash_flow),
            (
                f"historical_prices_{HISTORY_PERIOD}_{HISTORY_INTERVAL}",
                lambda s: m.get_historical_prices(
                    s, HISTORY_PERIOD, HISTORY_INTERVAL
                ),
            ),
        ]

    ####################################################
    # Fetch a single symbol (runs in a worker thread)
    ####################################################

    def _fetch_one(self, fetch_fn, symbol: str):
        """Fetch one payload with retry + exponential backoff."""

        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                time.sleep(REQUEST_DELAY)
                return symbol, fetch_fn(symbol), None
            except Exception as ex:  # noqa: BLE001 - record and back off
                last_error = str(ex)
                backoff = BACKOFF_BASE ** attempt + random.uniform(0, 0.5)
                time.sleep(backoff)

        return symbol, None, last_error

    ####################################################
    # Write a chunk to Bronze (with conflict retry)
    ####################################################

    @staticmethod
    def _write_batch(records: list[dict]) -> int:
        last_error = None
        for attempt in range(WRITE_RETRIES):
            try:
                return BronzeLoader.insert_batch(records)
            except Exception as ex:  # e.g. Delta metadata conflict
                last_error = str(ex)
                time.sleep(BACKOFF_BASE ** attempt + random.uniform(0, 0.5))
        raise RuntimeError(f"Batch write failed after retries: {last_error}")

    ####################################################
    # Fetch + write one chunk
    ####################################################

    def _process_chunk(self, endpoint: str, fetch_fn, chunk: list[str]):

        results = []
        failures = []

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = [
                pool.submit(self._fetch_one, fetch_fn, s) for s in chunk
            ]
            for future in as_completed(futures):
                symbol, payload, error = future.result()
                if error is not None:
                    failures.append((symbol, error))
                else:
                    results.append((symbol, payload))

        # Every symbol here was absent from Bronze for this endpoint
        # (skip-before-fetch), so all successful payloads are new rows.
        records = []
        for symbol, payload in results:
            payload_str, payload_hash = BronzeLoader.hash_payload(payload)
            records.append(
                {
                    "source": SOURCE,
                    "endpoint": endpoint,
                    "symbol": symbol,
                    "payload": payload_str,
                    "payload_hash": payload_hash,
                }
            )

        inserted = self._write_batch(records)

        return inserted, failures

    ####################################################
    # Run one endpoint over all pending symbols
    ####################################################

    def run_endpoint(self, endpoint: str, fetch_fn, limit: int = None):

        all_symbols = self.symbols_service.get_active_symbols()

        already = BronzeLoader.get_ingested_symbols(SOURCE, endpoint)
        pending = [s for s in all_symbols if s.upper() not in already]

        if limit is not None:
            pending = pending[:limit]

        print(
            f"\n=== {endpoint} === "
            f"pending: {len(pending)} | already ingested: {len(already)}"
        )

        if not pending:
            print(f"{endpoint}: nothing to do.")
            return 0, []

        total_inserted = 0
        all_failures = []

        for start in range(0, len(pending), CHUNK_SIZE):
            chunk = pending[start:start + CHUNK_SIZE]
            end = start + len(chunk)

            inserted, failures = self._process_chunk(endpoint, fetch_fn, chunk)

            total_inserted += inserted
            all_failures.extend(failures)

            print(
                f"  {endpoint} {end}/{len(pending)} "
                f"| inserted={total_inserted} | failed={len(all_failures)}"
            )

        if all_failures:
            self._write_failure_log(endpoint, all_failures)

        print(
            f"--- {endpoint} done | inserted={total_inserted} "
            f"| failed={len(all_failures)} ---"
        )

        return total_inserted, all_failures

    ####################################################
    # Run every endpoint
    ####################################################

    def run(self, limit: int = None):
        """
        Ingest all endpoints for all active symbols.

        limit: optional cap on symbols per endpoint (useful for a bounded
        test run). None = every pending symbol.
        """

        print("Starting full batch ingestion of all Yahoo endpoints.")

        summary = {}
        for endpoint, fetch_fn in self.endpoints():
            inserted, failures = self.run_endpoint(endpoint, fetch_fn, limit)
            summary[endpoint] = (inserted, len(failures))

        print("\n==== Batch ingestion complete ====")
        for endpoint, (inserted, failed) in summary.items():
            print(f"  {endpoint:<32} inserted={inserted:<7} failed={failed}")
        print(
            "\nRe-run this command to fetch any remaining symbols and retry "
            "failures."
        )

    ####################################################
    # Failure log
    ####################################################

    @staticmethod
    def _write_failure_log(endpoint: str, failures: list[tuple]):

        stamp = datetime.utcnow().isoformat()
        path = f"ingestion/failed_{endpoint}.log"

        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f"# Failures for {endpoint} at {stamp}Z\n")
            fh.write("# symbol\terror\n")
            for symbol, error in failures:
                fh.write(f"{symbol}\t{error}\n")

        print(f"  wrote {len(failures)} failures to {path}")


if __name__ == "__main__":
    BatchIngestor().run()
