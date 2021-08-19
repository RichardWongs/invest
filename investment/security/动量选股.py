import requests
import time
import configparser
from security import get_stock_kline, send_dingtalk_message
from datetime import datetime, date
from security.stock_pool import pool


def readconfig(env, configfile='security.ini'):
    config = configparser.ConfigParser()
    config.read(configfile, encoding='utf-8')
    assert env in config.sections(), "environment not match"
    items = config.items(env)
    return dict(items)


def get_benchmark():
    # 获取业绩基准
    benchmark = 0
    week_days = datetime.today().weekday()+1
    for index_code in ['399006', '399300', '399905', '000016']:
        index_data = get_stock_kline(index_code, is_index=True, period=101, limit=260+week_days)
        index_data = index_data[:-week_days]
        index_yield = round((index_data[-1]['close']-index_data[0]['last_close'])/index_data[0]['last_close']*100, 2)
        if index_yield > benchmark:
            benchmark = index_yield
    return benchmark


def get_stock_pool():
    # 获取全市场股票池
    stock_pool = []
    url = f"http://www.cnindex.com.cn/sample-detail/detail?indexcode=399311&dateStr=2021-07&pageNum=1&rows=1000"
    response = requests.get(url).json()
    response = response['data']['rows']
    for i in response:
        stock_pool.append({'code': i.get('seccode'), 'name': i.get('secname')})
    return stock_pool


def get_security():
    # 从中证800成分股中选取最近一年涨幅超过四大指数涨幅,且最近一年动量值在0.9以上的个股
    security = []
    benchmark = get_benchmark()
    stock_pool = pool
    week_days = datetime.today().weekday()+1
    for i in stock_pool:
        source_data = get_stock_kline(i.get('code'), limit=260+1)
        if source_data:
            data = source_data[:-1]
            close = source_data[-1]['close']
            highest = max([i['high'] for i in data])
            value = round(close/highest, 2)
            year_yield = round((data[-1]['close']-data[0]['last_close'])/data[0]['last_close']*100, 2)
            if value > 0.9 and year_yield > benchmark:
                tmp = {'code': i.get('code'), 'name': i.get('name'), 'value': value, 'closes': [i['close'] for i in source_data]}
                security.append(tmp)
        else:
            print(f"{i.get('code')}未获取到数据")
    # print(security)
    return security


def get_buying_point(close_prices, shot_line=5, long_line=20):
    # 根据均线获取买点 5日均线上穿20日均线
    assert len(close_prices) > 20
    shot_data = close_prices[-(shot_line+1):]
    long_data = close_prices[-(long_line+1):]
    shot_ma = sum(shot_data[1:])/len(shot_data[1:])
    shot_ma_pre = sum(shot_data[:-1])/len(shot_data[:-1])
    long_ma = sum(long_data[1:])/len(long_data[1:])
    long_ma_pre = sum(long_data[:-1])/len(long_data[:-1])
    if shot_ma_pre <= long_ma_pre and shot_ma > long_ma:
        return True


def get_buying_point_20_average(code):
    # 根据均线获取买点
    data = get_stock_kline(code)
    close = data[-1]['close']
    low = data[-1]['low']
    long_data = [i['close'] for i in data[-22:-1]]
    long_ma = sum(long_data[1:])/len(long_data[1:])
    long_ma_pre = sum(long_data[:-1])/len(long_data[:-1])
    if long_ma_pre < long_ma < close and (low <= long_ma or low <= long_ma * 1.005):
        # 20日均线向上,当日最低价回踩均线,收盘价站上均线
        return True


def get_position_stocks():
    # 查询已持仓股票, 以列表形式返回
    securities = readconfig('position_security')
    securities = securities.values()
    securities = [i for i in securities if i]
    return securities


def get_available_cash():
    # 查询账户可用资金
    cash = readconfig('available_cash')
    cash = [i for i in cash.values()][0]
    return int(cash)


def market_open():
    # 开盘时运行函数
    max_position_count = 3
    stocks = get_security()
    stock_pool = [i['code'] for i in stocks]
    sell_message = f"{date.today()}\n"
    for i in get_position_stocks():
        if i not in stock_pool:
            sell_message += f"平仓\t{i}\n"
            print(f"平仓\t{i}\n")
    send_dingtalk_message(sell_message)
    cash = get_available_cash()
    buying_message = f"{date.today()}\n"
    for i in stocks:
        position_count = len(get_position_stocks())
        if i.get('code') not in get_position_stocks() and max_position_count - position_count > 0:
            if get_buying_point_20_average(i.get('code')):
                buying_message += f"开仓\t{i.get('code')}\t{i.get('name')}\t金额:{cash/(max_position_count - position_count)}"
                print(f"开仓\t{i.get('code')}\t{i.get('name')}\t{i.get('value')}\t金额:{cash/(max_position_count - position_count)}")
    send_dingtalk_message(buying_message)


if __name__ == "__main__":
    start = time.time()
    market_open()
    print(f"cost time {int(time.time()-start)} 秒")
