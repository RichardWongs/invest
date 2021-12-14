# encoding: utf-8
import logging
import pickle
import time
import json

import redis
import requests
from RPS.RPS_DATA import pro
from monitor import EMA_V2, BooleanLine
from RPS.stock_pool import STOCK_LIST


def RedisConn():
    client = redis.Redis(host="172.16.1.162", port=6379, db=0)
    return client


class SecurityException(BaseException):
    pass


def get_stock_kline_with_indicators(code, is_index=False, period=101, limit=120):
    time.sleep(0.5)
    assert period in (1, 5, 15, 30, 60, 101, 102, 103)
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
                # new_data = {}
                for i in r:
                    i = {'day': i[0], 'open': float(i[1]), 'close': float(i[2]),
                         'high': float(i[3]), 'low': float(i[4]), 'VOL': int(i[5]),
                         'volume': float(i[6]), 'applies': float(i[8])}
                    new_data.append(i)
                    # new_data[i['day'].replace('-', '')] = i
                return new_data
    except SecurityException() as e:
        print(e)
        return None


def select_whole_market_stock():
    df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,industry,list_date')
    codes = df.ts_code.values
    names = df.name.values
    industrys = df.industry.values
    stock_list = []
    for code, name, industry in zip(codes, names, industrys):
        tmp = {'code': code, 'name': name, 'industry': industry}
        stock_list.append(tmp)
    return stock_list


def save_whole_market_data_to_redis():
    result = {}
    counter = 0
    client = RedisConn()
    for i in STOCK_LIST:
        counter += 1
        print(i, counter)
        code = i['code'].split('.')[0]
        data = get_stock_kline_with_indicators(code, period=103, limit=120)
        tmp = {'code': code, 'name': i['name'], 'industry': i['industry'], 'kline': data}
        result[code] = tmp
        client.set(f"stock:monthly:{code}", json.dumps(tmp))


def save_market_data_from_redis():
    filename = "weekly_kline.bin"
    with open(filename, 'wb') as f:
        klines = []
        client = RedisConn()
        keys = client.keys("stock:weekly:*")
        for k in keys:
            data = client.get(k).decode()
            data = json.loads(data)
            if not data['kline']:
                print(data['code'])
                continue
            data['kline'] = EMA_V2(EMA_V2(data['kline'], days=10), days=30)
            klines.append(data)
        f.write(pickle.dumps(klines))


# save_whole_market_data_to_redis()
# save_market_data_from_redis()
# (28.3, 4.13)
def read_weekly_kline():
    with open("weekly_kline.bin", 'rb') as f:
        content = f.read()
        content = pickle.loads(content)
        counter = 1
        for i in content:
            kline = i['kline']
            if len(kline) >= 53 and round((kline[-1]["close"] - kline[-53]['close']) / kline[-53]['close'] * 100,
                                          2) >= 28.3:
                if kline[-1]['close'] > kline[-1]['ema30'] > kline[-2]['ema30']:
                    kline = BooleanLine(kline)
                    if 0.3 >= kline[-1]["BBW"] > kline[-2]['BBW'] >= kline[-3]['BBW']:
                        i['kline'] = kline[-1]
                        print(counter, i)
                        counter += 1


def read_monthly_kline(month="20211130"):
    with open("monthly_kline.bin", 'rb') as f:
        content = f.read()
    content = pickle.loads(content)
    counter = 1
    result = []
    for i in content:
        if month in i['kline'].keys():
            result.append({'code': i['code'], 'name': i['name'], 'volume': i["kline"][month]["volume"]})
            counter += 1
    result = sorted(result, key=lambda x: x['volume'], reverse=True)
    return result


def VolumeStatistical(month):
    data = read_monthly_kline(month=month)
    totalVolume = sum([i['volume'] for i in data])
    topCount = int(len(data)*0.05)
    topCountVolume = sum([i['volume'] for i in data[:topCount]])
    topCountStock = [i['name'] for i in data[:topCount]]
    logging.warning(f"日期: {month}\t全市场总成交量: {totalVolume}\t成交量前5%个股总成交量: {topCountVolume}\t成交量占比: {round(topCountVolume/totalVolume, 2)}\t{len(topCountStock)}\t{topCountStock}")


m = ['20110930', '20111031', '20111130', '20111230', '20120131', '20120229', '20120330', '20120427', '20120531', '20120629',
         '20120731', '20120831', '20120928', '20121031', '20121130', '20121231', '20130131', '20130228', '20130329', '20130426',
         '20130531', '20130628', '20130731', '20130830', '20130930', '20131031', '20131129', '20131231', '20140130', '20140228',
         '20140331', '20140430', '20140530', '20140630', '20140731', '20140829', '20140930', '20141031', '20141128', '20141231',
         '20150130', '20150227', '20150331', '20150430', '20150529', '20150630', '20150731', '20150807', '20160129', '20160229',
         '20160331', '20160429', '20160531', '20160617', '20160729', '20160831', '20160930', '20161031', '20161130', '20161230',
         '20170126', '20170228', '20170331', '20170428', '20170531', '20170630', '20170731', '20170831', '20170929', '20171031',
         '20171130', '20171229', '20180131', '20180228', '20180330', '20180427', '20180531', '20180629', '20180731', '20180831',
         '20180928', '20181031', '20181130', '20181228', '20190131', '20190228', '20190329', '20190430', '20190531', '20190628',
         '20190731', '20190830', '20190930', '20191031', '20191129', '20191231', '20200123', '20200228', '20200331', '20200430',
         '20200529', '20200630', '20200731', '20200831', '20200930', '20201030', '20201130', '20201231', '20210129', '20210226',
         '20210331', '20210430', '20210531', '20210630', '20210730', '20210831', '20210930', '20211029', '20211130', '20211213']


