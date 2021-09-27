# encoding: utf-8
# 股票异常情况监控
import logging
from datetime import date, timedelta
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
    return round(max(high-low, abs(high-close), abs(low-close)), 3)


def ATR(kline: list):
    for i in range(len(kline)):
        kline[i]['TRI'] = TRI(high=kline[i]['high'], low=kline[i]['low'], close=kline[i]['last_close'])
    kline = EMA_V2(EMA_V2(kline, days=10, key='TRI', out_key='ATR_10'), days=20, key='TRI', out_key='ATR_20')
    return kline


def get_stock_kline_with_indicators(code, is_index=False, period=101, limit=120):
    # 添加技术指标布林线,布林线宽度
    time.sleep(1)
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
                        new_data[i]['TRI'] = TRI(high=new_data[i]['high'],
                                                 low=new_data[i]['low'],
                                                 close=new_data[i]['last_close'])
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
                return new_data[1:]
    except SecurityException() as e:
        print(e)
        return None


def get_market_data(code, start_date=20210101):
    from datetime import date, timedelta
    import time
    import tushare as ts
    pro = ts.pro_api("b625f0b90069039346d199aa3c0d5bc53fd47212437337b45ba87487")
    time.sleep(0.1)
    if not (str(code).endswith('.SH') or str(code).endswith('.SZ')):
        if str(code).startswith('6'):
            code = f"{code}.SH"
        else:
            code = f"{code}.SZ"
    start = start_date  # int(str(date.today()-timedelta(days=400)).replace('-', ''))
    end = int(str(date.today()).replace('-', ''))
    pool = []
    df = pro.daily(ts_code=code, start_date=start, end_date=end,
                   fields='trade_date,open,close,high,low,vol,pct_chg,pre_close')
    for i in df.values:
        pool.append({'day': i[0], 'open': i[1], 'close': i[4], 'high': i[2], 'low': i[3],
                     'last_close': i[5], 'applies': i[6], 'volume': i[7]})
    pool = pool[::-1]
    for i in range(len(pool)):
        pool[i]['TRI'] = TRI(pool[i]['high'], pool[i]['low'], pool[i]['last_close'])
        if i > 10:
            tenth_volume = []
            ATR_10 = 0
            for j in range(i - 1, i - 11, -1):
                tenth_volume.append(pool[j]['volume'])
                ATR_10 += pool[j]['TRI']
            pool[i]['ATR_10'] = round(ATR_10 / 10, 2)
            pool[i]['10th_largest'] = max(tenth_volume)
            pool[i]['10th_minimum'] = min(tenth_volume)
            pool[i]['avg_volume'] = sum(tenth_volume) / 10
            pool[i]['volume_ratio'] = round(pool[i]['volume'] / pool[i]['avg_volume'], 2)
        if i > 20:
            ATR_20 = 0
            for j in range(i - 1, i - 21, -1):
                ATR_20 += pool[j]['TRI']
            pool[i]['ATR_20'] = round(ATR_20 / 20, 2)
    return pool[1:]


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


def KDJ(kline: list):
    day = 9
    for i in range(1, len(kline)):
        if i >= day:
            Cn = kline[i]['close']
            prices = []
            for j in range(i, i - day, -1):
                prices.append(kline[j]['high'])
                prices.append(kline[j]['low'])
            Hn = max(prices)
            Ln = min(prices)
            RSV = (Cn - Ln) / (Hn - Ln) * 100
            K = 2 / 3 * kline[i - 1]['K'] + 1 / 3 * RSV
            D = 2 / 3 * kline[i - 1]['D'] + 1 / 3 * K
            J = 3 * K - 2 * D
            kline[i]['K'], kline[i]['D'], kline[i]['J'] = round(K, 2), round(D, 2), round(J, 2)
        else:
            kline[i]['K'], kline[i]['D'] = 50, 50
    for i in range(len(kline)):
        if 'K' in kline[i].keys():
            if kline[i]['K'] > kline[i]['D'] and kline[i - 1]['K'] < kline[i - 1]['D']:
                kline[i]['golden_cross'] = True
            else:
                kline[i]['golden_cross'] = False
    return kline


