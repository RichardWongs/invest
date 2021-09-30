# encoding: utf-8
# 动量模型核心教程  资料来源: 简放
import json
import os
import time
import logging
from datetime import date, timedelta
import numpy as np
import pandas as pd
import tushare as ts
from momentum import STOCK_LIST
pro = ts.pro_api("b625f0b90069039346d199aa3c0d5bc53fd47212437337b45ba87487")
begin_date = int(str(date.today() - timedelta(days=180)).replace('-', ''))
today = int(str(date.today()).replace('-', ''))
day = 180   # 上市时间满半年
rps_day = 20


def get_stock_list():
    # 获取沪深股市股票列表, 剔除上市不满一年的次新股
    df = pro.stock_basic(exchange='', list_status='L',
                         fields='ts_code,symbol,name,industry,list_date')  # fields='ts_code,symbol,name,area,industry,'
    df = df[df['list_date'].apply(int).values < begin_date]
    # 获取当前所有非新股次新股代码和名称
    codes = df.ts_code.values
    names = df.name.values
    industrys = df.industry.values
    list_dates = df.list_date.values
    stock_list = []
    for code, name, industry, list_date in zip(codes, names, industrys, list_dates):
        tmp = {'code': code, 'name': name, 'industry': industry, 'list_date': list_date}
        stock_list.append(tmp)
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
    filename = f'daily_price.csv'
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
            rps_df.loc[code, 'LIST_DATE'] = [i.get('list_date') for i in STOCK_LIST if i.get('code') == code][0]
            rps_df.loc[code, k] = round(float(rps[-1]), 2)
    rps_df.to_csv(filename, encoding='utf-8')


def create_RPS_file():
    stocks = get_stock_list()  # 获取全市场股票列表
    get_all_data(stocks)  # 获取行情数据并写入csv文件
    data = pd.read_csv(f'daily_price.csv', encoding='utf-8', index_col='trade_date')
    data.index = pd.to_datetime(data.index, format='%Y%m%d', errors='ignore')
    ret = cal_ret(data, w=rps_day)
    rps = all_RPS(ret)
    fill_in_data(rps, filename=f'RPS{rps_day}.csv')  # 计算个股20日RPS值并写入rps文件


def get_fund_holdings(quarter, year=date.today().year):
    # 基金持股
    logging.warning("查询基金持股数据")
    pool = []
    data = ts.fund_holdings(year=year, quarter=quarter)
    for i in data.values:
        code = i[7]
        name = i[3]
        fundHoldingdRatio = float(i[6])
        if fundHoldingdRatio >= 2:
            pool.append({'code': code, 'name': name})
    logging.warning(f"基金持股占比大于2%个股数量:{len(pool)}")
    return pool


def get_industry_momentum():
    df = pd.read_csv(f"RPS{rps_day}.csv", encoding='utf-8')
    fund_pool = get_fund_holdings(quarter=2)
    result = {}
    for i in range(4, len(df.columns)):
        all_data = []
        high_data = []
        for j in df.values:
            all_data.append(j[2])
            if j[i] >= 87 and j[3] < int(str(date.today() - timedelta(days=180)).replace('-', '')) \
                    and {'code': j[0].replace('.SH', '').replace('.SZ', ''), 'name': j[1]} in fund_pool:
                high_data.append(j[2])
        all_data_count = {}
        high_data_count = {}
        for j in all_data:
            all_data_count[j] = all_data.count(j)
        for j in high_data:
            high_data_count[j] = high_data.count(j)
        momentum = []
        for j in all_data_count.keys():
            if j in high_data_count.keys():
                tmp = {'industry': j,
                       'rank_count': high_data_count[j],
                       'member_count': all_data_count[j],
                       'momentum_score': round(high_data_count[j] * high_data_count[j] / all_data_count[j], 2)}
                momentum.append(tmp)
        result[df.columns[i]] = sorted(momentum, key=lambda x: x['momentum_score'], reverse=True)
    return result


def run():
    filename = "简放-动量模型.csv"
    if filename in os.listdir(os.curdir):
        os.remove(filename)
    create_RPS_file()
    data = get_industry_momentum()
    df = pd.DataFrame()
    for k, v in data.items():
        for i in v:
            df.loc[i['industry'], k] = i['momentum_score']
    df.to_csv(filename, encoding='utf-8')


def momentum_stock_filter(industry):
    pool = []
    df = pd.read_csv(f'RPS{rps_day}.csv', encoding='utf-8')
    for i in df.values:
        if i[2] == industry and i[-1] > 87:
            pool.append({'code': i[0], 'name': i[1]})
    return pool


def get_momentum_rank_top(filename="简放-动量模型.csv"):
    industry_list = []
    fund_holding = get_fund_holdings(quarter=2)
    print(fund_holding)
    df = pd.read_csv(filename, encoding='utf-8')
    for i in df.values:
        if i[-1] > 1:
            industry_list.append({'industry': i[0], df.columns[-5]: i[-5], df.columns[-4]: i[-4], df.columns[-3]: i[-3], df.columns[-2]: i[-2], df.columns[-1]: i[-1]})
            industry_pool = momentum_stock_filter(i[0])
    industry_list = sorted(industry_list, key=lambda x: x[df.columns[-1]], reverse=True)
    print(industry_list)


if __name__ == '__main__':
    # run()
    get_momentum_rank_top()
    # print(momentum_stock_filter('白酒'))
