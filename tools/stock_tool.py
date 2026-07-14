from services.financial_data_provider import financial_data_provider as provider


def get_stock_price(symbol: str):
    return provider.get_stock_price(symbol)


def get_historical_prices(
    symbol: str,
    period: str = "1y",
    interval: str = "1d"
):
    return provider.get_historical_prices(
        symbol,
        period,
        interval
    )