from tools.company_tool import get_company_info
from tools.stock_tool import get_stock_price
from tools.financial_tool import get_income_statement

print("=" * 60)
print("COMPANY")
print("=" * 60)
print(get_company_info("AAPL"))

print()

print("=" * 60)
print("PRICE")
print("=" * 60)
print(get_stock_price("MSFT"))

print()

print("=" * 60)
print("INCOME STATEMENT")
print("=" * 60)
print(get_income_statement("NVDA").head())