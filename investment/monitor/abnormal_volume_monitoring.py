import os
import logging
import pandas as pd
from datetime import date
from apscheduler.schedulers.blocking import BlockingScheduler
from security import get_stock_kline_with_volume
from RPS.quantitative_screening import get_fund_holdings, foreignCapitalHolding
from security import send_dingtalk_message
from security.动量选股 import get_position_stocks


class SecurityException(BaseException):
    pass


def get_average_price(kline, days):
    closes = [i['close'] for i in kline]
    assert len(closes) >= days
    return sum(closes[-days:])/days


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


def stock_pool_filter_process():
    rps_pool = get_RPS_stock_pool(rps_value=90)     # 股价相对强度RPS优先一切
    fund_pool = get_fund_holdings(quarter=2)
    foreign_capital_pool = foreignCapitalHolding()
    pool = fund_pool.union(foreign_capital_pool)    # 基金持股3% + 北向持股三千万
    pool = [i for i in pool if i in rps_pool]
    new_pool = []
    [new_pool.append({'code': i[0], 'name': i[1]}) for i in pool]
    print(f"基金持股3% + 北向持股三千万: {new_pool}")
    return new_pool


def run_monitor():
    pool = stock_pool_filter_process()
    notify_message = f"{date.today()}\n成交量异常警告:\n"
    for i in pool:
        kline = get_stock_kline_with_volume(i['code'])
        kline_item = kline[-1]
        if (kline_item['volume_ratio'] > 2 and kline_item['applies'] >= 5) \
                or (kline_item['volume_ratio'] < 0.6 and kline_item['applies'] < 0):
            notify_message += f"{i}\t"
    if len(notify_message.split('\t')) > 1 and notify_message.split('\t')[1]:
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


if __name__ == '__main__':
    sched = BlockingScheduler()
    sched.add_job(run_monitor, 'cron', hour="14", minute="40")
    sched.add_job(holding_volume_monitor, 'cron', hour="14", minute="45")
    sched.start()
