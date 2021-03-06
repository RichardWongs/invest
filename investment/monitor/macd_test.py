from RPS.动量模型 import find_institutions_holding
from monitor import *
from datetime import date


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


def readMarketData():
    # 读取本地行情文件并转换成字典返回
    import pickle
    os.chdir("../RPS")
    target = {}
    data = []
    for i in os.listdir(os.curdir):
        if i.startswith('MomentumMarketData'):
            with open(i, 'rb') as f:
                content = pickle.loads(f.read())
                data += content
    for i in data:
        target[i['code']] = i if len(i) <= 100 else i[-100:]
    return target


def find_institutions_holding_momentum():
    pool1 = find_institutions_holding()    # 机构持股股票池
    pool2 = select_high_rps_stock()  # 高RPS股票池
    pool = []
    for _, v in pool1.items():
        if v in pool2:
            pool.append(v)
    return pool


def Channel_Trade_System(pool: list):
    # 筛选机构持股列表中,股价当日曾跌破向下通道且MACD柱状线出现做多信号
    # all_kline = readMarketData()
    target = []
    index = -1
    for i in pool:
        if len(str(i['code']).split('.')[0]) == 6:
            c = Channel(code=i['code'], name=i['name'], kline=None)  # all_kline[i['code']]['kline']
            kline = c.kline
            kline = MACD(kline)
            if kline[index]['low'] <= kline[index]['down_channel'] and kline[index]['macd_direction'] != "DOWN":
                tmp = {'code': c.code, 'name': c.name, 'kline': kline[index]}
                target.append(tmp)
                logging.warning(tmp)
    logging.warning(f"{len(target)}\t{target}")
    return target


Channel_Trade_System(ALL_ETF)
