# encoding: utf-8
import pickle
import time
import json

import redis
import requests
from RPS.RPS_DATA import pro
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
    from monitor import EMA_V2
    filename = "monthly_kline.bin"
    with open(filename, 'wb') as f:
        klines = []
        client = RedisConn()
        keys = client.keys("stock:monthly:*")
        for k in keys:
            data = client.get(k).decode()
            data = json.loads(data)
            if not data['kline']:
                print(data['code'])
                continue
            # data = EMA_V2(EMA_V2(data['kline'], days=10), days=30)
            klines.append(data)
        f.write(pickle.dumps(klines))


# save_whole_market_data_to_redis()
# save_market_data_from_redis()




