import logging
import requests
import os, sys
import configparser
from security import get_stock_kline, send_dingtalk_message, get_stock_kline_with_volume
from datetime import datetime, date
from security.stock_pool import pool
sys.path.append(os.path.abspath(os.curdir))


def readconfig(env, configfile='security.ini'):
    config = configparser.ConfigParser()
    config.read(configfile, encoding='utf-8')
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


def get_security_V2():
    # 改进获取股票池方式, 根据RPS,机构持股,外资增持,股价接近一年新高等条件进行筛选,此股票池需每个交易日收盘后更新RPS数据
    from RPS.quantitative_screening import stock_pool_filter_process
    stock_pool = stock_pool_filter_process()
    for i in stock_pool:
        source_data = get_stock_kline_with_volume(i.get('code'), limit=260+1)
        if source_data:
            data = source_data[:-1]
            close = source_data[-1]['close']
            highest = max([i['close'] for i in data])   # 取最大的收盘价
            value = round(close/highest, 2)
            if value > 0.9:
                i['closes'] = [i['close'] for i in source_data]
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
    day = 20
    data = get_stock_kline_with_volume(code)
    close = data[-1]['close']
    low = data[-1]['low']
    long_data = [i['close'] for i in data[-(day+1):]]
    long_ma = sum(long_data[1:])/len(long_data[1:])
    long_ma_pre = sum(long_data[:-1])/len(long_data[:-1])
    if long_ma < close and (low <= long_ma):
        # 20日均线向上,当日最低价回踩均线,收盘价站上均线
        return True


def get_buying_point_50_average(code):
    # 根据均线获取买点
    day = 50
    data = get_stock_kline(code)
    close = data['kline'][-1]['close']
    low = data['kline'][-1]['low']
    long_data = [i['close'] for i in data['kline'][-(day+1):]]
    long_ma = sum(long_data[1:])/len(long_data[1:])
    long_ma_pre = sum(long_data[:-1])/len(long_data[:-1])
    if long_ma < close and (low <= long_ma or low <= long_ma * 1.02):
        # 50日均线向上,当日最低价回踩均线,收盘价站上均线
        return True


def get_selling_point(code):
    data = get_stock_kline(code)
    close = data['kline'][-1]['close']
    highest = max([i['close'] for i in data['kline']])
    value = round(close/highest, 2)
    long_data = [i['close'] for i in data['kline'][-51:]]
    long_ma = round(sum(long_data[1:])/len(long_data[1:]), 2)
    if close < long_ma or value < 0.9:
        del data['kline']
        return data


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
    max_position_count = 10
    stocks = get_security_V2()
    sell_message = f"{date.today()}\n"
    os.chdir("../security")
    position_stocks = get_position_stocks()
    for i in position_stocks:
        sell = get_selling_point(i)
        if sell:
            sell_message += f"平仓\t{sell.get('code')}\t{sell.get('name')}\n"
    logging.warning(sell_message)
    send_dingtalk_message(sell_message)
    cash = get_available_cash()
    buying_message = f"{date.today()}\n"
    for i in stocks:
        position_count = len(get_position_stocks())
        if i.get('code') not in get_position_stocks() and max_position_count - position_count > 0:
            if get_buying_point_50_average(i.get('code')):
                buying_message += f"开仓\t{i.get('code')}\t{i.get('name')}\t金额:{cash/(max_position_count - position_count)}"
                logging.warning(f"开仓\t{i.get('code')}\t{i.get('name')}\t{i.get('value')}\t金额:{cash/(max_position_count - position_count)}")
    if buying_message.split('\n')[1]:
        logging.warning(buying_message)
        send_dingtalk_message(buying_message)


if __name__ == "__main__":
    market_open()

