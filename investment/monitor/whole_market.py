# encoding: utf-8
import pickle
import time
import json
import requests
from RPS.RPS_DATA import pro
from RPS.stock_pool import STOCK_LIST


class SecurityException(BaseException):
    pass


def get_stock_kline(code, is_index=False, period=101, limit=120):
    time.sleep(0.5)
    assert period in (5, 15, 30, 60, 101, 102, 103)
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
                new_data = {}
                for i in r:
                    tmp = {'day': i[0], 'volume': float(i[6]), 'applies': float(i[8])}
                    new_data[i[0]] = tmp
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


def save_whole_market_data():
    s = STOCK_LIST
    with open("whole_market.bin", "wb") as f:
        result = {}
        counter = 0
        for i in s:
            counter += 1
            print(i, counter)
            code = i['code'].split('.')[0]
            data = get_stock_kline(code, period=103, limit=250)
            result[code] = {'code': code, 'name': i['name'], 'industry': i['industry'], 'kline': data}
        f.write(pickle.dumps(result))


# with open("whole_market.bin", "rb") as f:
#     content = f.read()
#     content = pickle.loads(content)
#     for _, v in content.items():
#         print(v['kline'])





