from services import market_data_service


def get_company_info(symbol: str):
    """
    Returns company profile information.
    """
    return market_data_service.get_company_info(symbol)