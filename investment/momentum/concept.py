# encoding: utf-8
# 概念及行业板块 RPS  资料来源: 陶博士
import json
import os
import time
import requests
import tushare as ts
import numpy as np
import pandas as pd
from datetime import date, timedelta
from momentum import CONCEPT_LIST
pro = ts.pro_api("b625f0b90069039346d199aa3c0d5bc53fd47212437337b45ba87487")
rps_days = [5, 10, 20, 60]
day = 150
begin = int(str(date.today()-timedelta(days=day)).replace('-', ''))
today = int(str(date.today()).replace('-', ''))


class SecurityException(BaseException):
    pass


def get_industry_list():
    url = "http://63.push2.eastmoney.com/api/qt/clist/get"
    params = {
        'cb': 'jQuery112404742947900780148_1629014352777',
        'pn': 1,
        'pz': 350,
        'po': 1,
        'np': 1,
        'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
        'fltt': 2,
        'invt': 2,
        'fid': 'f3',
        'fs': "m:90 t:2 f:!50",
        'fields': "f12,f14,f2",
        '_': int(time.time()*1000)
    }
    response = requests.get(url, params=params).text
    response = response.split('(')[1].split(')')[0]
    response = json.loads(response)
    industry_list = []
    if 'data' in response.keys():
        if 'diff' in response['data'].keys():
            response = response['data']['diff']
            for i in response:
                industry_list.append({'code': i['f12'], 'name': i['f14']})
    return industry_list


def get_concept_list():
    url = "http://89.push2.eastmoney.com/api/qt/clist/get"
    params = {
        'cb': 'jQuery112409358425433864748_1629007955206',
        'pn': 1,
        'pz': 350,
        'po': 1,
        'np': 1,
        'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
        'fltt': 2,
        'invt': 2,
        'fid': 'f3',
        'fs': "m:90 t:3 f:!50",
        'fields': "f12,f14,f2",
        '_': int(time.time()*1000)
    }
    response = requests.get(url, params=params).text
    response = response.split('(')[1].split(')')[0]
    response = json.loads(response)
    concept_list = []
    if 'data' in response.keys():
        if 'diff' in response['data'].keys():
            response = response['data']['diff']
            for i in response:
                concept_list.append({'code': i['f12'], 'name': i['f14']})
    return concept_list


def get_concept_kline(code, period=101, limit=20):
    assert period in (5, 15, 30, 60, 101, 102, 103)
    url = f"http://push2his.eastmoney.com/api/qt/stock/kline/get"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
    }
    params = {
        'cb': "jQuery11240671737283431526_1624931273440",
        'secid': f"90.{code}",
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
                data = []
                tmp_data = []
                for i in range(len(r)):
                    tmp = {}
                    current_data = r[i].split(',')
                    tmp['day'] = current_data[0]
                    tmp['close'] = float(current_data[2])
                    # df.loc['trade_date', 0] = tmp['day']
                    # df.loc[tmp['day'], 'close'] = tmp['close']
                    tmp['high'] = float(current_data[3])
                    tmp['low'] = float(current_data[4])
                    temp = [tmp['day'], tmp['close']]
                    # if i > 0:
                    #     tmp['last_close'] = float(r[i - 1].split(',')[2])
                    # data.append(tmp)
                    tmp_data.append(temp)
                # df = pd.DataFrame(tmp_data, columns=['trade_date', 'close'], dtype=float)
                df = pd.DataFrame(tmp_data, columns=['trade_date', 'close'], index=[i[0] for i in tmp_data])
                # return data[1:]
                return df.close
    except SecurityException() as e:
        print(e)
        return None


def get_all_data(stock_list):
    # 构建一个空的 dataframe 用来装数据, 获取列表中所有股票指定范围内的收盘价格
    data = pd.DataFrame()
    count = 0
    filename = f'daily_data{day}.csv'
    if filename in os.listdir(os.curdir):
        os.remove(filename)
    for i in stock_list:
        code = i.get('code')
        data[code] = get_concept_kline(code, limit=day)
        print(code, i.get('name'), count)
        count += 1
    data.index_col = 0
    data.to_csv(filename, encoding='utf-8')


# 计算收益率
def cal_ret(df, w=5):
    # w:周5;月20;半年：120; 一年250
    df = df / df.shift(w) - 1
    return df.iloc[w:, :].fillna(0)


# 计算RPS
def get_RPS(ser):
    df = pd.DataFrame(ser.sort_values(ascending=False))
    df['n'] = range(1, len(df) + 1)
    df['rps'] = (1 - df['n'] / len(df)) * 100
    return df


# 计算每个交易日所有股票滚动w日的RPS
def all_RPS(data):
    dates = data.index
    # dates = (data.index).strftime('%Y%m%d')
    RPS = {}
    for i in range(len(data)):
        RPS[dates[i]] = pd.DataFrame(get_RPS(data.iloc[i]).values, columns=['收益率', '排名', 'RPS'],
                                     index=get_RPS(data.iloc[i]).index)
    return RPS


# 获取所有股票在某个期间的RPS值
def all_data(rps, ret):
    df = pd.DataFrame(np.NaN, columns=ret.columns, index=ret.index)
    for date in ret.index:
        date = date.strftime('%Y%m%d')
        d = rps[date]
        for c in d.index:
            df.loc[date, c] = d.loc[c, 'RPS']
    return df


def fill_in_data(df, filename="RPS.csv"):
    rps_df = pd.DataFrame()
    if filename in os.listdir(os.curdir):
        os.remove(filename)
    for k, v in df.items():
        print(k)
        for code, rps in zip(v.index, v.values):
            rps_df.loc[code, 'NAME'] = [i.get('name') for i in CONCEPT_LIST if i.get('code') == code][0]
            rps_df.loc[code, k] = round(float(rps[-1]), 2)
    rps_df.to_csv(filename, encoding='utf-8')


def run():
    get_all_data(CONCEPT_LIST)
    data = pd.read_csv(f'daily_data{day}.csv', encoding='utf-8', index_col=0)
    data.index = pd.to_datetime(data.index, format='%Y%m%d', errors='ignore')
    for rps_day in rps_days:
        ret = cal_ret(data, w=rps_day)
        rps = all_RPS(ret)
        fill_in_data(rps, filename=f'plate_RPS_{rps_day}.csv')
    get_main_up()


def get_main_up():
    files = [f"plate_RPS_{i}.csv" for i in rps_days]
    rps90 = []
    for i in files:
        f = pd.read_csv(i, encoding='utf-8')
        for j in f.values:
            if j[-1] >= 90:
                rps90.append((j[0], j[1]))
    sets = set()
    for i in rps90:
        if rps90.count(i) >= 3:
            sets.add(i)
    [print(i[0], i[1]) for i in sets]


if __name__ == "__main__":
    run()


