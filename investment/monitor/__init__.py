# 股票异常情况监控
import requests, json, time


# 计算平均值
def mean(x):
    return sum(x) / len(x)


# 计算每一项数据与均值的差
def de_mean(x):
    x_bar = mean(x)
    return [x_i - x_bar for x_i in x]


# 辅助计算函数 dot product 、sum_of_squares
def dot(v, w):
    return sum(v_i * w_i for v_i, w_i in zip(v, w))


def sum_of_squares(v):
    return dot(v, v)


# 方差
def variance(x):
    n = len(x)
    deviations = de_mean(x)
    return sum_of_squares(deviations) / (n - 1)


# 标准差
def standard_deviation(x):
    import math
    return math.sqrt(variance(x))


# 协方差
def covariance(x, y):
    n = len(x)
    return dot(de_mean(x), de_mean(y)) / (n - 1)


# 相关系数
def correlation(x, y):
    stdev_x = standard_deviation(x)
    stdev_y = standard_deviation(y)
    if stdev_x > 0 and stdev_y > 0:
        return covariance(x, y) / stdev_x / stdev_y
    else:
        return 0


class SecurityException(BaseException):
    pass


def TRI(high, low, close):
    return round(max(high, close) - min(low, close), 3)


def get_stock_kline_with_indicators(code, is_index=False, period=101, limit=120):
    # 携带技术指标布林线,布林线宽度
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
                        new_data[i]['last_close'] = new_data[i - 1]['close']
                        new_data[i]['TRI'] = TRI(new_data[i]['high'], new_data[i]['low'], new_data[i]['last_close'])
                    if i > 10:
                        tenth_volume = []
                        ATR_10 = 0
                        for j in range(i - 1, i - 11, -1):
                            tenth_volume.append(new_data[j]['volume'])
                            ATR_10 += new_data[j]['TRI']
                        new_data[i]['ATR_10'] = round(ATR_10 / 10, 2)
                        new_data[i]['10th_largest'] = max(tenth_volume)
                        new_data[i]['10th_minimum'] = min(tenth_volume)
                        new_data[i]['avg_volume'] = sum(tenth_volume) / 10
                        new_data[i]['volume_ratio'] = round(new_data[i]['volume'] / new_data[i]['avg_volume'], 2)
                    if i > 20:
                        ATR_20 = 0
                        for j in range(i - 1, i - 21, -1):
                            ATR_20 += new_data[j]['TRI']
                        new_data[i]['ATR_20'] = round(ATR_20 / 20, 2)
                kline = BooleanLine(new_data[1:])
                kline = RSI(kline)
                return kline
    except SecurityException() as e:
        print(e)
        return None


def BooleanLine(kline: list):
    N = 20
    assert len(kline) > N
    for i in range(len(kline)):
        if i >= N:
            closes = []
            for j in range(i, i - N, -1):
                closes.append(kline[j]['close'])
            ma20 = round(sum(closes) / N, 2)
            BBU = ma20 + 2 * standard_deviation(closes)  # 布林线上轨
            BBL = ma20 - 2 * standard_deviation(closes)  # 布林线下轨
            BBW = (BBU - BBL) / ma20
            kline[i]['BBU'] = round(BBU, 2)
            kline[i]['BBL'] = round(BBL, 2)
            kline[i]['BBW'] = round(BBW, 2)
            # print(f"20日移动均线:{ma20}\t标准差:{standard_deviation(closes)}\t布林线上轨:{kline[i]['BBU']}\t布林线下轨:{kline[i]['BBL']}\t布林线宽度:{kline[i]['BBW']}")
    return kline


def RSI(data: list):
    assert data, "data 不能为空"
    rsi_day = 14
    up = [i if i > 0 else 0 for i in [i["applies"] for i in data[:14]]]
    down = [i * -1 if i < 0 else 0 for i in [i["applies"] for i in data[:14]]]
    smooth_up_14 = sum(up) / len(up)
    smooth_down_14 = sum(down) / len(down)
    new_data = []
    for i in range(len(data)):
        tmp_list = {}
        tmp_list["date"] = data[i]["day"]
        up_column = data[i]["applies"] if data[i]["applies"] > 0 else 0
        tmp_list["up_column"] = up_column
        down_column = data[i]["applies"] * -1 if data[i]["applies"] < 0 else 0
        tmp_list["down_column"] = down_column
        if i == 13:
            smooth_up = smooth_up_14
            smooth_down = smooth_down_14
        elif i > 13:
            smooth_up = (new_data[i - 1]["smooth_up"] * (rsi_day - 1) + up_column) / rsi_day
            smooth_down = (new_data[i - 1]["smooth_down"] * (rsi_day - 1) + down_column) / rsi_day
        else:
            smooth_up = smooth_down = None
        tmp_list["smooth_up"] = smooth_up
        tmp_list["smooth_down"] = smooth_down
        relative_intensity = smooth_up / smooth_down if (smooth_up is not None or smooth_down is not None) else None
        tmp_list["relative_intensity"] = relative_intensity
        if relative_intensity:
            tmp_list["RSI"] = round(100 - (100 / (1 + relative_intensity)), 2)
        new_data.append(tmp_list)
        for j in data:
            if j['day'] == tmp_list['date'] and 'RSI' in tmp_list.keys():
                j['RSI'] = tmp_list['RSI']
    return data



