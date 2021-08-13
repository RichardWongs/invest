# encoding: utf-8
# 量化选股流程  思路来源: 陶博士
import os
import pandas as pd
import tushare as ts
from datetime import date, datetime, timedelta
import requests
import json
import time
import logging
from RPS.foreign_capital_increase import foreign_capital_filter
from security import get_interval_yield
pro = ts.pro_api("b625f0b90069039346d199aa3c0d5bc53fd47212437337b45ba87487")


def get_fund_holdings(quarter, year=date.today().year):
    # 基金持股
    logging.warning("查询基金持股数据")
    pool = set()
    data = ts.fund_holdings(year=year, quarter=quarter)
    for i in data.values:
        code = i[7]
        name = i[3]
        fundHoldingdRatio = float(i[6])
        if fundHoldingdRatio >= 3:
            pool.add((code, name))
    return pool


def foreignCapitalHolding():
    # 外资持股清单(持股市值超过3000万)
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
    foreignCapital_pool = set()
    for i in response:
        code = i.get('SCode')
        name = i.get('SName')
        holding_market_value = round(i.get('ShareSZ')/100000000, 2)
        if holding_market_value > 0.3:
            foreignCapital_pool.add((code, name))
    return foreignCapital_pool


def get_industry_momentum_value():
    # 板块20日动量分值排行
    df = pd.read_csv("RPS20.csv", encoding='utf-8')
    all_data = []
    data = []
    for i in df.values:
        all_data.append(i[2])
        if i[-1] >= 87:
            # tmp = {'code': i[0], 'name': i[1], 'industry': i[2], 'RPS20': i[-1]}
            data.append(i[2])

    all_data_count = {}
    data_count = {}
    for i in all_data:
        all_data_count[i] = all_data.count(i)
    for i in data:
        data_count[i] = data.count(i)
    momentum = []
    for i in all_data_count.keys():
        if i in data_count.keys():
            # print(f"板块:{i}\t上榜数量:{data_count[i]}\t成分数量:{all_data_count[i]}\t")
            # print(f"板块:{i}\t动量分值:{round(data_count[i]*data_count[i]/all_data_count[i], 2)}")
            momentum.append({'industry': i, 'momentum_value': round(data_count[i]*data_count[i]/all_data_count[i], 2)})
    sorted_momentum = sorted(momentum, key=lambda x: x['momentum_value'], reverse=True)
    [print(i) for i in sorted_momentum]
    return sorted_momentum


def get_RPS_stock_pool():
    # 根据RPS值进行第一步筛选
    logging.warning("根据RPS查询股池")
    pool = set()
    files = ['RPS50.csv', 'RPS120.csv', 'RPS250.csv']
    for file in files:
        df = pd.read_csv(file, encoding='utf-8')
        for i in df.values:
            if i[-1] >= 90:
                pool.add((i[0].split('.')[0], i[1]))
    return pool


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
    if len(closes) < 1:
        logging.error(code, closes)
    close = closes[-1]
    highest = max(closes[:-1])
    momentum = round(close / highest, 3)
    interval_yield = round((closes[-1] - closes[0]) / closes[0] * 100, 2)
    return {'code': code, 'interval_yield': interval_yield, 'momentum': momentum}


def close_one_year_high(codes):
    # 接近一年新高
    logging.warning("股价接近一年新高")
    pool = []
    for i in codes:
        data = get_interval_yield(i[0])
        if data['momentum'] > 0.9:
            pool.append(i)
    return pool


def stock_pool_filter_process():
    rps_pool = get_RPS_stock_pool()
    fund_pool = get_fund_holdings(2)
    foreigncapital_pool = foreignCapitalHolding()
    pool = fund_pool.union(foreigncapital_pool)
    pool = [i for i in pool if i in rps_pool]
    pool = close_one_year_high(pool)
    new_pool = []
    [new_pool.append({'code': i[0], 'name': i[1]}) for i in pool]
    fc_add = foreign_capital_filter()
    result = [i for i in new_pool if i in fc_add]
    print(result)


if __name__ == '__main__':
    stock_pool_filter_process()


