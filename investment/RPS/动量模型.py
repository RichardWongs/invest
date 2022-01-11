# encoding: utf-8
import json
import logging
import os
import pickle
from datetime import date, timedelta

from RPS.holding import fund_holding, fc_holding
from RPS.stock_pool import NEW_STOCK_LIST
from monitor import get_market_data, MA_V2
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
    limit = 1600
    count = 0
    fileNO = 1
    lastOne = json.loads(client.get(keys[-1]))
    for i in keys:
        target.append(json.loads(client.get(i)))
        count += 1
        if count >= limit or json.loads(client.get(i)) == lastOne:
            with open(f"MomentumMarketData-{fileNO}.bin", 'wb') as f:
                f.write(pickle.dumps(target))
            fileNO += 1
            count = 0
            target = []


def readMarketDataFromLocal():
    # 从本地文件中读取行情数据
    files = os.listdir(os.curdir)
    target = []
    for i in files:
        if i.startswith('MomentumMarketData'):
            with open(i, 'rb') as f:
                content = pickle.loads(f.read())
                target += content
    return target


def find_institutions_holding():
    # 剔除基金持股小于2%或外资持股小于0.5%的个股
    pool = {}
    f = fund_holding + fc_holding
    for i in f:
        pool[i['code']] = i
    return pool


def find_high_rps_stock():
    # 剔除20日RPS强度小于85的个股
    content = readMarketDataFromLocal()
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
    content = readMarketDataFromLocal()
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


def find_trend_pool():
    from stock.StockFinancial import read_quarter_report
    quarter = read_quarter_report()  # 季报正增长
    for i in quarter:
        i['code'] = f"{i['code']}.SH" if i['code'].startswith('6') else f"{i['code']}.SZ"
    tmp = find_institutions_holding()
    ins = []    # 机构&外资持股
    for _, v in tmp.items():
        ins.append(v)
    result = [i for i in ins if i in quarter]
    k = readMarketDataFromLocal()
    movements = []
    for i in k:
        kline = MA_V2(MA_V2(MA_V2(i['kline'], 50), 150), 200)
        highest = max([i['high'] for i in kline])
        lowest = min([i['low'] for i in kline])
        close = kline[-1]['close']
        if close > kline[-1]['ma50'] > kline[-1]['ma150'] > kline[-1]['ma200']:
            if close > lowest * 1.3 and close > highest * 0.75:
                movements.append({'code': i['code'], 'name': i['name']})
    print(len(result), result)
    print(len(movements), movements)
    results = [i for i in result if i in movements]
    print(len(results), results)


def run():
    # 主线板块统计
    rps_pool = find_high_rps_stock()
    rps_pool = find_new_stock(rps_pool)
    institution_pool = find_institutions_holding()
    result = []
    for i in rps_pool:
        if i['code'] in institution_pool.keys():
            result.append(i)
    all_new_high = week52_new_high()
    institution_new_high = [i for i in result if i in all_new_high]
    print(f"全市场创新高个股数量:{len(all_new_high)}\t机构动量榜个股数量:{len(result)}\t创新高个股数量:{len(institution_new_high)}")
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
    target = sorted(target, key=lambda x: x['score'], reverse=True)
    for i in target:
        logging.warning(i)
    return target


def run_v2():
    from momentum.concept import get_concept_list, get_industry_list, select_composition_stock
    CONCEPT_LIST = get_concept_list() + get_industry_list()
    rps_pool = find_high_rps_stock()
    rps_pool = find_new_stock(rps_pool)
    institution_pool = find_institutions_holding()
    result = []
    for i in rps_pool:
        if i['code'] in institution_pool.keys():
            result.append(i)
    for i in CONCEPT_LIST:
        i['score'] = 0
        i['momentumPool'] = []
        i['pool'] = select_composition_stock(i['code'])
        tmp_name = [i['name'] for i in i['pool']]
        i['momentumPool'] = [f"{i['code']}-{i['name']}" for i in result if i['name'] in tmp_name]
        i['score'] = round(len(i['momentumPool'])*len(i['momentumPool'])/len(i['pool']), 2)
    CONCEPT_LIST = sorted(CONCEPT_LIST, key=lambda x: x['score'], reverse=True)
    for i in CONCEPT_LIST:
        del i['pool']
        if i['score'] >= 1:
            logging.warning(i)
    return CONCEPT_LIST


if __name__ == "__main__":
    # saveMarketData2Redis()
    # saveMarketData2Local()
    # run()
    # run_v2()
    find_trend_pool()
