import os
import json
from dotenv import load_dotenv
from openai import OpenAI

from tools.company_tool import get_company_info
from tools.stock_tool import get_stock_price
from tools.financial_tool import get_income_statement

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


class FinanceAgent:

    def __init__(self):

        self.messages = [
            {
                "role": "system",
                "content": """
You are Finance AI.

You are an expert financial research assistant.

Responsibilities:
- Answer financial questions accurately.
- Use tools whenever current financial data is required.
- Never guess stock prices or financial numbers.
- Compare companies professionally.
- Explain financial concepts in simple language.
- Format answers clearly using headings and bullet points.
"""
            }
        ]

        # Tools available to the model
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_company_info",
                    "description": "Get company profile, sector, market cap, and valuation information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Stock ticker symbol like AAPL, MSFT, NVDA"
                            }
                        },
                        "required": ["symbol"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_stock_price",
                    "description": "Get current stock price information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string"
                            }
                        },
                        "required": ["symbol"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_income_statement",
                    "description": "Get company income statement",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string"
                            }
                        },
                        "required": ["symbol"]
                    }
                }
            }
        ]

        self.available_functions = {
            "get_company_info": get_company_info,
            "get_stock_price": get_stock_price,
            "get_income_statement": get_income_statement,
        }

    def ask(self, question: str) -> str:

        self.messages.append(
            {
                "role": "user",
                "content": question
            }
        )

        response = client.chat.completions.create(
            model="gpt-5",
            messages=self.messages,
            tools=self.tools
        )

        message = response.choices[0].message

        # If GPT wants to call tools
        if message.tool_calls:

            self.messages.append(message)

            for tool_call in message.tool_calls:

                function_name = tool_call.function.name

                arguments = json.loads(
                    tool_call.function.arguments
                )

                result = self.available_functions[
                    function_name
                ](**arguments)

                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(
                            result,
                            default=str
                        )
                    }
                )

            # Ask GPT to explain the tool results
            final_response = client.chat.completions.create(
                model="gpt-5",
                messages=self.messages
            )

            answer = final_response.choices[0].message.content

            self.messages.append(
                {
                    "role": "assistant",
                    "content": answer
                }
            )

            return answer

        # No tool call needed
        answer = message.content

        self.messages.append(
            {
                "role": "assistant",
                "content": answer
            }
        )

        return answer

    def clear_history(self):
        """Reset conversation while keeping the system prompt."""

        self.messages = [self.messages[0]]