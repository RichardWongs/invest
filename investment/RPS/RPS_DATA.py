# encoding: utf-8
import logging
import os
import sys
import time
from datetime import date, timedelta, datetime
import numpy as np
import pandas as pd
import tushare as ts
from RPS.stock_pool import STOCK_LIST, NEW_STOCK_LIST
pro = ts.pro_api("b625f0b90069039346d199aa3c0d5bc53fd47212437337b45ba87487")
day = 400   # 上市时间满一年
rps_days = [20, 50, 120, 250]
begin_date = int(str(date.today() - timedelta(days=day)).replace('-', ''))
today = int(str(date.today()).replace('-', ''))


def get_stock_list():
    # 获取沪深股市股票列表, 剔除上市不满一年的次新股
    df = pro.stock_basic(exchange='', list_status='L',
                         fields='ts_code,symbol,name,industry,list_date')  # fields='ts_code,symbol,name,area,industry,'
    df = df[df['list_date'].apply(int).values < begin_date]
    # 获取当前所有非新股次新股代码和名称
    codes = df.ts_code.values
    names = df.name.values
    industrys = df.industry.values
    stock_list = []
    for code, name, industry in zip(codes, names, industrys):
        tmp = {'code': code, 'name': name, 'industry': industry}
        stock_list.append(tmp)
    return stock_list


def get_stock_list_V2():
    # 获取沪深股市股票列表, 剔除上市不满一年的次新股
    df = pro.stock_basic(exchange='', list_status='L',
                         fields='ts_code,symbol,name,industry,list_date')  # fields='ts_code,symbol,name,area,industry,'
    df = df[df['list_date'].apply(int).values < begin_date]
    # 获取当前所有非新股次新股代码和名称
    codes = df.ts_code.values
    names = df.name.values
    industrys = df.industry.values
    stock_list = {}
    for code, name, industry in zip(codes, names, industrys):
        tmp = {'code': code, 'name': name, 'industry': industry}
        stock_list[code] = tmp
    return stock_list


def get_data(code, start=begin_date, end=today):
    # 按照日期范围获取股票交易日期,收盘价
    time.sleep(0.1)
    df = pro.daily(ts_code=code, start_date=start, end_date=end, fields='trade_date,close')
    # 将交易日期设置为索引值
    df.index = pd.to_datetime(df.trade_date)
    df = df.sort_index()
    return df.close


def get_all_data(stock_list):
    # 构建一个空的 dataframe 用来装数据, 获取列表中所有股票指定范围内的收盘价格
    data = pd.DataFrame()
    count = 0
    filename = f'daily_data.csv'
    if filename in os.listdir(os.curdir):
        os.remove(filename)
    for i in stock_list:
        code = i.get('code')
        data[code] = get_data(code)
        print(code, i.get('name'), count)
        count += 1
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
            rps_df.loc[code, 'NAME'] = [i.get('name') for i in STOCK_LIST if i.get('code') == code][0]
            rps_df.loc[code, 'INDUSTRY'] = [i.get('industry') for i in STOCK_LIST if i.get('code') == code][0]
            rps_df.loc[code, k] = round(float(rps[-1]), 2)
    rps_df.to_csv(filename, encoding='utf-8')


def run():
    start = int(time.time())
    stock_list = get_stock_list()
    get_all_data(stock_list)
    data = pd.read_csv(f'daily_data.csv', encoding='utf-8', index_col='trade_date')
    data.index = pd.to_datetime(data.index, format='%Y%m%d', errors='ignore')
    for rps_day in rps_days:
        ret = cal_ret(data, w=rps_day)
        rps = all_RPS(ret)
        fill_in_data(rps, filename=f'RPS{rps_day}.csv')
    end = int(time.time())
    minutes = int((end - start) / 60)
    seconds = (end - start) % 60
    logging.warning(f"总耗时: {minutes}分{seconds}秒")


def fill_in_data_V2(df, filename):
    rps_df = pd.DataFrame()
    if filename in os.listdir(os.curdir):
        os.remove(filename)
    for k, v in df.items():
        print(k)
        for code, rps in v.items():
            rps_df.loc[code, 'NAME'] = NEW_STOCK_LIST[code]['name']
            rps_df.loc[code, 'INDUSTRY'] = NEW_STOCK_LIST[code]['industry']
            rps_df.loc[code, k] = rps['RPS']
    rps_df.to_csv(filename, encoding='utf-8')


def run_V2():
    if str(get_data("600519.SH").index[-1]).split(" ")[0] != str(date.today()):
        logging.error(f"行情数据未更新,请稍后执行!")
        sys.exit()
    start = int(time.time())
    stock_list = get_stock_list()
    assert len(NEW_STOCK_LIST) >= len(stock_list), "NEW_STOCK_LIST列表不完整, 请先更新"
    get_all_data(stock_list)
    data = pd.read_csv(f'daily_data.csv', encoding='utf-8', index_col='trade_date')
    data.index = pd.to_datetime(data.index, format='%Y%m%d', errors='ignore')
    for rps_day in rps_days:
        ret = cal_ret(data, w=rps_day)
        rps = all_RPS(ret)
        new_rps = {}
        for k, v in rps.items():
            tmp = {}
            for i in range(len(v)):
                tmp[v.index[i]] = {'code': v.index[i], 'RPS': round(v.values[i][-1], 2)}
            new_rps[k] = tmp
        fill_in_data_V2(new_rps, filename=f'RPS_{rps_day}_V2.csv')
    end = int(time.time())
    minutes = int((end - start) / 60)
    seconds = (end - start) % 60
    logging.warning(f"总耗时: {minutes}分{seconds}秒")


if __name__ == "__main__":
    run_V2()

