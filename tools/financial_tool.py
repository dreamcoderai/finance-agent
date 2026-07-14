from services.financial_data_provider import financial_data_provider as provider


def get_income_statement(symbol: str):
    return provider.get_income_statement(symbol)


def get_balance_sheet(symbol: str):
    return provider.get_balance_sheet(symbol)


def get_cash_flow(symbol: str):
    return provider.get_cash_flow(symbol)


def get_quarterly_income_statement(symbol: str):
    return provider.get_quarterly_income_statement(symbol)


def get_quarterly_balance_sheet(symbol: str):
    return provider.get_quarterly_balance_sheet(symbol)


def get_quarterly_cash_flow(symbol: str):
    return provider.get_quarterly_cash_flow(symbol)