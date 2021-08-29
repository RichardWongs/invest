import os
import logging
import pandas as pd
from datetime import date
from security import get_stock_kline_with_volume
from RPS.quantitative_screening import get_fund_holdings, foreignCapitalHolding, close_one_year_high, stock_pool_filter_process
from RPS.foreign_capital_increase import latest_week_foreign_capital_add_weight
from security import send_dingtalk_message
from security.动量选股 import get_position_stocks, get_buying_point_50_average, get_buying_point_20_average


class SecurityException(BaseException):
    pass


def get_average_price(kline, days):
    closes = [i['close'] for i in kline]
    assert len(closes) >= days
    return sum(closes[-days:]) / days


def get_avg_line_20_to_50(kline):
    # 股价介于50日均线之上至20日均线附近
    assert len(kline) > 50
    close = kline[-1]['close']
    avg_20 = get_average_price(kline, 20)
    avg_50 = get_average_price(kline, 50)
    if avg_50 < close <= avg_20 * 1.02:
        return True


def get_RPS_stock_pool(rps_value):
    # 根据RPS值进行第一步筛选
    os.chdir("../RPS")
    logging.warning("根据RPS查询股池")
    pool = set()
    files = ['RPS50.csv', 'RPS120.csv', 'RPS250.csv']
    for file in files:
        df = pd.read_csv(file, encoding='utf-8')
        for i in df.values:
            if i[-1] > rps_value:
                pool.add((i[0].split('.')[0], i[1]))
    return pool


def run_volume_monitor(pool, message=""):
    notify_message = f"{date.today()}\n{message}成交量异常警告:\n"
    notify_stocks = []
    for i in pool:
        kline = get_stock_kline_with_volume(i['code'])
        kline_item = kline[-1]
        if (kline_item['volume_ratio'] > 2 and kline_item['applies'] >= 5) \
                or (kline_item['volume_ratio'] < 0.6 and kline_item['applies'] < 0):
            i['volume_ratio'] = kline_item['volume_ratio']
            i['applies'] = kline_item['applies']
            notify_stocks.append(i)
    sorted_stocks = sorted(
        notify_stocks,
        key=lambda x: x['volume_ratio'],
        reverse=True)
    if sorted_stocks:
        for i in sorted_stocks:
            notify_message += f"{i}\n"
    if len(notify_message.split('\n')) > 2 and notify_message.split('\n')[2]:
        logging.warning(notify_message)
        send_dingtalk_message(notify_message)


def holding_volume_monitor():
    os.chdir("../security")
    notify_message = f"{date.today()}\n持仓异常警告:\t"
    for i in get_position_stocks():
        kline = get_stock_kline_with_volume(i)
        close = kline[-1]['close']
        day50_avg = get_average_price(kline, days=50)
        if close < day50_avg or kline[-1]['volume_ratio'] > 2:
            notify_message += f"{i}\t"
    if len(notify_message.split('\t')) > 1 and notify_message.split('\t')[1]:
        logging.warning(notify_message)
        send_dingtalk_message(notify_message)


def get_buying_point_by_50_average(pool):
    message = f"{date.today()}\n价格位于50日均线附近\n"
    for i in pool:
        if get_buying_point_50_average(i['code']):
            message += f"{i}\n"
    if len(message.split('\n')) > 2 and message.split('\n')[2]:
        logging.warning(message)
        send_dingtalk_message(message)


def get_today_strong_stock(pool):
    message = f"{date.today()}\n股价回踩20日均线\n"
    for i in pool:
        if get_buying_point_20_average(i['code']):
            message += f"{i}\n"
    if len(message.split('\n')) > 2 and message.split('\n')[2]:
        logging.warning(message)
        send_dingtalk_message(message)


def sending_today_stock_pool():
    pool = stock_pool_filter_process()
    run_volume_monitor(pool)
    get_buying_point_by_50_average(pool)
    get_today_strong_stock(pool)


def last_week_foreign_capital_add():
    pool = latest_week_foreign_capital_add_weight()
    logging.warning(f"最近5个交易日外资增持超过5千万: {pool}")
    run_volume_monitor(pool, message="外资一周增持个股")


if __name__ == '__main__':
    sending_today_stock_pool()
    last_week_foreign_capital_add()

