import requests
import json
import time

class SecurityException(BaseException):
    pass

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
    except SecurityException() as e:
        print(e)
        return None


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
    response = requests.post(url, headers=headers, params=params, data=json.dumps(body)).json()
    # print(json.dumps(response, indent=4, ensure_ascii=False))


def get_interval_yield(code, days=250):
    # 查询区间收益率
    data = get_stock_kline(code, limit=days+1)
    current_price = data[-1]['close']
    data = data[:-1]
    highest = max([i['close'] for i in data])
    momentum = round(current_price/highest, 3)
    interval_yield = round((data[-1]['close']-data[0]['last_close'])/data[0]['last_close']*100, 2)
    return {'code': code, 'interval_yield': interval_yield, 'momentum': momentum}

