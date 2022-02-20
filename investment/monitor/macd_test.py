from RPS.动量模型 import find_institutions_holding
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


def Channel_Trade_System():
    # 筛选机构持股列表中,股价当日曾跌破向下通道且MACD柱状线出现做多信号
    pool = find_institutions_holding()
    target = []
    for _, i in pool.items():
        if len(i['code'].split('.')[0]) == 6:
            c = Channel(code=i['code'], name=i['name'])
            kline = c.kline
            kline = MACD(kline)
            if kline[-1]['low'] <= kline[-1]['down_channel'] and kline[-1]['macd_direction'] != "DOWN":
                tmp = {'code': c.code, 'name': c.name, 'kline': kline[-1]}
                target.append(tmp)
                logging.warning(tmp)
    logging.warning(target)
    return target


Channel_Trade_System()
