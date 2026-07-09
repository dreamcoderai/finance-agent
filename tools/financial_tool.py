from services import market_data_service


def get_income_statement(symbol: str):
    return market_data_service.get_income_statement(symbol)


def get_balance_sheet(symbol: str):
    return market_data_service.get_balance_sheet(symbol)


def get_cash_flow(symbol: str):
    return market_data_service.get_cash_flow(symbol)


def get_quarterly_income_statement(symbol: str):
    return market_data_service.get_quarterly_income_statement(symbol)


def get_quarterly_balance_sheet(symbol: str):
    return market_data_service.get_quarterly_balance_sheet(symbol)


def get_quarterly_cash_flow(symbol: str):
    return market_data_service.get_quarterly_cash_flow(symbol)