import requests
import json
import time


class SecurityException(BaseException):
    pass


def get_average_price(closes, days):
    assert len(closes) >= days
    if isinstance(closes[-1], dict):
        closes = [i['close'] for i in closes]
    return sum(closes[-days:])/days


def get_stock_kline(code, is_index=False, period=101, limit=120):
    # time.sleep(0.5)
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
                new_data = {'code': r['data']['code'], 'name': r['data']['name'], 'kline': []}
                r = r['data']['klines']
                data = []
                for i in range(len(r)):
                    tmp = {}
                    current_data = r[i].split(',')
                    tmp['day'] = current_data[0]
                    tmp['close'] = float(current_data[2])
                    tmp['high'] = float(current_data[3])
                    tmp['low'] = float(current_data[4])
                    tmp['volume'] = float(current_data[6])
                    tmp['applies'] = float(current_data[8])
                    if i > 0:
                        tmp['last_close'] = float(r[i - 1].split(',')[2])
                    data.append(tmp)
                new_data['kline'] = data[1:]
                # return data[1:]
                return new_data
    except SecurityException() as e:
        print(e)
        return None


def get_stock_kline_with_volume(code, is_index=False, period=101, limit=120):
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
                new_data = []
                for i in r:
                    i = {'day': i[0], 'open': float(i[1]), 'close': float(i[2]),
                         'high': float(i[3]), 'low': float(i[4]), 'volume': float(i[6]),
                         'applies': float(i[8])}
                    new_data.append(i)
                for i in range(len(new_data)):
                    if i > 0:
                        new_data[i]['last_close'] = new_data[i-1]['close']
                    if i > 10:
                        tenth_volume = []
                        for j in range(i-1, i-11, -1):
                            tenth_volume.append(new_data[j]['volume'])
                        new_data[i]['10th_largest'] = max(tenth_volume)
                        new_data[i]['10th_minimum'] = min(tenth_volume)
                        new_data[i]['avg_volume'] = sum(tenth_volume)/10
                        new_data[i]['volume_ratio'] = round(new_data[i]['volume'] / new_data[i]['avg_volume'], 2)
                return new_data[1:]
    except SecurityException() as e:
        print(e)
        return None


def get_price(code):
    data = get_stock_kline_with_volume(code, limit=250)
    close = data[-1]['close']
    highest = max([i['high'] for i in data[:-1]])
    momentum = round(close / highest, 2)
    return close, momentum


def send_dingtalk_message(message):
    url = "https://oapi.dingtalk.com/robot/send"
    headers = {'Content-Type': 'application/json'}
    params = {
        'access_token': 'fa4cee8e6c94d8bef582caf47f22b326cf32d617d867ec7bbe611cc50b0729f8'
    }
    body = {
        'msgtype': 'text',
        'text': {'content': message}
    }
    response = requests.post(
        url,
        headers=headers,
        params=params,
        data=json.dumps(body)).json()
    # print(json.dumps(response, indent=4, ensure_ascii=False))


def get_interval_yield(code, days=250):
    # 查询区间收益率
    data = get_stock_kline_with_volume(code, limit=days + 1)
    current_price = data[-1]['close']
    data = data[:-1]
    highest = max([i['high'] for i in data])
    momentum = round(current_price / highest, 3)
    interval_yield = round(
        (data[-1]['close'] - data[0]['last_close']) / data[0]['last_close'] * 100, 2)
    return {'code': code, 'interval_yield': interval_yield, 'momentum': momentum}


# data = get_stock_kline_with_volume('000829')
# for i in data:
#     if 'volume_ratio' in i.keys() and i['volume_ratio']:
#         print(f"日期: {i['day']}\t涨跌幅: {i['applies']}\t成交量比值: {i['volume_ratio']}")


