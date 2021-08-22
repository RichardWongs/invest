import os
import logging
import pandas as pd
import requests, json, time
from datetime import date
# from security import get_stock_kline_with_volume
from RPS.quantitative_screening import get_fund_holdings, foreignCapitalHolding
from security import send_dingtalk_message
from security.动量选股 import get_position_stocks


class SecurityException(BaseException):
    pass


def get_average_price(kline, days):
    closes = [i['close'] for i in kline]
    assert len(closes) >= days
    return sum(closes[-days:])/days


def get_stock_kline_with_volume(code, is_index=False, period=101, limit=120):
    assert period in (5, 15, 30, 60, 101, 102, 103)
    if is_index:
        if code.startswith('3'):
            secid = f'0.{code}'
        elif code.startswith('0'):
            secid = f'1.{code}'
        elif code.startswith('H') or code.startswith('9'):
            secid = f'2.{code}'
        else:
            return None
    else:
        if str(code)[0] in ('0', '1', '3'):
            secid = f'0.{code}'
        else:
            secid = f'1.{code}'
    url = f"http://67.push2his.eastmoney.com/api/qt/stock/kline/get"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
    }
    params = {
        'cb': "jQuery11240671737283431526_1624931273440",
        'secid': secid,
        'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
        'fields1': 'f1,f2,f3,f4,f5,f6',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
        'klt': period,
        'fqt': 0,
        'end': '20500101',
        'lmt': limit,
        '_': f'{int(time.time()) * 1000}'
    }
    try:
        r = requests.get(url, headers=headers, params=params).text
        r = r.split('(')[1].split(')')[0]
        r = json.loads(r)
        if 'data' in r.keys():
            if isinstance(r['data'], dict) and 'klines' in r['data'].keys():
                r = r['data']['klines']
                r = [i.split(',') for i in r]
                new_data = []
                for i in r:
                    i = {'day': i[0], 'open': float(i[1]), 'close': float(i[2]),
                         'high': float(i[3]), 'low': float(i[4]), 'volume': float(i[6]),
                         'applies': float(i[8])}
                    new_data.append(i)
                for i in range(len(new_data)):
                    if i > 0:
                        new_data[i]['last_close'] = new_data[i-1]['close']
                    if i > 10:
                        avg_volume = 0
                        for j in range(i-1, i-11, -1):
                            avg_volume += new_data[j]['volume']
                        new_data[i]['avg_volume'] = avg_volume/10
                        if new_data[i]['volume'] > new_data[i]['avg_volume'] * 2:
                            new_data[i]['abnormal_volume'] = 1
                        elif new_data[i]['volume'] < new_data[i]['avg_volume'] / 2:
                            new_data[i]['abnormal_volume'] = 2
                        else:
                            new_data[i]['abnormal_volume'] = 0
                return new_data[1:]
    except SecurityException() as e:
        print(e)
        return None


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
        if (kline_item['abnormal_volume'] == 1 and kline_item['applies'] >= 5) or (kline_item['abnormal_volume'] == 2 and kline_item['applies'] < 0):
            notify_message += f"{i}\t"
    if len(notify_message.split('\t')) > 1 and notify_message.split('\t')[1]:
        send_dingtalk_message(notify_message)


def holding_volume_monitor():
    os.chdir("../security")
    notify_message = f"{date.today()}\n持仓异常警告:\t"
    for i in get_position_stocks():
        kline = get_stock_kline_with_volume(i)
        close = kline[-1]['close']
        day50_avg = get_average_price(kline, days=50)
        if close < day50_avg or kline[-1]['abnormal_volume'] == 1:
            notify_message += f"{i}\t"
    if len(notify_message.split('\t')) > 1 and notify_message.split('\t')[1]:
        print(notify_message.split('\t'))
        send_dingtalk_message(notify_message)


run_monitor()
holding_volume_monitor()
