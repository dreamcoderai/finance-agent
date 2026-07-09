from services import market_data_service


def get_stock_price(symbol: str):
    """
    Returns current stock quote.
    """
    return market_data_service.get_stock_price(symbol)


def get_historical_prices(
    symbol: str,
    period: str = "1y",
    interval: str = "1d",
):
    """
    Returns historical stock prices.
    """
    return market_data_service.get_historical_prices(
        symbol,
        period,
        interval,
    )