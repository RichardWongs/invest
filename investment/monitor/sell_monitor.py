import logging
from datetime import date
from security import send_dingtalk_message
from monitor import get_stock_kline_with_indicators, MACD, institutions_holding_rps_stock

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


