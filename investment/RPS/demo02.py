# encoding: utf-8
from datetime import date, timedelta
import time
import requests, json
import logging
import pandas as pd

import tushare as ts
pro = ts.pro_api("b625f0b90069039346d199aa3c0d5bc53fd47212437337b45ba87487")


def get_close(code):
    # 按照日期范围获取股票交易日期,收盘价
    start = int(str(date.today() - timedelta(days=365)).replace('-', ''))
    end = int(str(date.today()).replace('-', ''))
    df = pro.daily(ts_code=code, start_date=start, end_date=end, fields='trade_date,close')
    # 将交易日期设置为索引值
    df.index = pd.to_datetime(df.trade_date)
    df = df.sort_index()
    closes = []
    [closes.append(i[1]) for i in df.values]
    close = closes[-1]
    highest = max(closes[:-1])
    momentum = round(close / highest, 3)
    interval_yield = round((closes[-1] - closes[0]) / closes[0] * 100, 2)
    return {'code': code, 'interval_yield': interval_yield, 'momentum': momentum}


def foreignCapitalHolding():
    # 外资持股清单(持股市值超过5000万)
    logging.warning("查询外资持股数据")
    url = "http://dcfm.eastmoney.com/em_mutisvcexpandinterface/api/js/get"
    timestamp = int(time.time()*1000)
    params = {
        'callback': f'jQuery1123013917823929726048_{timestamp}',
        'st': 'ShareSZ_Chg_One',
        'sr': -1,
        'ps': 2000,
        'p': 1,
        'type': 'HSGT20_GGTJ_SUM',
        'token': '894050c76af8597a853f5b408b759f5d',
        'filter': f"(DateType='1')(HdDate='{date.today()-timedelta(days=1)}')"
    }
    r = requests.get(url, params=params)
    response = r.text.split('(')[1].split(')')[0]
    response = json.loads(response)
    response = sorted(response, key=lambda x: x['ShareSZ'], reverse=True)
    print(response)
    foreignCapital_pool = set()
    for i in response:
        code = i.get('SCode')
        name = i.get('SName')
        holding_market_value = round(i.get('ShareSZ')/100000000, 2)
        float_accounted = round(i.get('LTZB')*100, 2)
        if holding_market_value > 0.3:
            # tmp = {'code': code, 'name': name, 'holding_market_value': holding_market_value, 'float_accounted': float_accounted}
            foreignCapital_pool.add((code, name))
    return foreignCapital_pool

# {'SCode': '600519', 'SName': '贵州茅台', 'JG_SUM': 101.0, 'SharesRate': 7.27, 'NewPrice': 1750.5, 'ShareHold': 91376103.0, 'ShareSZ': 159953868301.5, 'LTZB': 0.0727402189368585, 'ZZB': 0.0727402189368585, 'LTSZ': 2198974248900.0, 'ZSZ': 2198974248900.0}

foreignCapitalHolding()
