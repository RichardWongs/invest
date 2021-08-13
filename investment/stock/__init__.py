import json
import time
import requests
from datetime import date, datetime


def get_stock_kline(code, period=101, limit=120, is_index=False):
    assert period in (5, 15, 30, 60, 101, 102, 103)
    if is_index:
        if str(code).startswith('0'):
            secid = f'0.{code}'
        elif str(code).startswith('3'):
            secid = f'1.{code}'
    else:
        if str(code)[0] in ('0', '1', '3'):
            secid = f'0.{code}'
        else:
            secid = f'1.{code}'
    url = f"http://67.push2his.eastmoney.com/api/qt/stock/kline/get"
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
        r = requests.get(url, params=params).text
        r = r.split('(')[1].split(')')[0]
        r = json.loads(r)
        if 'data' in r.keys():
            if isinstance(r['data'], dict) and 'klines' in r['data'].keys():
                r = r['data']['klines']
                data = []
                for i in range(len(r)):
                    tmp = {}
                    current_data = r[i].split(',')
                    tmp['day'] = current_data[0]
                    tmp['close'] = float(current_data[2])
                    tmp['high'] = float(current_data[3])
                    tmp['low'] = float(current_data[4])
                    if i > 0:
                        tmp['last_close'] = float(r[i - 1].split(',')[2])
                    data.append(tmp)
                return data[1:]
    except Exception() as e:
        print(e)
        return None
