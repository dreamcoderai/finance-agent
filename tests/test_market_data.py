from services.market_data import MarketDataService

service = MarketDataService()

print("=" * 50)
print("Company Info")
print("=" * 50)
print(service.get_company_info("AAPL"))

print()

print("=" * 50)
print("Stock Price")
print("=" * 50)
print(service.get_stock_price("AAPL"))

print()

print("=" * 50)
print("Income Statement")
print("=" * 50)
print(service.get_income_statement("AAPL").head())

print()

print("=" * 50)
print("Balance Sheet")
print("=" * 50)
print(service.get_balance_sheet("AAPL").head())

print()

print("=" * 50)
print("Cash Flow")
print("=" * 50)
print(service.get_cash_flow("AAPL").head())

print()

print("=" * 50)
print("Historical Prices")
print("=" * 50)
print(service.get_historical_prices("AAPL", period="1mo").head())