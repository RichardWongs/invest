from monitor import *


def simulation_week_macd(code):
    # 资料来源: 强势股投资日记 https://mp.weixin.qq.com/s/hskxWqXBoLDdc1ao57Ygaw
    simulation_date = date.today() + timedelta(days=7)
    kline = get_stock_kline_with_indicators(code, period=102)
    kline.append({'day': str(simulation_date), 'close': kline[-1]['close']})
    kline = MACD(kline)
    print(kline[-1])


def index_hour_rsi():
    indexs = [{'code': '000300', 'name': '沪深300'},
              {'code': '000905', 'name': '中证500'},
              {'code': '000016', 'name': '上证50'},
              {'code': '000688', 'name': '科创50'},
              {'code': '399296', 'name': '创成长'},
              {'code': '399997', 'name': '中证白酒'},
              {'code': '399976', 'name': 'CS新能车'},
              {'code': '399989', 'name': '中证医疗'},
              ]
    for i in indexs:
        kline = get_stock_kline_with_indicators(i['code'], is_index=True, period=60)
        kline = BooleanLine(RSI(kline))
        print(i['name'], kline[-1])



