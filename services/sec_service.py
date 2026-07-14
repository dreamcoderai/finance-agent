import requests
import pandas as pd


class SECService:

    COMPANY_TICKERS_URL = (
        "https://www.sec.gov/files/company_tickers.json"
    )

    HEADERS = {
        "User-Agent": "Finance AI Agent (your-email@example.com)"
    }

    def get_company_tickers(self) -> pd.DataFrame:

        response = requests.get(
            self.COMPANY_TICKERS_URL,
            headers=self.HEADERS,
            timeout=60,
        )

        response.raise_for_status()

        data = response.json()

        records = []

        for company in data.values():

            records.append({
                "cik": str(company["cik_str"]).zfill(10),
                "symbol": company["ticker"],
                "company_name": company["title"],
            })

        return pd.DataFrame(records)