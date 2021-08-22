import jqdatasdk as jq
from jqdatasdk import *
from jqdatasdk.technical_analysis import *
from datetime import datetime
jq.auth('16651605580', 'Aa123456')


def get_EMA(prices, days):
    emas = prices.copy()  # 创造一个和cps一样大小的集合
    for i in range(len(prices)):
        if i == 0:
            emas[i] = prices[i]
        if i > 0:
            emas[i] = ((days - 1) * emas[i - 1] + 2 * prices[i]) / (days + 1)
    return emas[-1]


def average_line(code, shot_days, long_days):
    shot_data = jq.get_price(code, end_date=datetime.today(), count=shot_days+1)
    long_data = jq.get_price(code, end_date=datetime.today(), count=long_days+1)
    shot_data = [i[1] for i in shot_data.values]
    long_data = [i[1] for i in long_data.values]
    shot_ma = sum(shot_data[1:])/len(shot_data[1:])
    shot_ma_pre = sum(shot_data[:-1])/len(shot_data[:-1])
    long_ma = sum(long_data[1:])/len(long_data[1:])
    long_ma_pre = sum(long_data[:-1])/len(long_data[:-1])
    if shot_ma_pre <= long_ma_pre and shot_ma > long_ma:
        print("短均线上穿长均线")


class Stock:
    def __init__(self, code):
        self.code = code
        self.roe = None #净资产收益率ROE
        self.roa = None #总资产净利率ROA
        self.inc_return = None  #净资产收益率(扣除非经常损益)
        self.inc_revenue_year_on_year = None    #营业收入同比增长
        self.inc_revenue_annual = None  #营业收入环比增长
        self.inc_net_profit_year_on_year = None #净利润同比增长
        self.inc_net_profit_annual = None   #净利润环比增长

code = '300015.XSHE'
q = jq.query(indicator.code,
             indicator.roe,
             indicator.roa,
             indicator.inc_return,
             indicator.inc_revenue_year_on_year,
             indicator.inc_revenue_annual,
             indicator.inc_net_profit_year_on_year,
             indicator.inc_net_profit_annual).filter(
    indicator.inc_return > 10).filter(
    indicator.inc_revenue_year_on_year > 0).filter(
    indicator.inc_revenue_annual > 0).filter(
    indicator.inc_net_profit_year_on_year > 0).filter(
    indicator.inc_net_profit_annual > 0).order_by(indicator.roa)
data = get_fundamentals(q, date=None, statDate=None)
print(data.values)
# data = data.values[0]
# s = Stock(code)
# s.roe = data[0]
# s.roa = data[1]
# s.inc_return = data[2]
# s.inc_revenue_year_on_year = data[3]
# s.inc_revenue_annual = data[4]
# s.inc_net_profit_year_on_year = data[5]
# s.inc_net_profit_annual = data[6]