def RSI_Deviation(data: list):
    # RSI背离
    number = 60
    data = data[13:]
    for i in range(len(data)):
        if i >= number:
            closes = []
            RSI = []
            for j in range(i, i - number, -1):
                closes.append(data[j]['close'])
                RSI.append(data[j]['RSI'])
            max_price = max(closes)
            min_price = min(closes)
            max_rsi = max(RSI)
            min_rsi = min(RSI)
            data[i]['price_high'] = True if data[i]['close'] == max_price else False
            data[i]['rsi_high'] = True if data[i]['RSI'] == max_rsi else False
            data[i]['price_low'] = True if data[i]['close'] == min_price else False
            data[i]['rsi_low'] = True if data[i]['RSI'] == min_rsi else False
            if data[i]['price_high'] != data[i]['rsi_high']:
                # 收盘价与RSI出现顶背离或底背离
                data[i]['deviation'] = 'top'
            elif data[i]['price_low'] != data[i]['rsi_low']:
                data[i]['deviation'] = 'end'
            else:
                data[i]['deviation'] = None
    return data


def EMA(cps, days):
    emas = cps.copy()
    for i in range(len(cps)):
        if i == 0:
            emas[i] = cps[i]
        if i > 0:
            emas[i] = ((days - 1) * emas[i - 1] + 2 * cps[i]) / (days + 1)
    return emas


def EMA_V2(cps, days, key='close', out_key=None):
    if not out_key:
        out_key = f'ema{days}'
    emas = cps.copy()
    for i in range(len(cps)):
        if i == 0:
            emas[i][out_key] = cps[i][key]
        if i > 0:
            emas[i][out_key] = ((days - 1) * emas[i - 1][out_key] + 2 * cps[i][key]) / (days + 1)
    return emas


def WMS(kline, N=30):
    kline = kline[-N:]
    C = kline[-1]['close']
    Hn = max([i['high'] for i in kline])
    Ln = min([i['low'] for i in kline])
    WR30 = (Hn - C) / (Hn - Ln) * 100
    return WR30


def TRIX(data):
    N, M = 12, 20
    for i in range(len(data)):
        if i >= N:
            tmp = []
            for j in range(i, i-N, -1):
                tmp.append(data[j]['close'])
            data[i][f'ma{N}'] = sum(tmp)/len(tmp)
    data = data[12:]
    TR = EMA_V2(EMA_V2(EMA_V2(data, N, key=f'ma{N}'), N, key=f'ma{N}'), N, key=f'ma{N}')
    trix = []
    for i in range(len(TR)):
        if i > 0:
            trix.append(round((TR[i][f'ema{N}'] - TR[i - 1][f'ema{N}']) / TR[i - 1][f'ema{N}'] * 100, 2))
    matrix = []
    for i in range(len(trix)):
        if i >= M:
            tmp = []
            for j in range(i, i - M, -1):
                tmp.append(trix[j])
            matrix.append(round(sum(tmp) / len(tmp), 2))
    trix = trix[-len(matrix):]
    data = data[-len(matrix):]
    print(f"trix:{len(trix)}\tmatrix:{len(matrix)}\tdata:{len(data)}")
    for i in range(len(data)):
        data[i]['TRIX'] = trix[i]
        data[i]['TRMA'] = matrix[i]
    return data


