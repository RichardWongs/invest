# 笑傲牛熊, 曼斯菲尔德相对强度

class SecurityException(BaseException):
    pass


def get_stock_kline_with_volume(code, is_index=False, period=101, limit=120):
    import time, requests, json
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
                    if i > 52:
                        new_data[i]['day52_applies'] = (new_data[i]['close']-new_data[i-52]['close'])/new_data[i-52]['close']*100
                    else:
                        new_data[i]['day52_applies'] = None

                return new_data[1:]
    except SecurityException() as e:
        print(e)
        return None


def index_applies(limit=120):
    indexes = ['000300', '000905', '399006', '000688']
    applies_120 = 0
    result = []
    for index in indexes:
        data120 = get_stock_kline_with_volume(index, is_index=True, limit=limit)
        pre, current = data120[0]['close'], data120[-1]['close']
        if applies_120 < current/pre:
            applies_120 = current/pre
            result = data120
    return result if result else None


def GET_RSMANSIFIELD(code):
    limit = 250
    index = index_applies(limit=limit)
    print([i['day52_applies'] for i in index])
    data120 = get_stock_kline_with_volume(code, limit=limit)
    print([i['day52_applies'] for i in data120])
    for i in range(len(data120)):
        if data120[i]['day52_applies'] and index[i]['day52_applies']:
            data120[i]['relative_intenity'] = round(data120[i]['day52_applies']/index[i]['day52_applies']-1, 2)
        else:
            data120[i]['relative_intenity'] = None
    print([i['relative_intenity'] for i in data120])


GET_RSMANSIFIELD(601636)
