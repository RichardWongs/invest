import logging
from datetime import date
from security import send_dingtalk_message
from monitor import *

SELL_LIST = [
    {'code': '600110', 'name': '诺德股份'},
    {'code': '600141', 'name': '兴发集团'},
    {'code': '159995', 'name': '芯片'},
]


def sell_signal(period=60):
    message = f"{date.today()}\t清仓警告\n"
    for i in SELL_LIST:
        kline = get_stock_kline_with_indicators(i['code'], period=period)
        kline = MACD(kline)
        # if kline[-1]['macd_direction'] == "DOWN" and kline[-2]['macd_direction'] == "UP":
        if kline[-1]['DIF'] < kline[-1]['DEA']:
            i['close'] = kline[-1]['close']
            message += f"{i['code']}\t{i['name']}\t{i['close']}\n"
            logging.warning(i)
    if message.split('\n')[1]:
        send_dingtalk_message(message)


def buy_signal(period=30):
    message = f"{date.today()}\t买点提示\n"
    for i in institutions_holding_rps_stock():
        kline = get_stock_kline_with_indicators(i['code'], period=period)
        kline = MACD(kline)
        if kline[-1]['DIF'] > kline[-1]['DEA'] and kline[-2]['DIF'] < kline[-2]['DEA']:
            i['close'] = kline[-1]['close']
            i['applies'] = kline[-1]['applies']
            message += f"{i['code']}\t{i['name']}\t{i['close']}\t{i['applies']}\n"
            logging.warning(i)
    if message.split('\n')[1]:
        send_dingtalk_message(message)


def stock_filter_by_Shrank_back_to_trample(volume_part=1):
    # 价格位于5日线之下,50日线方向向上,抓取缩量回踩的标的
    # volume_part 盘中执行时, 根据已开盘时长推算全天成交量
    N, M = 5, 50
    last_one = -1
    pool = institutions_holding_rps_stock_short()
    counter = 1
    message = f"{date.today()}\t缩量回踩标的筛选\n"
    for i in pool:
        kline = get_stock_kline_with_indicators(i['code'])
        kline = MACD(MA(MA(kline, N), M))
        if kline[last_one]['close'] <= kline[last_one][f'MA{N}']:
            if kline[last_one]['volume'] * volume_part < kline[last_one]['avg_volume']:
                i['industry'] = get_industry_by_code(i['code'])
                i['applies'] = kline[last_one]['applies']
                i['volume_ratio'] = kline[last_one]['volume_ratio']
                i['url'] = f"https://xueqiu.com/S/{'SH' if i['code'].startswith('6') else 'SZ'}{i['code']}"
                message += f"{i['code']}\t{i['name']}\t{i['close']}\t{i['applies']}\n"
                logging.warning(f" {counter}\t{i}")
    if message.split('\n')[1]:
        send_dingtalk_message(message)


