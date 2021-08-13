# encoding: utf-8
import time
import json
import logging
import pandas as pd
from datetime import date, timedelta
import requests
from bs4 import BeautifulSoup
import opencc
from security.stock_pool import whole_pool
import tushare as ts

cc = opencc.OpenCC('t2s')
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
    # 最新外资持股清单(持股市值超过3000万)
    logging.warning("查询外资持股数据")
    url = "http://dcfm.eastmoney.com/em_mutisvcexpandinterface/api/js/get"
    timestamp = int(time.time() * 1000)
    params = {
        'callback': f'jQuery1123013917823929726048_{timestamp}',
        'st': 'ShareSZ_Chg_One',
        'sr': -1,
        'ps': 2000,
        'p': 1,
        'type': 'HSGT20_GGTJ_SUM',
        'token': '894050c76af8597a853f5b408b759f5d',
        'filter': f"(DateType='1')(HdDate='{date.today() - timedelta(days=1)}')"
    }
    r = requests.get(url, params=params)
    response = r.text.split('(')[1].split(')')[0]
    response = json.loads(response)
    response = sorted(response, key=lambda x: x['ShareSZ'], reverse=True)
    foreignCapital_pool = []
    for i in response:
        code = i.get('SCode')
        name = i.get('SName')
        holding_market_value = round(i.get('ShareSZ') / 100000000, 2)
        holdingCount = i.get('ShareHold')
        price = i.get('NewPrice')
        float_accounted = i.get('LTZB')
        if holding_market_value > 0.3:
            tmp = {'code': code, 'name': name, 'price': price, 'holdingCount': holdingCount,
                   'holding_market_value': holding_market_value, 'float_accounted': float_accounted}
            foreignCapital_pool.append(tmp)
    return foreignCapital_pool


def foreignCapitalHistoryHolding(exchange, holding_date=date.today()):
    url = f"https://www.hkexnews.hk/sdw/search/mutualmarket_c.aspx?t={exchange}"
    body = {
        # "__VIEWSTATE": "/wEPDwUJNjIxMTYzMDAwZGQ79IjpLOM+JXdffc28A8BMMA9+yg==",
        # "__VIEWSTATEGENERATOR": "EC4ACD6F",
        # "__EVENTVALIDATION": "/wEdAAdtFULLXu4cXg1Ju23kPkBZVobCVrNyCM2j+bEk3ygqmn1KZjrCXCJtWs9HrcHg6Q64ro36uTSn/Z2SUlkm9HsG7WOv0RDD9teZWjlyl84iRMtpPncyBi1FXkZsaSW6dwqO1N1XNFmfsMXJasjxX85jz8PxJxwgNJLTNVe2Bh/bcg5jDf8=",
        "today": str(date.today()).replace('-', ''),
        "sortBy": "stockcode",
        "sortDirection": "desc",
        "alertMsg": "",
        "txtShareholdingDate": str(holding_date).replace('-', '/'),
        "btnSearch": "搜寻"
    }
    html = requests.post(url, json=body).text
    soup = BeautifulSoup(html, 'html.parser').select('div[class="mobile-list-body"]')
    data = [i.text for i in soup]
    fc_data = []
    for code, name, count in zip(range(0, len(data), 4), range(1, len(data), 4), range(2, len(data), 4)):
        tmp = {'code': data[code], 'name': cc.convert(data[name]), 'holdingCount': int(data[count].replace(',', ''))}
        fc_data.append(tmp)

    for i in whole_pool:
        for j in fc_data:
            if i['name'] == j['name']:
                j['code'] = i['code']
    return fc_data


def FC_history_Query(holding_date):
    # 外资历史持股数据查询
    exchanges = ['sh', 'sz']
    fc_total = []
    for i in exchanges:
        data = foreignCapitalHistoryHolding(i, holding_date=holding_date)
        fc_total += data
    return fc_total


def foreign_capital_add_weight():
    # 外资最近一周加仓或新进的个股
    history_data = FC_history_Query(date.today()-timedelta(days=30))
    print(history_data)
    new_data = FC_history_Query(date.today()-timedelta(days=1))
    # history_codes = [i['code'] for i in history_data]
    # new_codes = [i['code'] for i in new_data]
    # new_here = [i for i in new_codes if i not in history_codes]
    # print(f"I am new here.", new_here)
    result = []
    for i in new_data:
        for j in history_data:
            if i['code'] == j['code']:
                if i['holdingCount'] > j['holdingCount']:
                    result.append(i)
    return result


