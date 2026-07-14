"""
Main entry point for all data ingestion jobs.

Run:
    python ingestion/ingestion_manager.py
"""

from ingestion.sec_ingestion import SECIngestion
from ingestion.batch_ingestion import BatchIngestor


class IngestionManager:

    def __init__(self):
        self.sec = SECIngestion()
        self.batch = BatchIngestor()

    ####################################################
    # SEC
    ####################################################

    def ingest_sec_symbols(self):

        self.sec.ingest_symbols()

    ####################################################
    # Yahoo Finance
    ####################################################

    def ingest_yahoo(self, limit: int = None):

        # Ingest ALL Yahoo endpoints (profiles, prices, financials,
        # historical) for every active symbol, in one resumable, throttled,
        # batched pass. Safe to re-run: already-ingested symbols are skipped.
        self.batch.run(limit=limit)

    ####################################################
    # Run
    ####################################################

    def run(self, limit: int = None):

        # Step 1
        # Load master symbols from SEC into silver.symbols
        self.ingest_sec_symbols()

        # Step 2
        # Load all Yahoo Finance data into Bronze
        self.ingest_yahoo(limit=limit)


if __name__ == "__main__":
    IngestionManager().run()