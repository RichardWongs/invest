import logging
from datetime import date
from security import send_dingtalk_message
from monitor import get_stock_kline_with_indicators, MACD

SELL_LIST = [
    {'code': '002326', 'name': '永太科技'},
    {'code': '300443', 'name': '金雷股份'},
    {'code': '002407', 'name': '多氟多'},
    {'code': '600110', 'name': '诺德股份'},
]


def sell_signal():
    message = f"{date.today()}\t清仓警告\n"
    for i in SELL_LIST:
        kline = get_stock_kline_with_indicators(i['code'], period=60)
        kline = MACD(kline)
        if kline[-1]['macd_direction'] == "DOWN" and kline[-2]['macd_direction'] == "UP":
            i['close'] = kline[-1]['close']
            message += f"{i['code']}\t{i['name']}\t{i['close']}\n"
            logging.warning(i)
    if message.split('\n')[1]:
        send_dingtalk_message(message)