def Linear_Regression(kline: list):
    # 线性回归 y = mx + b  y:因变量, m:斜率, b:截距
    points = []
    x = []
    y = []
    for i in range(1, len(kline) + 1):
        x.append(kline[i - 1]['close'])
        y.append(i)
        points.append({'x': kline[i - 1]['close'], 'y': i})
    x_mean = sum(x) / len(x)
    y_mean = sum(y) / len(y)
    tmp = [k * v for k, v in zip(x, y)]
    x_y_mean = sum(tmp) / len(tmp)
    tmp = [i ** 2 for i in x]
    x_square_mean = sum(tmp) / len(tmp)
    m = (x_y_mean - x_mean * y_mean) / (x_square_mean - x_mean ** 2)
    b = y_mean - m * x_mean
    for i in points:
        i['y_predict'] = m * i['x'] + b
        i['square_error'] = (i['y'] - i['y_predict']) ** 2
        i['square_from_mean_y'] = (i['y'] - y_mean) ** 2
    SE_line = sum([i['square_error'] for i in points])
    SE_y_mean = sum([i['square_from_mean_y'] for i in points])
    R_square = 1 - SE_line / SE_y_mean
    # print(f"R_Square: {round(R_square, 2)}\t斜率: {round(m, 2)}\t截距: {round(b, 2)}")
    return {'R_Square': round(R_square, 2), 'slope': round(m, 2), 'intercept': round(b, 2)}


def KDJ_test(code):
    data = get_stock_kline_with_indicators(code)
    data = KDJ(data)
    for i in range(len(data)):
        if 'K' in data[i].keys():
            if data[i]['K'] > data[i]['D'] and data[i - 1]['K'] < data[i - 1]['D']:
                print(data[i])


def BooleanLine_filter(code, name=None):
    # data = get_stock_kline_with_indicators(code, limit=60)
    data = get_market_data(code, start_date=20200927)
    data = BooleanLine(data)
    if 0.2 >= data[-1]['BBW'] > data[-2]['BBW'] >= data[-3]['BBW']:
        return {'code': code, 'name': name, 'kline': data}
    return None


def RVI(kline: list):
    N = 10
    for i in range(len(kline)):
        kline[i]['Co'] = kline[i]['close'] - kline[i]['open']
        kline[i]['HL'] = kline[i]['high'] - kline[i]['low']
        if i >= 3:
            kline[i]['V1'] = (kline[i]['Co'] + 2 * kline[i - 1]['Co'] + 2 * kline[i - 2]['Co'] + kline[i - 3]['Co']) / 6
            kline[i]['V2'] = (kline[i]['HL'] + 2 * kline[i - 1]['HL'] + 2 * kline[i - 2]['HL'] + kline[i - 3]['HL']) / 6
        if i >= N + 3:
            tmp1, tmp2 = [], []
            for j in range(i, i - N, -1):
                tmp1.append(kline[j]['V1'])
                tmp2.append(kline[j]['V2'])
            S1 = sum(tmp1)
            S2 = sum(tmp2)
            kline[i]['RVI'] = S1 / S2
        if i >= N + 6:
            kline[i]['RVIS'] = (kline[i]['RVI'] + 2 * kline[i - 1]['RVI'] + 2 * kline[i - 2]['RVI'] + kline[i - 3][
                'RVI']) / 6
    return kline


def Keltner_Channel(kline: list):
    # 肯特钠通道
    basic_price = [(i['close'] + i['high'] + i['low']) / 3 for i in kline]
    mid = EMA(basic_price, 20)
    for i in range(len(kline)):
        if 'ATR_10' in kline[i].keys():
            kline[i]['mid_line'] = mid[i]
            kline[i]['on_line'] = mid[i] + 2 * kline[i]['ATR_10']
            kline[i]['under_line'] = mid[i] - 2 * kline[i]['ATR_10']
            if 'mid_line' in kline[i - 1].keys():
                if kline[i]['close'] > kline[i]['mid_line'] > kline[i - 1]['mid_line']:
                    kline[i]['trend'] = 'up'
                elif kline[i]['close'] < kline[i]['mid_line'] < kline[i - 1]['mid_line']:
                    kline[i]['trend'] = 'down'
                else:
                    kline[i]['trend'] = 'shock'
    return kline


