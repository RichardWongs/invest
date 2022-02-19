from datetime import date, timedelta
from fundresults import get_fund
from monitor import RSI, BooleanLine


def get_fund_kline(code, start_date=str(date.today() - timedelta(180)), end_date=str(date.today())):
    data = get_fund(code, start_date=start_date, end_date=end_date)
    for i in data:
        i['close'] = i['unit_close']
        i['last_close'] = i['last_unit_close']
        del i['cumulative_close']
        del i['unit_close']
        del i['last_cumulative_close']
        del i['last_unit_close']
        del i['ema50_unit_close']
        del i['ema150_unit_close']
        del i['ema50_cumulative_close']
        del i['ema150_cumulative_close']
    data = BooleanLine(RSI(data))
    return data


kline = get_fund_kline('007192')
for i in kline:
    print(i)

