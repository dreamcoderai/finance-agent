import os
import json

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

from services.financial_data_provider import financial_data_provider
from tools.company_tool import get_company_info
from tools.stock_tool import get_stock_price, get_historical_prices
from tools.financial_tool import (
    get_income_statement,
    get_balance_sheet,
    get_cash_flow,
    get_quarterly_income_statement,
    get_quarterly_balance_sheet,
    get_quarterly_cash_flow,
)

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


def _symbol_only(description: str) -> dict:
    """Shared JSON schema for tools that take a single ticker symbol."""

    return {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": description,
            }
        },
        "required": ["symbol"],
    }


class FinanceAgent:

    MODEL = "gpt-5"

    # Safety cap on agentic tool-calling rounds per question.
    MAX_TOOL_ROUNDS = 6

    def __init__(self):

        self.messages = [
            {
                "role": "system",
                "content": """
You are Finance AI, an expert financial research assistant.

Data:
- Company and financial data is served from a Databricks lakehouse
  (built from SEC symbols and Yahoo Finance), with a live fallback.
- Financial statements are returned in long format: one row per
  (fiscal_year[/fiscal_quarter], metric, value). Aggregate and read the
  relevant metric rows to answer (e.g. "Total Revenue", "Net Income").

Responsibilities:
- Use tools whenever current or company-specific financial data is required.
- Never guess stock prices or financial numbers; call a tool instead.
- If a tool returns no data for a symbol, say so plainly rather than
  inventing figures.
- Compare companies professionally and cite the concrete numbers you used.
- Explain financial concepts in simple language.
- Format answers clearly using headings and bullet points.
""",
            }
        ]

        # Tool schemas exposed to the model.
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_company_info",
                    "description": (
                        "Company profile: name, sector, industry, market "
                        "cap, valuation ratios (P/E, EPS), and latest price "
                        "snapshot."
                    ),
                    "parameters": _symbol_only(
                        "Stock ticker symbol like AAPL, MSFT, NVDA"
                    ),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_stock_price",
                    "description": "Latest available stock price snapshot for a symbol.",
                    "parameters": _symbol_only("Stock ticker symbol"),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_historical_prices",
                    "description": (
                        "Historical daily OHLCV price series for a symbol. "
                        "Use for trends, returns, and volatility over time."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Stock ticker symbol",
                            },
                            "period": {
                                "type": "string",
                                "description": "Look-back window",
                                "enum": [
                                    "1mo", "3mo", "6mo", "1y",
                                    "2y", "5y", "10y", "ytd", "max",
                                ],
                            },
                            "interval": {
                                "type": "string",
                                "description": "Bar interval",
                                "enum": ["1d", "1wk", "1mo"],
                            },
                        },
                        "required": ["symbol"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_income_statement",
                    "description": "Annual income statement (revenue, profit, expenses) by fiscal year.",
                    "parameters": _symbol_only("Stock ticker symbol"),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_balance_sheet",
                    "description": "Annual balance sheet (assets, liabilities, equity) by fiscal year.",
                    "parameters": _symbol_only("Stock ticker symbol"),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_cash_flow",
                    "description": "Annual cash flow statement (operating, investing, financing) by fiscal year.",
                    "parameters": _symbol_only("Stock ticker symbol"),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_quarterly_income_statement",
                    "description": "Quarterly income statement by fiscal year and quarter.",
                    "parameters": _symbol_only("Stock ticker symbol"),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_quarterly_balance_sheet",
                    "description": "Quarterly balance sheet by fiscal year and quarter.",
                    "parameters": _symbol_only("Stock ticker symbol"),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_quarterly_cash_flow",
                    "description": "Quarterly cash flow statement by fiscal year and quarter.",
                    "parameters": _symbol_only("Stock ticker symbol"),
                },
            },
        ]

        self.available_functions = {
            "get_company_info": get_company_info,
            "get_stock_price": get_stock_price,
            "get_historical_prices": get_historical_prices,
            "get_income_statement": get_income_statement,
            "get_balance_sheet": get_balance_sheet,
            "get_cash_flow": get_cash_flow,
            "get_quarterly_income_statement": get_quarterly_income_statement,
            "get_quarterly_balance_sheet": get_quarterly_balance_sheet,
            "get_quarterly_cash_flow": get_quarterly_cash_flow,
        }

    ####################################################################
    # Helpers
    ####################################################################

    @staticmethod
    def _serialize_result(result) -> str:
        """
        Turn a tool result into a compact JSON string for the model.

        Tools return either dicts (profile/price) or DataFrames (statements
        and price history), so DataFrames are emitted as JSON records instead
        of their string repr.
        """

        if isinstance(result, pd.DataFrame):
            return result.to_json(orient="records", date_format="iso")

        return json.dumps(result, default=str)

    def _run_tool(self, tool_call) -> str:

        name = tool_call.function.name

        function = self.available_functions.get(name)

        if function is None:
            return json.dumps({"error": f"Unknown tool: {name}"})

        try:
            arguments = json.loads(tool_call.function.arguments or "{}")
            result = function(**arguments)
            return self._serialize_result(result)

        except Exception as ex:  # surface tool errors to the model
            return json.dumps({"error": str(ex)})

    ####################################################################
    # Public API
    ####################################################################

    def set_data_source(self, mode):
        """
        Select which backend the tools use: "auto" | "databricks" | "yahoo".
        """
        financial_data_provider.set_source(mode)

    def get_last_sources(self) -> dict:
        """
        Which backend(s) actually served data for the most recent question.
        See FinancialDataProvider.sources_summary() for the shape.
        """
        return getattr(self, "last_sources", {"log": [], "sources": []})

    def ask(self, question: str) -> str:

        self.messages.append({"role": "user", "content": question})

        # Track which data source serves each tool call for this question.
        financial_data_provider.reset_tracking()

        # Agentic loop: let the model call tools across multiple rounds
        # (e.g. fetch several companies to compare) until it produces a
        # final natural-language answer.
        for _ in range(self.MAX_TOOL_ROUNDS):

            response = client.chat.completions.create(
                model=self.MODEL,
                messages=self.messages,
                tools=self.tools,
            )

            message = response.choices[0].message
            self.messages.append(message)

            if not message.tool_calls:
                self.last_sources = financial_data_provider.sources_summary()
                return message.content

            for tool_call in message.tool_calls:
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": self._run_tool(tool_call),
                    }
                )

        # Tool-round budget exhausted: ask once more without tools for a
        # best-effort answer from what has been gathered.
        final = client.chat.completions.create(
            model=self.MODEL,
            messages=self.messages,
        )

        answer = final.choices[0].message.content
        self.messages.append({"role": "assistant", "content": answer})

        self.last_sources = financial_data_provider.sources_summary()

        return answer

    def clear_history(self):
        """Reset conversation while keeping the system prompt."""

        self.messages = [self.messages[0]]