def Vegas_Channel(code, name=None):
    # 维加斯通道
    logging.warning(f"Vegas_Channel\t{code}\t{name}")
    long, mid, shot = 169, 144, 12
    kline = get_stock_kline_with_indicators(code, period=60, limit=250)
    kline = EMA_V2(EMA_V2(EMA_V2(kline, long), mid), shot)
    close = kline[-1]['close']
    mid_price = kline[-1][f'ema{mid}']
    long_price = kline[-1][f'ema{long}']
    logging.warning(f"{code}\t{name}\t{kline[-1]}")
    if (close <= mid_price * 1.05 or close <= long_price * 1.05) and (close > mid_price and close > long_price):
        return {'code': code, 'name': name, 'kline': kline}


def linear_regression_stock_filter(limit=120):
    # 根据线性回归函数对个股历史股价进行走势判断, 并计算出决定系数,斜率,截距,排序后返回
    from RPS.quantitative_screening import get_RPS_stock_pool
    pool = get_RPS_stock_pool()
    new_pool = [{'code': i[0], 'name': i[1]} for i in pool]
    start = int(str(date.today()-timedelta(days=365)).replace('-', ''))
    for i in new_pool:
        # kline = get_stock_kline_with_indicators(i['code'], limit=limit)
        kline = get_market_data(i['code'], start_date=start)
        r = Linear_Regression(kline)
        i['R_Square'] = r['R_Square']
        i['slope'] = r['slope']
        i['intercept'] = r['intercept']
        logging.warning(f"{i['code']}\t{i['name']}\t{i['R_Square']}\t{i['slope']}\t{i['intercept']}")
    return sorted(new_pool, key=lambda x: x['R_Square'], reverse=True)


def filter_stock_by_boolean_and_keltner_channel():
    # 通过布林线指标及肯特纳通道进行个股筛选
    from RPS.quantitative_screening import get_RPS_stock_pool
    pool = get_RPS_stock_pool()
    new = []
    for i in pool:
        data = BooleanLine_filter(i[0], name=i[1])
        if data:
            kline = Keltner_Channel(data['kline'])
            data['kline'] = kline
            if kline[-1]['trend'] == 'up':
                logging.warning(f"{i[0]}\t{i[1]}\t{kline}")
                new.append(data)
    for i in new:
        logging.warning(f"{i['code']}\t{i['name']}")
    return new


def CCI(kline: list):
    N = 14
    for i in range(len(kline)):
        kline[i]['TP'] = (kline[i]['high'] + kline[i]['low'] + kline[i]['close'])/3
        if i >= N:
            tmp = []
            for j in range(i, i-N, -1):
                tmp.append(kline[j]['close'])
            kline[i][f'ma{N}'] = sum(tmp)/len(tmp)
        if i >= 2 * N:
            tmp = []
            for j in range(i, i-N, -1):
                tmp.append(abs(kline[j][f'ma{N}']-kline[j]['close']))
            kline[i]['MD'] = sum(tmp)/len(tmp)
            kline[i]['CCI'] = (kline[i]['TP']-kline[i][f'ma{N}'])/kline[i]['MD']/0.015
    return kline


def MACD(kline: list):
    kline = EMA_V2(EMA_V2(EMA_V2(kline, days=12), days=26), days=50)
    for i in range(len(kline)):
        kline[i]['DIF'] = kline[i]['ema12'] - kline[i]['ema26']
    kline = EMA_V2(kline, days=9, key='DIF', out_key='DEA')
    for i in range(len(kline)):
        kline[i]['MACD'] = 2 * (kline[i]['DIF'] - kline[i]['DEA'])
    return kline


data = get_market_data('300750', start_date=20200101)
data = MACD(data)
for i in range(len(data)):
    close = data[i]['close']
    ema50 = data[i]['ema50']
    if data[i]['DIF'] < 0 and data[i]['DEA'] < 0:
        if data[i]['DIF'] > data[i]['DEA'] and data[i-1]['DIF'] < data[i-1]['DEA']:
            logging.warning(f"day: {data[i]['day']}\tDIF: {data[i]['DIF']}\tDEA: {data[i]['DEA']}")
    # print(data[i])

