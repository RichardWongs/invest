# encoding: utf-8
import json
import logging
import pickle
import tushare as ts
from datetime import date, timedelta
from RPS.stock_pool import NEW_STOCK_LIST
from RPS.holding import fund_holding, fc_holding
from monitor import get_stock_kline_with_indicators, get_market_data
from monitor.whole_market import RedisConn
start_date = int(str(date.today()-timedelta(days=400)).replace('-', ''))


def saveMarketData2Redis():
    # 查询全市场股票行情数据存储到redis中
    N = 20
    day = 1
    client = RedisConn()
    key = f"stock:momentum:*"
    keys = client.keys(key)
    keys = [i.decode() for i in keys]
    counter = 1
    for k, v in NEW_STOCK_LIST.items():
        if f"stock:momentum:{k}" not in keys:
            kline = get_market_data(k)
            if len(kline) > 0:
                if len(kline) > 20:
                    v['applies_20'] = round((kline[-day]['close']-kline[-(N+day)]['close'])/kline[-(N+day)]['close'], 2)
                else:
                    v['applies_20'] = round((kline[-day]['close']-kline[0]['close'])/kline[0]['close'], 2)
                v['kline'] = kline
                client.set(f"stock:momentum:{k}", json.dumps(v))
            print(counter, v)
            counter += 1


def saveMarketData2Local():
    client = RedisConn()
    keys = [i.decode() for i in client.keys(f"stock:momentum:*")]
    target = []
    for i in keys:
        target.append(json.loads(client.get(i)))
    with open("MomentumMarketData.bin", 'wb') as f:
        f.write(pickle.dumps(target))


def find_institutions_holding():
    # 剔除基金持股小于2%或外资持股小于0.5%的个股
    pool = {}
    f = fund_holding + fc_holding
    for i in f:
        pool[i['code']] = i
    return pool


def find_high_rps_stock():
    # 剔除20日RPS强度小于85的个股
    with open("MomentumMarketData.bin", 'rb') as f:
        content = pickle.loads(f.read())
        stockCount = int(len(content)*0.15)
        result = []
        for i in content:
            del i['kline']
            result.append(i)
        result = sorted(result, key=lambda x: x['applies_20'], reverse=True)
        return result[:stockCount]


def find_new_stock(pool):
    # 剔除上市不足一个月的新股
    target = []
    for i in pool:
        if int(i['list_date']) < int(str(date.today()-timedelta(30)).replace('-', '')):
            target.append(i)
    return target


def week52_new_high():
    # 统计当日创下一年新高的数量
    target = []
    with open("MomentumMarketData.bin", 'rb') as f:
        content = pickle.loads(f.read())
        for i in content:
            if len(i['kline']) > 250:
                kline = i['kline'][-250:]
            else:
                kline = i['kline']
            highest = max([i['high'] for i in kline])
            if highest == kline[-1]['high']:
                del i['kline']
                target.append(i)
        return target


def industry_distribution():
    # 全市场个股行业分布统计
    r = []
    for _, v in NEW_STOCK_LIST.items():
        if v['industry']:
            r.append(v['industry'])
    s = set(r)
    t = {}
    for i in s:
        t[i] = r.count(i)
    return t


def plate_statistical():
    # 主线板块统计
    rps_pool = find_high_rps_stock()
    rps_pool = find_new_stock(rps_pool)
    institution_pool = find_institutions_holding()
    result = []
    for i in rps_pool:
        if i['code'] in institution_pool.keys():
            result.append(i)
    industrys = [i['industry'] for i in result]
    industrySet = set(industrys)
    target = []
    t = industry_distribution()
    for i in industrySet:
        count = industrys.count(i)
        total_count = t[i]
        tmp = {'industry': i, 'score': round(count*count/total_count, 2),
               'pool': [f"{j['code']}-{j['name']}" for j in result if j['industry'] == i]}
        target.append(tmp)
    return sorted(target, key=lambda x: x['score'], reverse=True)




