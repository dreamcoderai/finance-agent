from services.financial_data_provider import financial_data_provider as provider


def get_company_info(symbol: str):
    return provider.get_company_info(symbol)