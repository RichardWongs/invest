# encoding: utf-8
# 股票异常情况监控
import logging
from datetime import date, timedelta
import requests, json, time
from RPS.quantitative_screening import *
from RPS import TrendStock, Beautiful, YeChengStock, Zulu, smart_car, smart_car2
from momentum.concept import select_composition_stock
from RPS.stock_pool import NEW_STOCK_LIST
import colorama
from colorama import Fore, Back, Style

colorama.init()


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


def get_code_by_name(name: str):
    for _, i in NEW_STOCK_LIST.items():
        if name == i['name']:
            return i['code']


def get_name_by_code(code):
    if '.S' in str(code):
        return NEW_STOCK_LIST[code]['name']
    else:
        code = f"{code}.SH" if str(code).startswith('6') else f"{code}.SZ"
        return NEW_STOCK_LIST[code]['name']


def get_industry_by_code(code):
    code = str(code).split('.')[0]
    assert str(code)[0] in ('0', '3', '6')
    code = f"{code}.SH" if str(code).startswith('6') else f"{code}.SZ"
    if code not in NEW_STOCK_LIST.keys():
        logging.warning(f"{code} not in NEW_STOCK_LIST.")
        return None
    return NEW_STOCK_LIST[code]['industry']


def TRI(high, low, close):
    return round(max(high - low, abs(high - close), abs(low - close)), 3)


def ATR(kline: list):
    for i in range(len(kline)):
        kline[i]['TRI'] = TRI(high=kline[i]['high'], low=kline[i]['low'], close=kline[i]['last_close'])
        highest, tmp = 0, []
        for j in range(i, i - 40, -1):
            tmp.append(kline[j]['high'])
        kline[i]['highest'] = max(tmp)
    kline = EMA_V2(EMA_V2(kline, days=10, key='TRI', out_key='ATR_10'), days=20, key='TRI', out_key='ATR_20')
    for i in range(len(kline)):
        kline[i]['stopLossPrice'] = round(kline[i]['highest'] - 2 * kline[i]['ATR_20'], 2)
    return kline


def Compact_Structure(kline: list):
    # 根据方差值判断个股结构紧凑程度
    # kline 最好为周K线,N>=4, 方差值越小,代表结构越紧凑
    N = 20
    for i in range(len(kline)):
        if i > 0:
            kline[i]['v'] = kline[i]['close'] / kline[i - 1]['close'] - 1
        if i > N:
            tmp = []
            for j in range(i, i - N, -1):
                tmp.append(kline[j]['v'])
            kline[i]['variance'] = round(variance(tmp) * 1000, 2)
    for i in range(len(kline)):
        if 'v' in kline[i].keys():
            del kline[i]['v']
    return kline


def get_stock_kline_with_indicators(code, is_index=False, period=101, limit=120):
    if '.' in str(code):
        code = str(code).split('.')[0]
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
                for i in r:
                    i = {'day': i[0], 'open': float(i[1]), 'close': float(i[2]),
                         'high': float(i[3]), 'low': float(i[4]), 'VOL': int(i[5]),
                         'volume': float(i[6]), 'applies': float(i[8])}
                    new_data.append(i)
                day = 10
                for i in range(len(new_data)):
                    if i > 0:
                        new_data[i]['last_close'] = new_data[i - 1]['close']
                        new_data[i]['TRI'] = TRI(high=new_data[i]['high'],
                                                 low=new_data[i]['low'],
                                                 close=new_data[i]['last_close'])
                    if i > day:
                        tenth_volume = []
                        for j in range(i - 1, i - (day + 1), -1):
                            tenth_volume.append(new_data[j]['volume'])
                        new_data[i]['10th_largest'] = max(tenth_volume)
                        new_data[i]['10th_minimum'] = min(tenth_volume)
                        new_data[i]['avg_volume'] = sum(tenth_volume) / len(tenth_volume)
                        new_data[i]['volume_ratio'] = round(new_data[i]['volume'] / new_data[i]['avg_volume'], 2)
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
    day = 10
    for i in range(len(pool)):
        pool[i]['TRI'] = TRI(pool[i]['high'], pool[i]['low'], pool[i]['last_close'])
        if i > day:
            tenth_volume = []
            for j in range(i - 1, i - (day + 1), -1):
                tenth_volume.append(pool[j]['volume'])
            pool[i]['10th_largest'] = max(tenth_volume)
            pool[i]['10th_minimum'] = min(tenth_volume)
            pool[i]['avg_volume'] = sum(tenth_volume) / len(tenth_volume)
            pool[i]['volume_ratio'] = round(pool[i]['volume'] / pool[i]['avg_volume'], 2)
        if i >= 50:
            tmp = []
            for j in range(i, i - 50, -1):
                tmp.append(pool[j]['close'])
            pool[i]['ma50'] = sum(tmp) / len(tmp)
    return pool[1:]


def BooleanLine(kline: list, N=20):
    assert len(kline) > N
    for i in range(len(kline)):
        if i >= N:
            closes = []
            for j in range(i, i - N, -1):
                closes.append(kline[j]['close'])
            ma20 = round(sum(closes) / N, 2)
            kline[i]['MID'] = ma20
            BBU = ma20 + 2 * standard_deviation(closes)  # 布林线上轨
            BBL = ma20 - 2 * standard_deviation(closes)  # 布林线下轨
            # kline[i]['BBU_minus'] = ma20 + 1 * standard_deviation(closes)
            # kline[i]['BBL_minus'] = ma20 - 1 * standard_deviation(closes)
            BBW = (BBU - BBL) / ma20
            kline[i]['BBU'] = round(BBU, 2)
            kline[i]['BBL'] = round(BBL, 2)
            kline[i]['BBW'] = round(BBW, 2)
    return kline[N:]


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


def MA(kline, N):
    if len(kline) >= N:
        for i in range(len(kline)):
            if i >= N:
                tmp = []
                for j in range(i, i - N, -1):
                    tmp.append(kline[j]['close'])
                kline[i][f'MA{N}'] = round(sum(tmp) / len(tmp), 2)
    return kline


def MA_V2(kline: list, N, key="close"):
    assert len(kline) > N
    for i in range(len(kline)):
        if i >= N:
            tmp = []
            for j in range(i, i - N, -1):
                tmp.append(kline[j][key])
            if key == "close":
                kline[i][f'ma{N}'] = round(sum(tmp) / len(tmp), 2)
            else:
                kline[i][f'ma_{key}_{N}'] = round(sum(tmp) / len(tmp), 2)
        else:
            kline[i][f'ma{N}'] = kline[i]['close']
    return kline


def EMA(cps, days):
    emas = cps.copy()
    for i in range(len(cps)):
        if i == 0:
            emas[i] = cps[i]
        if i > 0:
            emas[i] = round(((days - 1) * emas[i - 1] + 2 * cps[i]) / (days + 1), 2)
    return emas


def EMA_V2(cps, days, key='close', out_key=None):
    if not out_key:
        out_key = f'ema{days}'
    emas = cps.copy()
    for i in range(len(cps)):
        if i == 0:
            emas[i][out_key] = cps[i][key]
        if i > 0:
            emas[i][out_key] = round(((days - 1) * emas[i - 1][out_key] + 2 * cps[i][key]) / (days + 1), 2)
    return emas


def WMS(kline, N=30):
    kline = kline[-N:]
    C = kline[-1]['close']
    Hn = max([i['high'] for i in kline])
    Ln = min([i['low'] for i in kline])
    WR30 = (Hn - C) / (Hn - Ln) * 100
    return WR30


def William(kline: list, N=14):
    for i in range(len(kline)):
        if i >= N:
            high_price, low_price = [], []
            for j in range(i, i - N, -1):
                high_price.append(kline[j]['high'])
                low_price.append(kline[j]['low'])
            highest = max(high_price)
            lowest = min(low_price)
            close = kline[i]['close']
            kline[i]['%R'] = (highest - close) / (highest - lowest) * -100
    return kline[N:]


def DMI(kline: list):
    for i in range(len(kline)):
        if i > 0:
            kline[i]['+DM'] = kline[i]['high'] - kline[i - 1]['high'] if kline[i]['high'] - kline[i - 1][
                'high'] > 0 else 0
            kline[i]['-DM'] = kline[i - 1]['low'] - kline[i]['low'] if kline[i - 1]['low'] - kline[i]['low'] > 0 else 0
            kline[i]['TR'] = TRI(kline[i]['high'], kline[i]['low'], kline[i - 1]['close'])


def TRIX(kline: list):
    N, M = 12, 20
    kline = EMA_V2(EMA_V2(EMA_V2(kline, N), N, key=f'ema{N}'), N, key=f'ema{N}')
    for i in range(len(kline)):
        if i > 0:
            kline[i]['TRIX'] = round((kline[i][f'ema{N}'] - kline[i - 1][f'ema{N}']) / kline[i - 1][f'ema{N}'] * 100, 2)
        if i >= M:
            tmp = []
            for j in range(i, i - M, -1):
                tmp.append(kline[j]['TRIX'])
            kline[i]['TRIXMA'] = round(sum(tmp) / len(tmp), 2)
    return kline


def DMA(kline: list):
    N, M = 10, 50
    for i in range(len(kline)):
        if i >= 10:
            tmp = []
            for j in range(i, i - N, -1):
                tmp.append(kline[j]['close'])
            kline[i][f'ma{N}'] = sum(tmp) / len(tmp)
        if i >= M:
            tmp2 = []
            for j in range(i, i - M, -1):
                tmp2.append(kline[j]['close'])
            kline[i][f'ma{M}'] = sum(tmp2) / len(tmp2)
            kline[i]['DMA'] = round(kline[i][f'ma{N}'] - kline[i][f'ma{M}'], 2)
        if i >= M + N:
            tmp3 = []
            for j in range(i, i - N, -1):
                tmp3.append(kline[j]['DMA'])
            kline[i]['AMA'] = round(sum(tmp3) / len(tmp3), 2)
        if f'ma{N}' in kline[i].keys():
            del kline[i][f'ma{N}']
        if f'ma{M}' in kline[i].keys():
            del kline[i][f'ma{M}']
    return kline[M + N:]


def Linear_Regression(kline: list, key="close"):
    # 线性回归 y = mx + b  y:因变量, m:斜率, b:截距
    points = []
    x = []
    y = []
    for i in range(1, len(kline) + 1):
        x.append(kline[i - 1][key])
        y.append(i)
        points.append({'x': kline[i - 1][key], 'y': i})
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
    start = int(str(date.today() - timedelta(days=365)).replace('-', ''))
    for i in new_pool:
        kline = get_stock_kline_with_indicators(i['code'], limit=limit)
        # kline = get_market_data(i['code'], start_date=start)
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


def BBI(kline: list):
    for i in range(len(kline)):
        if i >= 3:
            tmp = []
            for j in range(i, i - 3, -1):
                tmp.append(kline[j]['close'])
            kline[i]['ma3'] = sum(tmp) / len(tmp)
        if i >= 6:
            tmp = []
            for j in range(i, i - 6, -1):
                tmp.append(kline[j]['close'])
            kline[i]['ma6'] = sum(tmp) / len(tmp)
        if i >= 12:
            tmp = []
            for j in range(i, i - 12, -1):
                tmp.append(kline[j]['close'])
            kline[i]['ma12'] = sum(tmp) / len(tmp)
        if i >= 24:
            tmp = []
            for j in range(i, i - 24, -1):
                tmp.append(kline[j]['close'])
            kline[i]['ma24'] = sum(tmp) / len(tmp)
    for i in range(len(kline)):
        if i >= 24:
            kline[i]['BBI'] = round((kline[i]['ma3'] + kline[i]['ma6'] + kline[i]['ma12'] + kline[i]['ma24']) / 4, 2)
        if 'ma3' in kline[i].keys():
            del kline[i]['ma3']
        if 'ma6' in kline[i].keys():
            del kline[i]['ma6']
        if 'ma12' in kline[i].keys():
            del kline[i]['ma12']
        if 'ma24' in kline[i].keys():
            del kline[i]['ma24']
    return kline


def CCI(kline: list):
    N = 14
    for i in range(len(kline)):
        kline[i]['TP'] = (kline[i]['high'] + kline[i]['low'] + kline[i]['close']) / 3
        if i >= N:
            tmp = []
            for j in range(i, i - N, -1):
                tmp.append(kline[j]['close'])
            kline[i][f'ma{N}'] = sum(tmp) / len(tmp)
        if i >= 2 * N:
            tmp = []
            for j in range(i, i - N, -1):
                tmp.append(abs(kline[j][f'ma{N}'] - kline[j]['close']))
            kline[i]['MD'] = sum(tmp) / len(tmp)
            kline[i]['CCI'] = (kline[i]['TP'] - kline[i][f'ma{N}']) / kline[i]['MD'] / 0.015
    return kline


def MACD(kline: list):
    N, M = 12, 26
    kline = EMA_V2(EMA_V2(EMA_V2(kline, days=N), days=M), days=50)
    for i in range(len(kline)):
        kline[i]['DIF'] = kline[i][f'ema{N}'] - kline[i][f'ema{M}']
    kline = EMA_V2(kline, days=9, key='DIF', out_key='DEA')
    for i in range(len(kline)):
        kline[i]['MACD'] = 2 * (kline[i]['DIF'] - kline[i]['DEA'])
        if i > 0:
            if kline[i]['MACD'] > kline[i - 1]['MACD'] and kline[i]['DIF'] >= kline[i - 1]['DIF']:
                kline[i]['macd_direction'] = 'UP'
            if kline[i]['MACD'] > kline[i - 1]['MACD'] and kline[i]['DIF'] < kline[i - 1]['DIF']:
                kline[i]['macd_direction'] = 'UP-'
            else:
                kline[i]['macd_direction'] = 'DOWN'
    return kline


def WAD(kline: list):
    # 威廉多空力度线
    for i in range(len(kline)):
        if i > 0:
            kline[i]['TRL'] = min(kline[i - 1]['close'], kline[i]['low'])
            kline[i]['TRH'] = max(kline[i - 1]['close'], kline[i]['high'])
            if kline[i]['close'] > kline[i - 1]['close']:
                kline[i]['AD'] = kline[i]['close'] - kline[i]['TRL']
            if kline[i]['close'] < kline[i - 1]['close']:
                kline[i]['AD'] = kline[i]['close'] - kline[i]['TRH']
            if kline[i]['close'] == kline[i - 1]['close']:
                kline[i]['AD'] = 0
            kline[i]['WAD'] = round(kline[i]['AD'] + kline[i - 1]['WAD'], 2)
        else:
            kline[i]['WAD'] = 0
        if i >= 30:
            tmp = []
            for j in range(i, i - 30, -1):
                tmp.append(kline[j]['WAD'])
            kline[i]['MAWAD'] = round(sum(tmp) / len(tmp), 2)
    for i in kline:
        if 'TRL' in i.keys():
            del i['TRL']
            del i['TRH']
            del i['AD']
    return kline[30:]


def PVI_NVI(kline: list):
    N = 20
    for i in range(len(kline)):
        if i == 0:
            kline[i]['PVI'] = 100
            kline[i]['NVI'] = 100
        if i > 0:
            kline[i]['PV'] = kline[i]['close'] / kline[i - 1]['close'] if kline[i]['volume'] > kline[i - 1][
                'volume'] else 1
            kline[i]['NV'] = kline[i]['close'] / kline[i - 1]['close'] if kline[i]['volume'] < kline[i - 1][
                'volume'] else 1
            kline[i]['PVI'] = kline[i - 1]['PVI'] * kline[i]['PV']
            kline[i]['NVI'] = kline[i - 1]['NVI'] * kline[i]['NV']
        if i >= N:
            tmp_pvi = []
            tmp_nvi = []
            for j in range(i, i - N, -1):
                tmp_pvi.append(kline[j]['PVI'])
                tmp_nvi.append(kline[j]['NVI'])
            kline[i]['MA_PVI'] = round(sum(tmp_pvi) / len(tmp_pvi), 2)
            kline[i]['MA_NVI'] = round(sum(tmp_nvi) / len(tmp_nvi), 2)
    return kline[N:]


def PVT(kline: list):
    for i in range(len(kline)):
        if i > 0:
            kline[i]['PVT'] = (kline[i]['close'] - kline[i - 1]['close']) / kline[i - 1]['close'] * kline[i]['VOL']
        if i > 1:
            kline[i]['PVT'] = kline[i]['PVT'] + kline[i - 1]['PVT']
            if kline[i]['close'] < kline[i - 1]['close'] and kline[i]['PVT'] > kline[i - 1]['PVT']:
                kline[i]['PVT_SIG'] = "BUY"
            if kline[i]['close'] > kline[i - 1]['close'] and kline[i]['PVT'] < kline[i - 1]['PVT']:
                kline[i]['PVT_SIG'] = "SELL"
    return kline[1:]


def OBV(kline: list):
    for i in range(len(kline)):
        if i == 0:
            kline[i]['OBV'] = kline[i]['volume']
        else:
            if kline[i]['close'] > kline[i - 1]['close']:
                kline[i]['OBV'] = kline[i - 1]['OBV'] + kline[i]['volume']
            elif kline[i]['close'] < kline[i - 1]['close']:
                kline[i]['OBV'] = kline[i - 1]['OBV'] - kline[i]['volume']
            else:
                pass
    return kline


def Force_Index(kline: list):
    N, M = 2, 13
    for i in range(len(kline)):
        if i > 0:
            kline[i]['FI'] = kline[i]['VOL'] * (kline[i]['close'] - kline[i - 1]['close'])
    kline = kline[1:]
    kline = EMA_V2(EMA_V2(kline, N, key="FI", out_key=f"FI_EMA_{N}"), M, key="FI", out_key=f"FI_EMA_{M}")
    return kline


def Kaufman_Adaptive_Moving_Average(kline: list):
    N = 10
    fast = 2
    slow = 30
    kline = EMA_V2(EMA_V2(kline, fast), slow)
    for i in range(len(kline)):
        if i > N:
            DIRECTION = abs(kline[i]['close'] - kline[i - N]['close'])  # 方向
            tmp = []
            for j in range(i, i - N, -1):
                tmp.append(abs(kline[j]['close'] - kline[j - 1]['close']))
            VOLATILITY = sum(tmp)  # 波动率
            ER = abs(DIRECTION / VOLATILITY)  # 效率
            FAST_SC = fast / (fast + 1)
            SLOW_SC = slow / (slow + 1)
            SSC = ER * (FAST_SC - SLOW_SC) + SLOW_SC
            CONSTANT = SSC * SSC
            print(f"CONSTANT:{CONSTANT}")
    return kline


def KAMA(kline, N=10, NF=2, NS=30):
    direction = [0 for _ in range(len(kline))]
    for i in range(len(kline)):
        if i >= N:
            direction[i] = kline[i]['close'] - kline[i - N]['close']
    volatility = [0 for _ in range(len(kline))]
    delt = [0 for _ in range(len(kline))]
    for i in range(1, len(kline)):
        delt[i] = abs(kline[i]['close'] - kline[i - 1]['close'])
    for i in range(N - 1, len(kline)):
        sum = 0
        for j in range(N):
            sum = sum + delt[i - N + 1 + j]
        volatility[i] = sum

    fastest = 2 / (NF + 1)
    slowest = 2 / (NS + 1)

    ER = [0 for _ in range(len(kline))]
    smooth = [0 for _ in range(len(kline))]
    c = [0 for _ in range(len(kline))]

    for i in range(N, len(kline)):
        ER[i] = abs(direction[i] / volatility[i])
        smooth[i] = ER[i] * (fastest - slowest) + slowest
        c[i] = smooth[i] * smooth[i]

    ama = [0 for _ in range(len(kline))]
    ama[N - 1] = kline[N - 1]['close']
    for i in range(N, len(kline)):
        ama[i] = ama[i - 1] + c[i] * (kline[i]['close'] - ama[i - 1])
        kline[i]['KAMA'] = round(ama[i], 2)
    return kline[N:]


def pocket_protection(kline: list):
    # 口袋支点公式
    assert len(kline) >= 250
    close = kline[-1]['close']
    max_5 = max([i['close'] for i in kline[-5:]])
    ma50 = kline[-1]['ma50']
    if biggest_decline_calc(kline) < 50 and close == max_5 and close > ma50:
        # 半年内最大跌幅小于50% 收盘价创5日新高 收盘价大于50日均价
        if (kline[-1]['applies'] >= 5 and kline[-1]['volume'] > kline[-1]['10th_largest']) or kline[-1][
            'applies'] > 9.9:
            # 当日涨幅大于5%,成交量超过最近10日最大成交量 股价当日涨停则成交量不做要求
            highest_250 = [i['high'] for i in kline[-250:]]
            lowest_15 = [i['low'] for i in kline[-15:]]
            lowest_50 = [i['low'] for i in kline[-50:]]
            return True


def pocket_protection_V2(kline: list):
    close = kline[-1]['close']
    H250 = max(i['high'] for i in kline[-250:])
    high, low, kline = calc_v(kline)
    L40 = min(i['low'] for i in kline[-40:])
    if L40 > high / 2 or close >= H250:
        if round((high - low) / high * 100, 2) < 46:
            # 半年内最大跌幅小于50% 收盘价创5日新高 收盘价大于50日均价
            if (kline[-1]['applies'] >= 5 and kline[-1]['volume'] > kline[-1]['10th_largest']) \
                    or kline[-1]['applies'] > 9.9:
                # 当日涨幅大于5%,成交量超过最近10日最大成交量 股价当日涨停则成交量不做要求
                return True


def calc_v(kline: list):
    # 计算最近半年最大调整幅度
    assert len(kline) >= 120
    kline = kline[-120:]
    close = kline[-1]['close']
    max_price = {'day': '', 'high': 0}
    for j in kline:
        if j['high'] > max_price['high']:
            max_price['day'] = j['day']
            max_price['high'] = j['high']
    high = max_price['high']
    for j in range(len(kline)):
        if max_price['day'] == kline[j]['day']:
            kline = kline[j:]
            break
    low = min([j['low'] for j in kline])
    # biggest_decline = round((high - low)/high * 100, 2)
    return high, low, kline


def BIAS(kline: list):
    N = 18
    A1 = 0.15
    for i in range(len(kline)):
        if i >= N:
            tmp = []
            for j in range(i, i - N, -1):
                tmp.append(kline[j]['close'])
            kline[i]['BIAS1'] = round(kline[i]['close'] / (sum(tmp) / len(tmp)) - 1, 2)
            kline[i]['BIAS2'] = kline[i]['BIAS1'] * (1 + A1)
            kline[i]['BIAS3'] = kline[i]['BIAS1'] * (1 - A1)
    return kline


def ARBR(kline: list):
    N = 42
    for i in range(len(kline)):
        if i >= N:
            AR1, AR2 = [], []
            for j in range(i, i - N, -1):
                AR1.append(kline[j]['high'] - kline[j]['close'])
                AR2.append(kline[j]['open'] - kline[j]['low'])
            kline[i]['AR'] = round(sum(AR1) / sum(AR2), 2)
        if i > N:
            BR1, BR2 = [], []
            for j in range(i, i - N, -1):
                BR1.append(kline[j]['high'] - kline[j - 1]['close'])
                BR2.append(kline[j - 1]['close'] - kline[j]['low'])
            kline[i]['BR'] = round(sum(BR1) / sum(BR2), 2)
    return kline[N:]


def MTM(kline: list):
    N, M = 2, 30
    for i in range(len(kline)):
        if i >= N:
            kline[i]['MTM'] = round(kline[i]['close'] - kline[i - N]['close'], 2)
    kline = kline[N:]
    for i in range(len(kline)):
        if i >= M:
            tmp = []
            for j in range(i, i - M, -1):
                tmp.append(kline[j]['MTM'])
            kline[i]['MTMMA'] = round(sum(tmp) / len(tmp), 2)
    return kline[M:]


def MFI(kline: list):
    N = 14
    for i in range(len(kline)):
        kline[i]['TYP'] = round((kline[i]['high'] + kline[i]['low'] + kline[i]['close']) / 3, 2)
        if i > 0:
            if kline[i]['TYP'] > kline[i - 1]['TYP']:
                kline[i]['in_amount'] = kline[i]['TYP'] * kline[i]['volume']
                kline[i]['out_amount'] = 0
            else:
                kline[i]['in_amount'] = 0
                kline[i]['out_amount'] = kline[i]['TYP'] * kline[i]['volume']
        if i >= N:
            tmp_in, tmp_out = [], []
            for j in range(i, i - N, -1):
                tmp_in.append(kline[i]['in_amount'])
                tmp_out.append(kline[i]['out_amount'])
            print(sum(tmp_in), sum(tmp_out))
            # kline[i]['V1'] = sum(tmp_in)/sum(tmp_out)
    return kline


def stock_filter_by_pocket_protection():
    from RPS.quantitative_screening import institutions_holding_rps_stock
    logging.warning(f"stock filter by pocket protection !")
    pool = institutions_holding_rps_stock()
    result = []
    for i in pool:
        data = get_stock_kline_with_indicators(i['code'], limit=150)
        if pocket_protection(data):
            i['industry'] = get_industry_by_code(i['code'])
            result.append(i)
            logging.warning(f"{i}")
    return result


def stock_filter_by_MACD_and_BBI(period=101, limit=150):
    logging.warning(f"stock filter by MACD and BBI !")
    pool = institutions_holding_rps_stock()
    result = []
    for i in pool:
        data = get_stock_kline_with_indicators(i['code'], period=period, limit=limit)
        data = ATR(data)
        data = BBI(MACD(data))
        if data[-1]['MACD'] < 0 and data[-1]['macd_direction'] == "UP" and data[-2]['macd_direction'] == "DOWN":
            i['industry'] = get_industry_by_code(i['code'])
            i['applies'] = data[-1]['applies']
            i['volume'] = data[-1]['volume']
            i['10th_largest'] = data[-1]['10th_largest']
            result.append(i)
    return result


def stock_filter_by_MACD_and_BBI_V2(pool: list):
    result = []
    for i in pool:
        data = i['kline']
        data = ATR(data)
        data = BBI(MACD(data))
        target = {}
        if data[-1]['MACD'] < 0 and data[-1]['macd_direction'] == "UP" and data[-2]['macd_direction'] == "DOWN":
            i['applies'] = data[-1]['applies']
            i['volume'] = data[-1]['volume']
            i['10th_largest'] = data[-1]['10th_largest']
            target['code'] = i['code']
            target['name'] = i['name']
            target['industry'] = i['industry'] = get_industry_by_code(i['code'])
            result.append({'code': i['code'], 'name': i['name'], 'industry': i['industry']})
            logging.warning(f"{target}")
    return result


def stock_filter_by_BooleanLine(pool=None, period=101, limit=150):
    logging.warning(f"stock filter by BooleanLine !")
    if not pool:
        pool = institutions_holding_rps_stock()
    result = []
    count = 1
    for i in pool:
        i['code'] = i['code'].split('.')[0]
        data = get_stock_kline_with_indicators(i['code'], period=period, limit=limit)
        data = BooleanLine(ATR(data))
        if 0.2 >= data[-1]['BBW'] > data[-2]['BBW'] >= data[-3]['BBW']:
            i['week_applies'] = round((data[-1]['close'] - data[-5]['last_close']) / data[-5]['last_close'] * 100, 2)
            if i['week_applies'] > 0:
                i['industry'] = get_industry_by_code(i['code'])
                i['BBW'] = [data[-3]['BBW'], data[-2]['BBW'], data[-1]['BBW']]
                i['url'] = f"https://xueqiu.com/S/{'SH' if i['code'].startswith('6') else 'SZ'}{i['code']}"
                result.append(i)
                logging.warning(f"价格从盘整带向上启动: {count}\t{i}")
                count += 1
    return result


def stock_filter_by_BooleanV1(pool=None, period=101):
    if not pool:
        pool = institutions_holding_rps_stock()
    count = 1
    result = []
    for i in pool:
        i['code'] = i['code'].split('.')[0]
        kline = get_stock_kline_with_indicators(i['code'], period=period)
        kline = BooleanLine(kline)
        if kline[-1]['MID'] > kline[-2]['MID'] or kline[-1]['BBW'] < 0.2:
            if (kline[-1]['close'] > kline[-1]['MID'] and kline[-2]['close'] < kline[-2]['MID']) \
                    or (kline[-1]['MID'] < kline[-1]['close'] <= kline[-1]['MID'] * 1.02):
                i['industry'] = get_industry_by_code(i['code'])
                i['BBW'] = [kline[-3]['BBW'], kline[-2]['BBW'], kline[-1]['BBW']]
                i['url'] = f"https://xueqiu.com/S/{'SH' if i['code'].startswith('6') else 'SZ'}{i['code']}"
                logging.warning(f"价格上穿/回落至布林线中轨带: {count}\t{i}")
                count += 1
                result.append(i)
    return result


def stock_filter_by_BooleanLine_V2(pool: list):
    result = []
    for i in pool:
        data = i['kline']
        data = ATR(data)
        data = BooleanLine(data)
        target = {}
        if 0.2 >= data[-1]['BBW'] > data[-2]['BBW'] >= data[-3]['BBW']:
            i['BBW'] = data[-1]['BBW']
            i['week_applies'] = round((data[-1]['close'] - data[-5]['last_close']) / data[-5]['last_close'] * 100, 2)
            if i['week_applies'] > 0:
                target['code'] = i['code']
                target['name'] = i['name']
                target['industry'] = i['industry'] = get_industry_by_code(i['code'])
                result.append({'code': i['code'], 'name': i['name'], 'industry': i['industry']})
                logging.warning(f"{target}")
    return result


def stock_filter_by_WAD(period=101, limit=180):
    logging.warning(f"stock filter by WAD !")
    pool = institutions_holding_rps_stock()
    result = []
    for i in pool:
        data = get_stock_kline_with_indicators(i['code'], period=period, limit=limit)
        data = ATR(data)
        data = WAD(data)
        biggest_decline = biggest_decline_calc(data)
        if data[-1]['WAD'] > data[-1]['MAWAD'] and data[-2]['WAD'] < data[-2]['MAWAD']:
            i['WAD'] = data[-1]['WAD']
            i['MAWAD'] = data[-1]['MAWAD']
            i['industry'] = get_industry_by_code(i['code'])
            result.append(i)
            logging.warning(f"{i}\t半年内最大跌幅: {biggest_decline}")
    return result


def stock_filter_by_WAD_V2(pool: list):
    result = []
    for i in pool:
        data = i['kline']
        data = ATR(data)
        data = WAD(data)
        target = {}
        if data[-1]['WAD'] > data[-1]['MAWAD'] and data[-2]['WAD'] < data[-2]['MAWAD']:
            i['WAD'] = data[-1]['WAD']
            i['MAWAD'] = data[-1]['MAWAD']
            target['code'] = i['code']
            target['name'] = i['name']
            target['industry'] = i['industry'] = get_industry_by_code(i['code'])
            result.append({'code': i['code'], 'name': i['name'], 'industry': i['industry']})
            logging.warning(f"{target}")
    return result


def stock_filter_by_Compact_Structure():
    # 股价结构紧凑
    pool = institutions_holding_rps_stock()
    result = []
    for i in pool:
        data = get_stock_kline_with_indicators(i['code'])
        data = Compact_Structure(data)
        i['industry'] = get_industry_by_code(i['code'])
        i['variance'] = data[-1]['variance']
        result.append(i)
        logging.warning(i)
    return sorted(result, key=lambda x: x['variance'], reverse=True)


def stock_filter_by_kama():
    # 根据考夫曼自适应均线对股票池进行筛选
    pool = institutions_holding_rps_stock()
    result = []
    for i in pool:
        data = get_stock_kline_with_indicators(i['code'])
        data = KAMA(data)
        if data[-1]['close'] > data[-1]['KAMA'] and data[-2]['close'] < data[-2]['KAMA']:
            i['close'] = data[-1]['close']
            i['applies'] = data[-1]['applies']
            result.append(i)
            logging.warning(i)
    return result


def stock_filter_by_kama_V2(pool: list):
    # 根据考夫曼自适应均线对股票池进行筛选
    result = []
    for i in pool:
        data = i['kline']
        data = KAMA(data)
        target = {}
        if data[-1]['close'] > data[-1]['KAMA'] and data[-2]['close'] < data[-2]['KAMA']:
            i['close'] = data[-1]['close']
            i['applies'] = data[-1]['applies']
            target['code'] = i['code']
            target['name'] = i['name']
            target['industry'] = i['industry'] = get_industry_by_code(i['code'])
            result.append({'code': i['code'], 'name': i['name'], 'industry': i['industry']})
            logging.warning(target)
    return result


def Channel_Trade_System(kline: list):
    N, M = 13, 26
    kline = EMA_V2(EMA_V2(kline, N), M)
    baseline = find_channel_coefficients(kline)
    logging.warning(f"channel_coefficients:{baseline}")
    for i in range(len(kline)):
        kline[i]['up_channel'] = kline[i][f'ema{M}'] + baseline * kline[i][f'ema{M}']
        kline[i]['down_channel'] = kline[i][f'ema{M}'] - baseline * kline[i][f'ema{M}']
    return kline


def calc_coefficients(kline, M=26, channel_coefficients=0.05):
    count = 0
    total_count = len(kline)
    for i in range(len(kline)):
        kline[i]['up_channel'] = kline[i][f'ema{M}'] + channel_coefficients * kline[i][f'ema{M}']
        kline[i]['down_channel'] = kline[i][f'ema{M}'] - channel_coefficients * kline[i][f'ema{M}']
    for i in range(len(kline)):
        if kline[i]['close'] > kline[i]['up_channel'] or kline[i]['close'] < kline[i]['down_channel']:
            count += 1
    return round((total_count - count) / total_count, 2)


def find_channel_coefficients(kline: list):
    channel_coefficients = 0.05
    standard = 0.95
    while True:
        ratio = calc_coefficients(kline, channel_coefficients=channel_coefficients)
        if ratio < standard:
            channel_coefficients += 0.01
        else:
            break
    return round(channel_coefficients, 2)


def Power_System(kline: list):
    N, M, L = 13, 26, 150
    kline = EMA_V2(EMA_V2(EMA_V2(kline, L), N), M)
    kline = MACD(kline)
    if kline[-1]['close'] > kline[-1][f'ema{L}']:
        if kline[-1][f'ema{N}'] > kline[-2][f'ema{N}'] \
                and kline[-1][f'ema{M}'] > kline[-2][f'ema{M}'] \
                and kline[-1]['macd_direction'] == 'UP':
            return True


def ATR_Channel_System(kline: list):
    M = 26
    ATR_parameter = 20
    kline = EMA_V2(ATR(kline), M)
    for i in range(len(kline)):
        kline[i]['+1ATR'] = round(kline[i][f'ema{M}'] + kline[i][f'ATR_{ATR_parameter}'], 2)
        kline[i]['+2ATR'] = round(kline[i][f'ema{M}'] + 2 * kline[i][f'ATR_{ATR_parameter}'], 2)
        kline[i]['+3ATR'] = round(kline[i][f'ema{M}'] + 3 * kline[i][f'ATR_{ATR_parameter}'], 2)
        kline[i]['-1ATR'] = round(kline[i][f'ema{M}'] - kline[i][f'ATR_{ATR_parameter}'], 2)
        kline[i]['-2ATR'] = round(kline[i][f'ema{M}'] - 2 * kline[i][f'ATR_{ATR_parameter}'], 2)
        kline[i]['-3ATR'] = round(kline[i][f'ema{M}'] - 3 * kline[i][f'ATR_{ATR_parameter}'], 2)
    return kline


class Channel:

    def __init__(self, code, name, period=101, limit=120):
        self.code = code
        self.name = name
        self.kline = get_stock_kline_with_indicators(code, limit=limit, period=period)
        self.channel_trade_system()

    def channel_trade_system(self):
        N, M = 13, 26
        self.kline = KAMA(EMA_V2(EMA_V2(EMA_V2(self.kline, N), M), 50))
        up_channel_coefficients, down_channel_coefficients = self.find_channel_coefficients()
        logging.warning(f"code: {self.code}\tname: {self.name}\t"
                        f"up_channel_coefficients:{up_channel_coefficients}\t"
                        f"down_channel_coefficients:{down_channel_coefficients}")
        for i in range(len(self.kline)):
            self.kline[i]['up_channel'] = self.kline[i][f'ema{M}'] + \
                                          up_channel_coefficients * self.kline[i][f'ema{M}']
            self.kline[i]['down_channel'] = self.kline[i][f'ema{M}'] - \
                                            down_channel_coefficients * self.kline[i][f'ema{M}']

    def calc_coefficients(
            self, M=26, up_channel_coefficients=0.01, down_channel_coefficients=0.01):
        up_count, down_count = 0, 0
        total_count = len(self.kline)
        for i in range(len(self.kline)):
            self.kline[i]['up_channel'] = self.kline[i][f'ema{M}'] + \
                                          up_channel_coefficients * self.kline[i][f'ema{M}']
            self.kline[i]['down_channel'] = self.kline[i][f'ema{M}'] - \
                                            down_channel_coefficients * self.kline[i][f'ema{M}']
        for i in range(len(self.kline)):
            if self.kline[i]['close'] > self.kline[i]['up_channel']:
                up_count += 1
            if self.kline[i]['close'] < self.kline[i]['down_channel']:
                down_count += 1
        return round((total_count - up_count) / total_count,
                     2), round((total_count - down_count) / total_count, 2)

    def find_channel_coefficients(self):
        up_channel_coefficients, down_channel_coefficients = 0.01, 0.01
        standard = 0.95
        ucc, dcc = None, None
        while True:
            up_ratio, down_ratio = self.calc_coefficients(up_channel_coefficients=up_channel_coefficients,
                                                          down_channel_coefficients=down_channel_coefficients)
            if up_ratio < standard:
                up_channel_coefficients += 0.01
            else:
                ucc = up_channel_coefficients
            if down_ratio < standard:
                down_channel_coefficients += 0.01
            else:
                dcc = down_channel_coefficients
            if ucc and dcc:
                break
        return round(up_channel_coefficients, 2), round(
            down_channel_coefficients, 2)


def stock_filter_by_down_channel():
    pool = institutions_holding_rps_stock()
    result = []
    for i in pool:
        c = Channel(i['code'], i['name'])
        if c.kline[-1]['ema50'] >= c.kline[-2]['ema50']:
            if c.kline[-1]['close'] <= c.kline[-1]['down_channel']:
                i['industry'] = get_industry_by_code(i['code'])
                logging.warning(i)
                result.append(i)
    return result


def FIP(kline: list):
    # 温水煮青蛙动量算法
    if len(kline) < 250:
        logging.warning(f"行情数据不足一年, 可能导致算法计算准确度不足")
    kline = kline[-250:]
    profit = int((kline[-1]['close'] / kline[0]['last_close'] - 1) * 100)
    positive = round(len([1 for i in kline if i['applies'] > 0]) / len(kline), 2)
    negative = round(len([1 for i in kline if i['applies'] < 0]) / len(kline), 2)
    logging.warning(f"profit:{profit}\tpositive:{positive}\tnegative:{negative}")
    return round(profit * (negative - positive), 2)


def stock_filter_by_Shrank_back_to_trample(pool=None, volume_part=1):
    # 价格位于5日线之下,50日线方向向上,抓取缩量回踩的标的
    # volume_part 盘中执行时, 根据已开盘时长推算全天成交量
    N, M = 5, 50
    last_one = -1
    if not pool:
        pool = institutions_holding_rps_stock()
    result = []
    counter = 1
    for i in pool:
        kline = get_stock_kline_with_indicators(i['code'])
        if len(kline) > M:
            kline = MACD(MA(MA(kline, N), M))
            if kline[last_one][f'MA{M}'] <= kline[last_one]['close'] <= kline[last_one][f'MA{N}']:
                if kline[last_one]['volume'] * volume_part < kline[last_one]['avg_volume']:
                    code = i['code'].split('.')[0]
                    i['industry'] = get_industry_by_code(i['code'])
                    i['applies'] = kline[last_one]['applies']
                    i['volume_ratio'] = kline[last_one]['volume_ratio']
                    i['url'] = f"https://xueqiu.com/S/{'SH' if i['code'].startswith('6') else 'SZ'}{code}"
                    result.append(i)
                    logging.warning(f" {counter}\t{i}")
                    counter += 1
    return result


def stock_filter_by_Shrank_back_to_trample_V2(pool: list):
    # 价格位于10日线之下,50日线方向向上,抓取缩量回踩的标的
    N, M = 5, 50
    result = []
    for i in pool:
        kline = i['kline']
        kline = MA(MA(kline, N), M)
        target = {}
        if kline[-1][f'MA{M}'] >= kline[-2][f'MA{M}'] and kline[-1]['close'] <= kline[-1][f'MA{N}']:
            if kline[-1]['volume'] < kline[-1]['10th_minimum']:
                i['industry'] = get_industry_by_code(i['code'])
                i['applies'] = kline[-1]['applies']
                i['volume_ratio'] = kline[-1]['volume_ratio']
                target['code'] = i['code']
                target['name'] = i['name']
                target['industry'] = get_industry_by_code(i['code'])
                result.append({'code': i['code'], 'name': i['name'], 'industry': i['industry']})
                logging.warning(target)
    return result


def stock_filter_by_ema_week():
    pool = get_all_RPS_stock_pool()
    for i in pool:
        kline = get_stock_kline_with_indicators(i['code'])
        kline = EMA_V2(EMA_V2(kline, 10), 30)
        if kline[-1]['ema30'] >= kline[-2]['ema30']:
            i['close'] = kline[-1]['close']
            i['ema10'] = kline[-1]['ema10']
            i['ema30'] = kline[-1]['ema30']
            i['applies'] = kline[-1]['applies']
            if kline[-1]['ema30'] < kline[-1]['close'] < kline[-1]['ema10']:
                logging.warning(f"price between ema10 and ema30: {i}")
            if kline[-1]['close'] > kline[-1]['ema30'] and kline[-2]['close'] < kline[-2]['ema30']:
                logging.warning(f"price breakthrough from ema30: {i}")


def stock_filter_aggregation(pool=Beautiful):
    if not pool:
        pool = institutions_holding_rps_stock()
    for i in pool:
        i['kline'] = get_stock_kline_with_indicators(i['code'], period=101, limit=180)
    logging.warning(f"MACD STOCK FILTER")
    macd_pool = stock_filter_by_MACD_and_BBI_V2(pool)
    logging.warning(f"WAD STOCK FILTER")
    wad_pool = stock_filter_by_WAD_V2(pool)
    logging.warning(f"BooleanLine STOCK FILTER")
    boolean_pool = stock_filter_by_BooleanLine_V2(pool)
    logging.warning(f"KAMA STOCK FILTER")
    kama_pool = stock_filter_by_kama_V2(pool)
    total = macd_pool + wad_pool + boolean_pool + kama_pool
    for i in total:
        if total.count(i) > 1:
            print(i, "买入信号出现超过一次")


def outputTrendStockSortByVolume():
    result = []
    day = -1
    counter = 1
    for i in TrendStock:
        code = i['code'].split('.')[0]
        kline = get_stock_kline_with_indicators(code)
        kline = MA(kline, 10)
        if kline[day]['volume'] < kline[day]['avg_volume']:
            i['close'] = kline[day]['close']
            i['applies'] = kline[day]['applies']
            i['volume_ratio'] = kline[day]['volume_ratio']
            result.append(i)
    result = sorted(result, key=lambda x: x['volume_ratio'], reverse=True)
    for i in result:
        logging.warning(f"{counter}\t{i}")
        counter += 1
    return result


def Short_term_strength(code, limit=5):
    # 短期强弱判定
    data = get_stock_kline_with_indicators(code, limit=limit)
    max_volume = {'v': 0, 'count': 0, 'high': 0, 'low': 0}
    for i in range(len(data)):
        if data[i]['VOL'] > max_volume['v']:
            max_volume['v'] = data[i]['VOL']
            max_volume['count'] = i
            max_volume['high'] = data[i]['high']
            max_volume['low'] = data[i]['low']
    data = data[max_volume['count'] + 1:]
    if len(data) > 0:
        if max_volume['high'] < min([i['close'] for i in data]):
            return True


def Mansfield(kline, index_kline):
    assert len(kline) == len(index_kline)
    for i in range(len(kline)):
        kline[i]['relative_intensity'] = round(kline[i]['applies'] / index_kline[i]['applies'], 3)
    return kline


def TrendBuyPoint():
    for i in TrendStock:
        data = get_stock_kline_with_indicators(i['code'].split('.')[0], period=30)
        data = MACD(data)
        i['close'] = data[-1]['close']
        # print(i)
        if (data[-1]['DIF'] < 0) and (data[-1]['DIF'] > data[-1]['DEA']) and (data[-2]['DIF'] > data[-2]['DEA']):
            logging.warning(i)


def TrendStopLoss():
    for i in TrendStock:
        code = i['code'].split('.')[0]
        data = get_stock_kline_with_indicators(code)
        data = ATR(data)
        i['close'] = data[-1]['close']
        i['stopLoss'] = round(data[-1]['highest'] - 2 * data[-1]['ATR_20'], 2)
        print(Fore.LIGHTRED_EX + f"{i}" + Style.RESET_ALL if i['close'] > i[
            'stopLoss'] else Fore.LIGHTGREEN_EX + f"{i}" + Style.RESET_ALL)


def StanWeinstein():
    pool = institutions_holding()
    for i in pool:
        data = get_stock_kline_with_indicators(i['code'])
        data = EMA_V2(EMA_V2(data, 10), 30)
        if data[-1]['close'] > data[-1]['ema30'] >= data[-2]['ema30']:
            i['industry'] = get_industry_by_code(i['code'])
            i['close'] = data[-1]['close']
            i['ema10'] = data[-1]['ema10']
            i['ema30'] = data[-1]['ema30']
            i['premium'] = round((i['close']-i['ema30'])/i['ema30']*100, 2)
            logging.warning(i)


def NewStockDetail():
    pool = select_composition_stock("BK0501")
    for i in pool:
        code = f"{i['code']}.SH" if str(i['code']).startswith('6') else f"{i['code']}.SZ"
        i['industry'] = get_industry_by_code(i['code'])
        i['list_date'] = int(NEW_STOCK_LIST[code]['list_date'])
        i['url'] = f"https://xueqiu.com/S/{'SH' if i['code'].startswith('6') else 'SZ'}{i['code']}"
        if i['list_date'] >= int(str(date.today()-timedelta(90)).replace('-', '')) and not i['code'].startswith('68'):
            kline = get_stock_kline_with_indicators(i['code'], limit=250)
            avg_close = sum([i['close'] for i in kline])/len(kline)
            if kline[0]['close'] < avg_close:
                logging.warning(f"{i}\t{len(kline)}")
            else:
                print(f"{i}\t{len(kline)}")


if __name__ == "__main__":
    stock_filter_by_Shrank_back_to_trample(pool=smart_car)
    # res = {'600104.SH': {'code': '600104.SH', 'name': '上汽集团', 'industry': '汽车整车'}, '000550.SZ': {'code': '000550.SZ', 'name': '江铃汽车', 'industry': '汽车整车'}, '002920.SZ': {'code': '002920.SZ', 'name': '德赛西威', 'industry': '汽车配件'}, '003021.SZ': {'code': '003021.SZ', 'name': '兆威机电', 'industry': '元器件'}, '601238.SH': {'code': '601238.SH', 'name': '广汽集团', 'industry': '汽车整车'}, '601965.SH': {'code': '601965.SH', 'name': '中国汽研', 'industry': '汽车服务'}, '002906.SZ': {'code': '002906.SZ', 'name': '华阳集团', 'industry': '汽车配件'}, '600166.SH': {'code': '600166.SH', 'name': '福田汽车', 'industry': '汽车整车'}, '300342.SZ': {'code': '300342.SZ', 'name': '天银机电', 'industry': '家用电器'}, '002965.SZ': {'code': '002965.SZ', 'name': '祥鑫科技', 'industry': '汽车配件'}, '000625.SZ': {'code': '000625.SZ', 'name': '长安汽车', 'industry': '汽车整车'}, '688113.SH': {'code': '688113.SH', 'name': '联测科技', 'industry': '专用机械'}, '002405.SZ': {'code': '002405.SZ', 'name': '四维图新', 'industry': '软件服务'}, '000868.SZ': {'code': '000868.SZ', 'name': '安凯客车', 'industry': '汽车整车'}, '301031.SZ': {'code': '301031.SZ', 'name': '中熔电气', 'industry': '电气设备'}, '600699.SH': {'code': '600699.SH', 'name': '均胜电子', 'industry': '汽车配件'}, '300339.SZ': {'code': '300339.SZ', 'name': '润和软件', 'industry': '软件服务'}, '002239.SZ': {'code': '002239.SZ', 'name': '奥特佳', 'industry': '汽车配件'}, '600418.SH': {'code': '600418.SH', 'name': '江淮汽车', 'industry': '汽车整车'}, '002786.SZ': {'code': '002786.SZ', 'name': '银宝山新', 'industry': '专用机械'}, '600733.SH': {'code': '600733.SH', 'name': '北汽蓝谷', 'industry': '汽车整车'}, '002126.SZ': {'code': '002126.SZ', 'name': '银轮股份', 'industry': '汽车配件'}, '300648.SZ': {'code': '300648.SZ', 'name': '星云股份', 'industry': '电器仪表'}, '002036.SZ': {'code': '002036.SZ', 'name': '联创电子', 'industry': '元器件'}, '300432.SZ': {'code': '300432.SZ', 'name': '富临精工', 'industry': '汽车配件'}, '002897.SZ': {'code': '002897.SZ', 'name': '意华股份', 'industry': '元器件'}, '002885.SZ': {'code': '002885.SZ', 'name': '京泉华', 'industry': '元器件'}, '002232.SZ': {'code': '002232.SZ', 'name': '启明信息', 'industry': '软件服务'}, '300473.SZ': {'code': '300473.SZ', 'name': '德尔股份', 'industry': '汽车配件'}, '002050.SZ': {'code': '002050.SZ', 'name': '三花智控', 'industry': '家用电器'}, '601127.SH': {'code': '601127.SH', 'name': '小康股份', 'industry': '汽车整车'}, '688550.SH': {'code': '688550.SH', 'name': '瑞联新材', 'industry': '化工原料'}, '605589.SH': {'code': '605589.SH', 'name': '圣泉集团', 'industry': '化工原料'}, '300398.SZ': {'code': '300398.SZ', 'name': '飞凯材料', 'industry': '染料涂料'}, '002409.SZ': {'code': '002409.SZ', 'name': '雅克科技', 'industry': '化工原料'}, '603306.SH': {'code': '603306.SH', 'name': '华懋科技', 'industry': '汽车配件'}, '300623.SZ': {'code': '300623.SZ', 'name': '捷捷微电', 'industry': '半导体'}, '600895.SH': {'code': '600895.SH', 'name': '张江高科', 'industry': '园区开发'}, '300236.SZ': {'code': '300236.SZ', 'name': '上海新阳', 'industry': '半导体'}, '002324.SZ': {'code': '002324.SZ', 'name': '普利特', 'industry': '塑料'}, '300331.SZ': {'code': '300331.SZ', 'name': '苏大维格', 'industry': '元器件'}, '300655.SZ': {'code': '300655.SZ', 'name': '晶瑞电材', 'industry': '化工原料'}, '300721.SZ': {'code': '300721.SZ', 'name': '怡达股份', 'industry': '化工原料'}, '300758.SZ': {'code': '300758.SZ', 'name': '七彩化学', 'industry': '染料涂料'}, '300456.SZ': {'code': '300456.SZ', 'name': '赛微电子', 'industry': '元器件'}, '688019.SH': {'code': '688019.SH', 'name': '安集科技', 'industry': '半导体'}, '300131.SZ': {'code': '300131.SZ', 'name': '英唐智控', 'industry': '商贸代理'}, '300200.SZ': {'code': '300200.SZ', 'name': '高盟新材', 'industry': '化工原料'}, '603650.SH': {'code': '603650.SH', 'name': '彤程新材', 'industry': '化工原料'}, '300225.SZ': {'code': '300225.SZ', 'name': '金力泰', 'industry': '染料涂料'}, '603931.SH': {'code': '603931.SH', 'name': '格林达', 'industry': '化工原料'}, '300429.SZ': {'code': '300429.SZ', 'name': '强力新材', 'industry': '化工原料'}, '688181.SH': {'code': '688181.SH', 'name': '八亿时空', 'industry': '半导体'}, '688199.SH': {'code': '688199.SH', 'name': '久日新材', 'industry': '化工原料'}, '688157.SH': {'code': '688157.SH', 'name': '松井股份', 'industry': '染料涂料'}, '603005.SH': {'code': '603005.SH', 'name': '晶方科技', 'industry': '半导体'}, '688037.SH': {'code': '688037.SH', 'name': '芯源微', 'industry': '半导体'}, '300346.SZ': {'code': '300346.SZ', 'name': '南大光电', 'industry': '元器件'}, '300522.SZ': {'code': '300522.SZ', 'name': '世名科技', 'industry': '染料涂料'}, '688630.SH': {'code': '688630.SH', 'name': '芯碁微装', 'industry': '专用机械'}, '002643.SZ': {'code': '002643.SZ', 'name': '万润股份', 'industry': '化工原料'}, '000969.SZ': {'code': '000969.SZ', 'name': '安泰科技', 'industry': '小金属'}, '688268.SH': {'code': '688268.SH', 'name': '华特气体', 'industry': '化工原料'}, '300537.SZ': {'code': '300537.SZ', 'name': '广信材料', 'industry': '染料涂料'}, '300637.SZ': {'code': '300637.SZ', 'name': '扬帆新材', 'industry': '化工原料'}, '002584.SZ': {'code': '002584.SZ', 'name': '西陇科学', 'industry': '化工原料'}, '603078.SH': {'code': '603078.SH', 'name': '江化微', 'industry': '化工原料'}, '300460.SZ': {'code': '300460.SZ', 'name': '惠伦晶体', 'industry': '元器件'}, '300576.SZ': {'code': '300576.SZ', 'name': '容大感光', 'industry': '染料涂料'}, '300538.SZ': {'code': '300538.SZ', 'name': '同益股份', 'industry': '批发业'}, '300521.SZ': {'code': '300521.SZ', 'name': '爱司凯', 'industry': '专用机械'}, '300031.SZ': {'code': '300031.SZ', 'name': '宝通科技', 'industry': '互联网'}, '300726.SZ': {'code': '300726.SZ', 'name': '宏达电子', 'industry': '元器件'}, '600510.SH': {'code': '600510.SH', 'name': '黑牡丹', 'industry': '全国地产'}, '000733.SZ': {'code': '000733.SZ', 'name': '振华科技', 'industry': '元器件'}, '603733.SH': {'code': '603733.SH', 'name': '仙鹤股份', 'industry': '造纸'}, '600563.SH': {'code': '600563.SH', 'name': '法拉电子', 'industry': '元器件'}, '002484.SZ': {'code': '002484.SZ', 'name': '江海股份', 'industry': '元器件'}, '300064.SZ': {'code': '300064.SZ', 'name': '*ST金刚', 'industry': '矿物制品'}, '000636.SZ': {'code': '000636.SZ', 'name': '风华高科', 'industry': '元器件'}, '603989.SH': {'code': '603989.SH', 'name': '艾华集团', 'industry': '元器件'}, '002389.SZ': {'code': '002389.SZ', 'name': '航天彩虹', 'industry': '航空'}, '000021.SZ': {'code': '000021.SZ', 'name': '深科技', 'industry': 'IT设备'}, '002091.SZ': {'code': '002091.SZ', 'name': '江苏国泰', 'industry': '商贸代理'}, '000009.SZ': {'code': '000009.SZ', 'name': '中国宝安', 'industry': '电气设备'}, '601608.SH': {'code': '601608.SH', 'name': '中信重工', 'industry': '专用机械'}, '600884.SH': {'code': '600884.SH', 'name': '杉杉股份', 'industry': '电气设备'}, '300174.SZ': {'code': '300174.SZ', 'name': '元力股份', 'industry': '化工原料'}, '002418.SZ': {'code': '002418.SZ', 'name': '康盛股份', 'industry': '家用电器'}, '605376.SH': {'code': '605376.SH', 'name': '博迁新材', 'industry': '小金属'}, '600110.SH': {'code': '600110.SH', 'name': '诺德股份', 'industry': '电气设备'}, '300037.SZ': {'code': '300037.SZ', 'name': '新宙邦', 'industry': '化工原料'}, '002028.SZ': {'code': '002028.SZ', 'name': '思源电气', 'industry': '电气设备'}, '600522.SH': {'code': '600522.SH', 'name': '中天科技', 'industry': '通信设备'}, '002356.SZ': {'code': '002356.SZ', 'name': '*ST赫美', 'industry': '其他商业'}, '002012.SZ': {'code': '002012.SZ', 'name': '凯恩股份', 'industry': '造纸'}, '000723.SZ': {'code': '000723.SZ', 'name': '美锦能源', 'industry': '焦炭加工'}, '002808.SZ': {'code': '002808.SZ', 'name': '恒久科技', 'industry': '元器件'}, '002598.SZ': {'code': '002598.SZ', 'name': '山东章鼓', 'industry': '机械基件'}, '002350.SZ': {'code': '002350.SZ', 'name': '北京科锐', 'industry': '电气设备'}, '300960.SZ': {'code': '300960.SZ', 'name': '通业科技', 'industry': '运输设备'}, '002347.SZ': {'code': '002347.SZ', 'name': '泰尔股份', 'industry': '机械基件'}, '600773.SH': {'code': '600773.SH', 'name': '西藏城投', 'industry': '区域地产'}, '002480.SZ': {'code': '002480.SZ', 'name': '新筑股份', 'industry': '机械基件'}, '002951.SZ': {'code': '002951.SZ', 'name': '金时科技', 'industry': '广告包装'}, '002444.SZ': {'code': '002444.SZ', 'name': '巨星科技', 'industry': '轻工机械'}, '003005.SZ': {'code': '003005.SZ', 'name': '竞业达', 'industry': '软件服务'}, '688167.SH': {'code': '688167.SH', 'name': '炬光科技', 'industry': '半导体'}, '603035.SH': {'code': '603035.SH', 'name': '常熟汽饰', 'industry': '汽车配件'}, '002273.SZ': {'code': '002273.SZ', 'name': '水晶光电', 'industry': '元器件'}, '300620.SZ': {'code': '300620.SZ', 'name': '光库科技', 'industry': '元器件'}, '603297.SH': {'code': '603297.SH', 'name': '永新光学', 'industry': '电器仪表'}, '300698.SZ': {'code': '300698.SZ', 'name': '万马科技', 'industry': '通信设备'}, '002222.SZ': {'code': '002222.SZ', 'name': '福晶科技', 'industry': '元器件'}, '603319.SH': {'code': '603319.SH', 'name': '湘油泵', 'industry': '汽车配件'}, '300177.SZ': {'code': '300177.SZ', 'name': '中海达', 'industry': '通信设备'}, '300241.SZ': {'code': '300241.SZ', 'name': '瑞丰光电', 'industry': '半导体'}, '300552.SZ': {'code': '300552.SZ', 'name': '万集科技', 'industry': '软件服务'}, '688195.SH': {'code': '688195.SH', 'name': '腾景科技', 'industry': '元器件'}, '002813.SZ': {'code': '002813.SZ', 'name': '路畅科技', 'industry': '汽车配件'}, '601615.SH': {'code': '601615.SH', 'name': '明阳智能', 'industry': '电气设备'}, '300757.SZ': {'code': '300757.SZ', 'name': '罗博特科', 'industry': '专用机械'}, '300751.SZ': {'code': '300751.SZ', 'name': '迈为股份', 'industry': '专用机械'}, '002129.SZ': {'code': '002129.SZ', 'name': '中环股份', 'industry': '电气设备'}, '600151.SH': {'code': '600151.SH', 'name': '航天机电', 'industry': '汽车配件'}, '002506.SZ': {'code': '002506.SZ', 'name': '协鑫集成', 'industry': '电气设备'}, '601012.SH': {'code': '601012.SH', 'name': '隆基股份', 'industry': '电气设备'}, '002309.SZ': {'code': '002309.SZ', 'name': '中利集团', 'industry': '电气设备'}, '600438.SH': {'code': '600438.SH', 'name': '通威股份', 'industry': '电气设备'}, '002459.SZ': {'code': '002459.SZ', 'name': '晶澳科技', 'industry': '电气设备'}, '002079.SZ': {'code': '002079.SZ', 'name': '苏州固锝', 'industry': '半导体'}, '600546.SH': {'code': '600546.SH', 'name': '山煤国际', 'industry': '煤炭开采'}, '603077.SH': {'code': '603077.SH', 'name': '和邦生物', 'industry': '化工原料'}, '002860.SZ': {'code': '002860.SZ', 'name': '星帅尔', 'industry': '家用电器'}, '000821.SZ': {'code': '000821.SZ', 'name': '京山轻机', 'industry': '轻工机械'}, '002610.SZ': {'code': '002610.SZ', 'name': '爱康科技', 'industry': '电气设备'}, '300118.SZ': {'code': '300118.SZ', 'name': '东方日升', 'industry': '电气设备'}, '300842.SZ': {'code': '300842.SZ', 'name': '帝科股份', 'industry': '半导体'}, '300117.SZ': {'code': '300117.SZ', 'name': '嘉寓股份', 'industry': '装修装饰'}, '300093.SZ': {'code': '300093.SZ', 'name': '金刚玻璃', 'industry': '玻璃'}, '300724.SZ': {'code': '300724.SZ', 'name': '捷佳伟创', 'industry': '专用机械'}, '603396.SH': {'code': '603396.SH', 'name': '金辰股份', 'industry': '专用机械'}, '688359.SH': {'code': '688359.SH', 'name': '三孚新科', 'industry': '化工原料'}, '300075.SZ': {'code': '300075.SZ', 'name': '数字政通', 'industry': '软件服务'}, '300825.SZ': {'code': '300825.SZ', 'name': '阿尔特', 'industry': '汽车服务'}, '002463.SZ': {'code': '002463.SZ', 'name': '沪电股份', 'industry': '元器件'}, '002829.SZ': {'code': '002829.SZ', 'name': '星网宇达', 'industry': '航空'}, '300099.SZ': {'code': '300099.SZ', 'name': '精准信息', 'industry': '电器仪表'}, '601633.SH': {'code': '601633.SH', 'name': '长城汽车', 'industry': '汽车整车'}, '002766.SZ': {'code': '002766.SZ', 'name': '*ST索菱', 'industry': '汽车配件'}, '600741.SH': {'code': '600741.SH', 'name': '华域汽车', 'industry': '汽车配件'}, '601766.SH': {'code': '601766.SH', 'name': '中国中车', 'industry': '运输设备'}, '300292.SZ': {'code': '300292.SZ', 'name': '吴通控股', 'industry': '软件服务'}, '002415.SZ': {'code': '002415.SZ', 'name': '海康威视', 'industry': '电器仪表'}, '002230.SZ': {'code': '002230.SZ', 'name': '科大讯飞', 'industry': '软件服务'}, '300496.SZ': {'code': '300496.SZ', 'name': '中科创达', 'industry': '软件服务'}, '002065.SZ': {'code': '002065.SZ', 'name': '东华软件', 'industry': '软件服务'}, '600066.SH': {'code': '600066.SH', 'name': '宇通客车', 'industry': '汽车整车'}, '002414.SZ': {'code': '002414.SZ', 'name': '高德红外', 'industry': '电器仪表'}, '301091.SZ': {'code': '301091.SZ', 'name': '深城交', 'industry': '建筑工程'}, '601799.SH': {'code': '601799.SH', 'name': '星宇股份', 'industry': '汽车配件'}, '600081.SH': {'code': '600081.SH', 'name': '东风科技', 'industry': '汽车配件'}, '600686.SH': {'code': '600686.SH', 'name': '金龙汽车', 'industry': '汽车整车'}, '300853.SZ': {'code': '300853.SZ', 'name': '申昊科技', 'industry': '电器仪表'}, '300458.SZ': {'code': '300458.SZ', 'name': '全志科技', 'industry': '元器件'}, '601689.SH': {'code': '601689.SH', 'name': '拓普集团', 'industry': '汽车配件'}, '600006.SH': {'code': '600006.SH', 'name': '东风汽车', 'industry': '汽车整车'}, '002594.SZ': {'code': '002594.SZ', 'name': '比亚迪', 'industry': '汽车整车'}, '002373.SZ': {'code': '002373.SZ', 'name': '千方科技', 'industry': '软件服务'}, '300114.SZ': {'code': '300114.SZ', 'name': '中航电测', 'industry': '电器仪表'}, '002421.SZ': {'code': '002421.SZ', 'name': '达实智能', 'industry': '软件服务'}, '603528.SH': {'code': '603528.SH', 'name': '多伦科技', 'industry': '软件服务'}, '300516.SZ': {'code': '300516.SZ', 'name': '久之洋', 'industry': '电器仪表'}, '603508.SH': {'code': '603508.SH', 'name': '思维列控', 'industry': '软件服务'}, '002413.SZ': {'code': '002413.SZ', 'name': '雷科防务', 'industry': '通信设备'}, '000572.SZ': {'code': '000572.SZ', 'name': '海马汽车', 'industry': '汽车整车'}, '002456.SZ': {'code': '002456.SZ', 'name': '欧菲光', 'industry': '元器件'}, '603776.SH': {'code': '603776.SH', 'name': '永安行', 'industry': '公共交通'}, '002448.SZ': {'code': '002448.SZ', 'name': '中原内配', 'industry': '汽车配件'}, '002151.SZ': {'code': '002151.SZ', 'name': '北斗星通', 'industry': '通信设备'}, '688521.SH': {'code': '688521.SH', 'name': '芯原股份-U', 'industry': '半导体'}, '002313.SZ': {'code': '002313.SZ', 'name': '日海智能', 'industry': '通信设备'}, '002703.SZ': {'code': '002703.SZ', 'name': '浙江世宝', 'industry': '汽车配件'}, '000957.SZ': {'code': '000957.SZ', 'name': '中通客车', 'industry': '汽车整车'}, '002055.SZ': {'code': '002055.SZ', 'name': '得润电子', 'industry': '元器件'}, '002214.SZ': {'code': '002214.SZ', 'name': '大立科技', 'industry': '电器仪表'}, '600718.SH': {'code': '600718.SH', 'name': '东软集团', 'industry': '软件服务'}, '002331.SZ': {'code': '002331.SZ', 'name': '皖通科技', 'industry': '软件服务'}, '603458.SH': {'code': '603458.SH', 'name': '勘设股份', 'industry': '建筑工程'}, '300598.SZ': {'code': '300598.SZ', 'name': '诚迈科技', 'industry': '软件服务'}, '000338.SZ': {'code': '000338.SZ', 'name': '潍柴动力', 'industry': '汽车配件'}, '300520.SZ': {'code': '300520.SZ', 'name': '科大国创', 'industry': '软件服务'}, '002362.SZ': {'code': '002362.SZ', 'name': '汉王科技', 'industry': '软件服务'}, '688088.SH': {'code': '688088.SH', 'name': '虹软科技', 'industry': '软件服务'}, '603023.SH': {'code': '603023.SH', 'name': '威帝股份', 'industry': '汽车配件'}, '000951.SZ': {'code': '000951.SZ', 'name': '中国重汽', 'industry': '汽车整车'}, '000901.SZ': {'code': '000901.SZ', 'name': '航天科技', 'industry': '汽车配件'}, '601777.SH': {'code': '601777.SH', 'name': '力帆科技', 'industry': '摩托车'}, '300656.SZ': {'code': '300656.SZ', 'name': '民德电子', 'industry': 'IT设备'}, '002630.SZ': {'code': '002630.SZ', 'name': '华西能源', 'industry': '专用机械'}, '301221.SZ': {'code': '301221.SZ', 'name': '光庭信息', 'industry': '软件服务'}, '300045.SZ': {'code': '300045.SZ', 'name': '华力创通', 'industry': 'IT设备'}, '300627.SZ': {'code': '300627.SZ', 'name': '华测导航', 'industry': '通信设备'}, '300411.SZ': {'code': '300411.SZ', 'name': '金盾股份', 'industry': '专用机械'}, '002383.SZ': {'code': '002383.SZ', 'name': '合众思壮', 'industry': '通信设备'}, '002355.SZ': {'code': '002355.SZ', 'name': '兴民智通', 'industry': '汽车配件'}, '002937.SZ': {'code': '002937.SZ', 'name': '兴瑞科技', 'industry': '元器件'}, '002590.SZ': {'code': '002590.SZ', 'name': '万安科技', 'industry': '汽车配件'}, '603197.SH': {'code': '603197.SH', 'name': '保隆科技', 'industry': '汽车配件'}, '002284.SZ': {'code': '002284.SZ', 'name': '亚太股份', 'industry': '汽车配件'}, '300418.SZ': {'code': '300418.SZ', 'name': '昆仑万维', 'industry': '互联网'}, '600262.SH': {'code': '600262.SH', 'name': '北方股份', 'industry': '汽车整车'}, '300098.SZ': {'code': '300098.SZ', 'name': '高新兴', 'industry': '通信设备'}, '300270.SZ': {'code': '300270.SZ', 'name': '中威电子', 'industry': '通信设备'}, '002970.SZ': {'code': '002970.SZ', 'name': '锐明技术', 'industry': '通信设备'}, '002806.SZ': {'code': '002806.SZ', 'name': '华锋股份', 'industry': '铝'}, '000980.SZ': {'code': '000980.SZ', 'name': '*ST众泰', 'industry': '汽车配件'}, '300304.SZ': {'code': '300304.SZ', 'name': '云意电气', 'industry': '汽车配件'}, '300209.SZ': {'code': '300209.SZ', 'name': '天泽信息', 'industry': '互联网'}, '300742.SZ': {'code': '300742.SZ', 'name': '越博动力', 'industry': '汽车配件'}, '605118.SH': {'code': '605118.SH', 'name': '力鼎光电', 'industry': '元器件'}, '000836.SZ': {'code': '000836.SZ', 'name': '富通信息', 'industry': '通信设备'}, '300807.SZ': {'code': '300807.SZ', 'name': '天迈科技', 'industry': '软件服务'}, '300020.SZ': {'code': '300020.SZ', 'name': '银江技术', 'industry': '软件服务'}, '000909.SZ': {'code': '000909.SZ', 'name': '数源科技', 'industry': '综合类'}, '688022.SH': {'code': '688022.SH', 'name': '瀚川智能', 'industry': '专用机械'}, '300459.SZ': {'code': '300459.SZ', 'name': '汤姆猫', 'industry': '互联网'}, '300113.SZ': {'code': '300113.SZ', 'name': '顺网科技', 'industry': '互联网'}, '002555.SZ': {'code': '002555.SZ', 'name': '三七互娱', 'industry': '互联网'}, '300136.SZ': {'code': '300136.SZ', 'name': '信维通信', 'industry': '通信设备'}, '002624.SZ': {'code': '002624.SZ', 'name': '完美世界', 'industry': '影视音像'}, '600850.SH': {'code': '600850.SH', 'name': '电科数字', 'industry': '软件服务'}, '002602.SZ': {'code': '002602.SZ', 'name': '世纪华通', 'industry': '互联网'}, '002168.SZ': {'code': '002168.SZ', 'name': '惠程科技', 'industry': '互联网'}, '002425.SZ': {'code': '002425.SZ', 'name': '凯撒文化', 'industry': '互联网'}, '002174.SZ': {'code': '002174.SZ', 'name': '游族网络', 'industry': '互联网'}, '300556.SZ': {'code': '300556.SZ', 'name': '丝路视觉', 'industry': '软件服务'}, '300356.SZ': {'code': '300356.SZ', 'name': 'ST光一', 'industry': '电气设备'}, '600640.SH': {'code': '600640.SH', 'name': '新国脉', 'industry': '影视音像'}, '002517.SZ': {'code': '002517.SZ', 'name': '恺英网络', 'industry': '互联网'}, '002343.SZ': {'code': '002343.SZ', 'name': '慈文传媒', 'industry': '影视音像'}, '002558.SZ': {'code': '002558.SZ', 'name': '巨人网络', 'industry': '互联网'}, '600804.SH': {'code': '600804.SH', 'name': '鹏博士', 'industry': '电信运营'}, '300288.SZ': {'code': '300288.SZ', 'name': '朗玛信息', 'industry': '软件服务'}, '300472.SZ': {'code': '300472.SZ', 'name': '新元科技', 'industry': '专用机械'}, '002699.SZ': {'code': '002699.SZ', 'name': '美盛文化', 'industry': '影视音像'}, '300264.SZ': {'code': '300264.SZ', 'name': '佳创视讯', 'industry': '通信设备'}, '300052.SZ': {'code': '300052.SZ', 'name': '中青宝', 'industry': '互联网'}, '300148.SZ': {'code': '300148.SZ', 'name': '天舟文化', 'industry': '互联网'}, '300494.SZ': {'code': '300494.SZ', 'name': '盛天网络', 'industry': '互联网'}, '300043.SZ': {'code': '300043.SZ', 'name': '星辉娱乐', 'industry': '文教休闲'}, '601163.SH': {'code': '601163.SH', 'name': '三角轮胎', 'industry': '汽车配件'}, '000589.SZ': {'code': '000589.SZ', 'name': '贵州轮胎', 'industry': '汽车配件'}, '300667.SZ': {'code': '300667.SZ', 'name': '必创科技', 'industry': '电器仪表'}, '002073.SZ': {'code': '002073.SZ', 'name': '软控股份', 'industry': '软件服务'}, '002666.SZ': {'code': '002666.SZ', 'name': '德联集团', 'industry': '化工原料'}, '688208.SH': {'code': '688208.SH', 'name': '道通科技', 'industry': '汽车配件'}, '603266.SH': {'code': '603266.SH', 'name': '天龙股份', 'industry': '塑料'}, '002593.SZ': {'code': '002593.SZ', 'name': '日上集团', 'industry': '汽车配件'}, '603390.SH': {'code': '603390.SH', 'name': '通达电气', 'industry': '汽车配件'}, '300014.SZ': {'code': '300014.SZ', 'name': '亿纬锂能', 'industry': '电气设备'}, '300445.SZ': {'code': '300445.SZ', 'name': '康斯特', 'industry': '电器仪表'}, '603358.SH': {'code': '603358.SH', 'name': '华达科技', 'industry': '汽车配件'}, '300643.SZ': {'code': '300643.SZ', 'name': '万通智控', 'industry': '汽车配件'}, '688288.SH': {'code': '688288.SH', 'name': '鸿泉物联', 'industry': '汽车配件'}, '300007.SZ': {'code': '300007.SZ', 'name': '汉威科技', 'industry': '电器仪表'}, '300507.SZ': {'code': '300507.SZ', 'name': '苏奥传感', 'industry': '汽车配件'}, '300462.SZ': {'code': '300462.SZ', 'name': '华铭智能', 'industry': '专用机械'}, '002917.SZ': {'code': '002917.SZ', 'name': '金奥博', 'industry': '化工原料'}, '603895.SH': {'code': '603895.SH', 'name': '天永智能', 'industry': '专用机械'}, '300124.SZ': {'code': '300124.SZ', 'name': '汇川技术', 'industry': '电器仪表'}, '000333.SZ': {'code': '000333.SZ', 'name': '美的集团', 'industry': '家用电器'}, '000961.SZ': {'code': '000961.SZ', 'name': '中南建设', 'industry': '建筑工程'}, '300024.SZ': {'code': '300024.SZ', 'name': '机器人', 'industry': '专用机械'}, '002292.SZ': {'code': '002292.SZ', 'name': '奥飞娱乐', 'industry': '影视音像'}, '002472.SZ': {'code': '002472.SZ', 'name': '双环传动', 'industry': '汽车配件'}, '300475.SZ': {'code': '300475.SZ', 'name': '香农芯创', 'industry': '家用电器'}, '601138.SH': {'code': '601138.SH', 'name': '工业富联', 'industry': '通信设备'}, '300073.SZ': {'code': '300073.SZ', 'name': '当升科技', 'industry': '电气设备'}, '300391.SZ': {'code': '300391.SZ', 'name': '康跃科技', 'industry': '机械基件'}, '002358.SZ': {'code': '002358.SZ', 'name': 'ST森源', 'industry': '电气设备'}, '002228.SZ': {'code': '002228.SZ', 'name': '合兴包装', 'industry': '广告包装'}, '002698.SZ': {'code': '002698.SZ', 'name': '博实股份', 'industry': '化工机械'}, '000938.SZ': {'code': '000938.SZ', 'name': '紫光股份', 'industry': '软件服务'}, '000584.SZ': {'code': '000584.SZ', 'name': '哈工智能', 'industry': '专用机械'}, '600835.SH': {'code': '600835.SH', 'name': '上海机电', 'industry': '运输设备'}, '300193.SZ': {'code': '300193.SZ', 'name': '佳士科技', 'industry': '专用机械'}, '603025.SH': {'code': '603025.SH', 'name': '大豪科技', 'industry': '纺织机械'}, '600282.SH': {'code': '600282.SH', 'name': '南钢股份', 'industry': '普钢'}, '603901.SH': {'code': '603901.SH', 'name': '永创智能', 'industry': '专用机械'}, '002008.SZ': {'code': '002008.SZ', 'name': '大族激光', 'industry': '电器仪表'}, '600565.SH': {'code': '600565.SH', 'name': '迪马股份', 'industry': '全国地产'}, '002147.SZ': {'code': '002147.SZ', 'name': '*ST新光', 'industry': '区域地产'}, '600503.SH': {'code': '600503.SH', 'name': '华丽家族', 'industry': '区域地产'}, '000410.SZ': {'code': '000410.SZ', 'name': 'ST沈机', 'industry': '机床制造'}, '300308.SZ': {'code': '300308.SZ', 'name': '中际旭创', 'industry': '通信设备'}, '002367.SZ': {'code': '002367.SZ', 'name': '康力电梯', 'industry': '运输设备'}, '603416.SH': {'code': '603416.SH', 'name': '信捷电气', 'industry': '电器仪表'}, '002348.SZ': {'code': '002348.SZ', 'name': '高乐股份', 'industry': '文教休闲'}, '002979.SZ': {'code': '002979.SZ', 'name': '雷赛智能', 'industry': '专用机械'}, '300461.SZ': {'code': '300461.SZ', 'name': '田中精机', 'industry': '专用机械'}, '002283.SZ': {'code': '002283.SZ', 'name': '天润工业', 'industry': '汽车配件'}, '600894.SH': {'code': '600894.SH', 'name': '广日股份', 'industry': '运输设备'}, '300580.SZ': {'code': '300580.SZ', 'name': '贝斯特', 'industry': '汽车配件'}, '600728.SH': {'code': '600728.SH', 'name': '佳都科技', 'industry': '软件服务'}, '002690.SZ': {'code': '002690.SZ', 'name': '美亚光电', 'industry': '专用机械'}, '688128.SH': {'code': '688128.SH', 'name': '中国电研', 'industry': '专用机械'}, '002067.SZ': {'code': '002067.SZ', 'name': '景兴纸业', 'industry': '造纸'}, '688155.SH': {'code': '688155.SH', 'name': '先惠技术', 'industry': '专用机械'}, '002625.SZ': {'code': '002625.SZ', 'name': '光启技术', 'industry': '航空'}, '300115.SZ': {'code': '300115.SZ', 'name': '长盈精密', 'industry': '元器件'}, '000850.SZ': {'code': '000850.SZ', 'name': '华茂股份', 'industry': '纺织'}, '688255.SH': {'code': '688255.SH', 'name': '凯尔达', 'industry': '机械基件'}, '002535.SZ': {'code': '002535.SZ', 'name': 'ST林重', 'industry': '工程机械'}, '600710.SH': {'code': '600710.SH', 'name': '苏美达', 'industry': '商贸代理'}, '300358.SZ': {'code': '300358.SZ', 'name': '楚天科技', 'industry': '医疗保健'}, '002526.SZ': {'code': '002526.SZ', 'name': '山东矿机', 'industry': '工程机械'}, '300367.SZ': {'code': '300367.SZ', 'name': 'ST网力', 'industry': 'IT设备'}, '002689.SZ': {'code': '002689.SZ', 'name': '远大智能', 'industry': '运输设备'}, '002583.SZ': {'code': '002583.SZ', 'name': '海能达', 'industry': '通信设备'}, '300188.SZ': {'code': '300188.SZ', 'name': '美亚柏科', 'industry': '软件服务'}, '000413.SZ': {'code': '000413.SZ', 'name': '东旭光电', 'industry': '元器件'}, '002031.SZ': {'code': '002031.SZ', 'name': '巨轮智能', 'industry': '汽车配件'}, '603030.SH': {'code': '603030.SH', 'name': '全筑股份', 'industry': '装修装饰'}, '688277.SH': {'code': '688277.SH', 'name': '天智航-U', 'industry': '医疗保健'}, '002131.SZ': {'code': '002131.SZ', 'name': '利欧股份', 'industry': '互联网'}, '300278.SZ': {'code': '300278.SZ', 'name': '*ST华昌', 'industry': '专用机械'}, '688165.SH': {'code': '688165.SH', 'name': '埃夫特-U', 'industry': '专用机械'}, '300280.SZ': {'code': '300280.SZ', 'name': '紫天科技', 'industry': '广告包装'}, '002611.SZ': {'code': '002611.SZ', 'name': '东方精工', 'industry': '轻工机械'}, '002527.SZ': {'code': '002527.SZ', 'name': '新时达', 'industry': '电器仪表'}, '002747.SZ': {'code': '002747.SZ', 'name': '埃斯顿', 'industry': '机械基件'}, '600775.SH': {'code': '600775.SH', 'name': '南京熊猫', 'industry': '通信设备'}, '002403.SZ': {'code': '002403.SZ', 'name': '爱仕达', 'industry': '家用电器'}, '600288.SH': {'code': '600288.SH', 'name': '大恒科技', 'industry': '软件服务'}, '300532.SZ': {'code': '300532.SZ', 'name': '今天国际', 'industry': '软件服务'}, '603486.SH': {'code': '603486.SH', 'name': '科沃斯', 'industry': '家用电器'}, '300276.SZ': {'code': '300276.SZ', 'name': '三丰智能', 'industry': '专用机械'}, '000404.SZ': {'code': '000404.SZ', 'name': '长虹华意', 'industry': '家用电器'}, '300044.SZ': {'code': '300044.SZ', 'name': '*ST赛为', 'industry': '软件服务'}, '002063.SZ': {'code': '002063.SZ', 'name': '远光软件', 'industry': '软件服务'}, '600346.SH': {'code': '600346.SH', 'name': '恒力石化', 'industry': '化纤'}, '603203.SH': {'code': '603203.SH', 'name': '快克股份', 'industry': '专用机械'}, '002376.SZ': {'code': '002376.SZ', 'name': '新北洋', 'industry': 'IT设备'}, '300486.SZ': {'code': '300486.SZ', 'name': '东杰智能', 'industry': '专用机械'}, '002520.SZ': {'code': '002520.SZ', 'name': '日发精机', 'industry': '机床制造'}, '002722.SZ': {'code': '002722.SZ', 'name': '金轮股份', 'industry': '纺织机械'}, '300023.SZ': {'code': '300023.SZ', 'name': '*ST宝德', 'industry': '专用机械'}, '000795.SZ': {'code': '000795.SZ', 'name': '英洛华', 'industry': '矿物制品'}, '300420.SZ': {'code': '300420.SZ', 'name': '五洋停车', 'industry': '机械基件'}, '603656.SH': {'code': '603656.SH', 'name': '泰禾智能', 'industry': '专用机械'}, '002334.SZ': {'code': '002334.SZ', 'name': '英威腾', 'industry': '电气设备'}, '300173.SZ': {'code': '300173.SZ', 'name': '福能东方', 'industry': '轻工机械'}, '300691.SZ': {'code': '300691.SZ', 'name': '联合光电', 'industry': '元器件'}, '688218.SH': {'code': '688218.SH', 'name': '江苏北人', 'industry': '专用机械'}, '000988.SZ': {'code': '000988.SZ', 'name': '华工科技', 'industry': '电器仪表'}, '603011.SH': {'code': '603011.SH', 'name': '合锻智能', 'industry': '机床制造'}, '001696.SZ': {'code': '001696.SZ', 'name': '宗申动力', 'industry': '摩托车'}, '300307.SZ': {'code': '300307.SZ', 'name': '慈星股份', 'industry': '纺织机械'}, '600579.SH': {'code': '600579.SH', 'name': '克劳斯', 'industry': '化工机械'}, '002090.SZ': {'code': '002090.SZ', 'name': '金智科技', 'industry': '软件服务'}, '002497.SZ': {'code': '002497.SZ', 'name': '雅化集团', 'industry': '化工原料'}, '688003.SH': {'code': '688003.SH', 'name': '天准科技', 'industry': '专用机械'}, '301199.SZ': {'code': '301199.SZ', 'name': '迈赫股份', 'industry': '专用机械'}, '002009.SZ': {'code': '002009.SZ', 'name': '天奇股份', 'industry': '工程机械'}, '688090.SH': {'code': '688090.SH', 'name': '瑞松科技', 'industry': '专用机械'}, '300543.SZ': {'code': '300543.SZ', 'name': '朗科智能', 'industry': '电气设备'}, '002139.SZ': {'code': '002139.SZ', 'name': '拓邦股份', 'industry': '元器件'}, '002957.SZ': {'code': '002957.SZ', 'name': '科瑞技术', 'industry': '专用机械'}, '300382.SZ': {'code': '300382.SZ', 'name': '斯莱克', 'industry': '专用机械'}, '605056.SH': {'code': '605056.SH', 'name': '咸亨国际', 'industry': '电器仪表'}, '603960.SH': {'code': '603960.SH', 'name': '克来机电', 'industry': '汽车配件'}, '300281.SZ': {'code': '300281.SZ', 'name': '金明精机', 'industry': '专用机械'}, '600843.SH': {'code': '600843.SH', 'name': '上工申贝', 'industry': '纺织机械'}, '002380.SZ': {'code': '002380.SZ', 'name': '科远智慧', 'industry': '电气设备'}, '002229.SZ': {'code': '002229.SZ', 'name': '鸿博股份', 'industry': '广告包装'}, '002097.SZ': {'code': '002097.SZ', 'name': '山河智能', 'industry': '工程机械'}, '002441.SZ': {'code': '002441.SZ', 'name': '众业达', 'industry': '批发业'}, '002006.SZ': {'code': '002006.SZ', 'name': '精功科技', 'industry': '专用机械'}, '002577.SZ': {'code': '002577.SZ', 'name': '雷柏科技', 'industry': 'IT设备'}, '002892.SZ': {'code': '002892.SZ', 'name': '科力尔', 'industry': '电气设备'}, '300002.SZ': {'code': '300002.SZ', 'name': '神州泰岳', 'industry': '软件服务'}, '002011.SZ': {'code': '002011.SZ', 'name': '盾安环境', 'industry': '家用电器'}, '002559.SZ': {'code': '002559.SZ', 'name': '亚威股份', 'industry': '机床制造'}, '002184.SZ': {'code': '002184.SZ', 'name': '海得控制', 'industry': '软件服务'}, '600560.SH': {'code': '600560.SH', 'name': '金自天正', 'industry': '电气设备'}, '300154.SZ': {'code': '300154.SZ', 'name': '瑞凌股份', 'industry': '机械基件'}, '300201.SZ': {'code': '300201.SZ', 'name': '海伦哲', 'industry': '专用机械'}, '002599.SZ': {'code': '002599.SZ', 'name': '盛通股份', 'industry': '广告包装'}, '688558.SH': {'code': '688558.SH', 'name': '国盛智科', 'industry': '机床制造'}, '603015.SH': {'code': '603015.SH', 'name': '弘讯科技', 'industry': '电气设备'}, '002547.SZ': {'code': '002547.SZ', 'name': '春兴精工', 'industry': '通信设备'}, '300279.SZ': {'code': '300279.SZ', 'name': '和晶科技', 'industry': '元器件'}, '300097.SZ': {'code': '300097.SZ', 'name': '智云股份', 'industry': '专用机械'}, '688248.SH': {'code': '688248.SH', 'name': '南网科技', 'industry': '电气设备'}, '002337.SZ': {'code': '002337.SZ', 'name': '赛象科技', 'industry': '化工机械'}, '002270.SZ': {'code': '002270.SZ', 'name': '华明装备', 'industry': '电气设备'}, '300134.SZ': {'code': '300134.SZ', 'name': '大富科技', 'industry': '通信设备'}, '300282.SZ': {'code': '300282.SZ', 'name': '三盛教育', 'industry': '文教休闲'}, '000837.SZ': {'code': '000837.SZ', 'name': '秦川机床', 'industry': '机床制造'}, '300663.SZ': {'code': '300663.SZ', 'name': '科蓝软件', 'industry': '软件服务'}, '300249.SZ': {'code': '300249.SZ', 'name': '依米康', 'industry': '软件服务'}, '300222.SZ': {'code': '300222.SZ', 'name': '科大智能', 'industry': '电气设备'}, '300126.SZ': {'code': '300126.SZ', 'name': '锐奇股份', 'industry': '轻工机械'}, '300802.SZ': {'code': '300802.SZ', 'name': '矩子科技', 'industry': 'IT设备'}, '002363.SZ': {'code': '002363.SZ', 'name': '隆基机械', 'industry': '汽车配件'}, '600520.SH': {'code': '600520.SH', 'name': '文一科技', 'industry': '机械基件'}, '603131.SH': {'code': '603131.SH', 'name': '上海沪工', 'industry': '专用机械'}, '002660.SZ': {'code': '002660.SZ', 'name': '茂硕电源', 'industry': '电气设备'}, '300607.SZ': {'code': '300607.SZ', 'name': '拓斯达', 'industry': '专用机械'}, '300415.SZ': {'code': '300415.SZ', 'name': '伊之密', 'industry': '专用机械'}, '300195.SZ': {'code': '300195.SZ', 'name': '长荣股份', 'industry': '轻工机械'}, '300112.SZ': {'code': '300112.SZ', 'name': '万讯自控', 'industry': '电器仪表'}, '300076.SZ': {'code': '300076.SZ', 'name': 'GQY视讯', 'industry': 'IT设备'}, '688025.SH': {'code': '688025.SH', 'name': '杰普特', 'industry': '元器件'}, '002903.SZ': {'code': '002903.SZ', 'name': '宇环数控', 'industry': '机床制造'}, '300293.SZ': {'code': '300293.SZ', 'name': '蓝英装备', 'industry': '专用机械'}, '300466.SZ': {'code': '300466.SZ', 'name': '赛摩智能', 'industry': '电器仪表'}, '002026.SZ': {'code': '002026.SZ', 'name': '山东威达', 'industry': '机械基件'}, '300161.SZ': {'code': '300161.SZ', 'name': '华中数控', 'industry': '机床制造'}, '600633.SH': {'code': '600633.SH', 'name': '浙数文化', 'industry': '互联网'}, '300533.SZ': {'code': '300533.SZ', 'name': '冰川网络', 'industry': '互联网'}, '300051.SZ': {'code': '300051.SZ', 'name': 'ST三五', 'industry': '互联网'}, '600880.SH': {'code': '600880.SH', 'name': '博瑞传播', 'industry': '广告包装'}, '002464.SZ': {'code': '002464.SZ', 'name': '*ST众应', 'industry': '互联网'}, '600576.SH': {'code': '600576.SH', 'name': '祥源文化', 'industry': '影视音像'}, '600637.SH': {'code': '600637.SH', 'name': '东方明珠', 'industry': '影视音像'}, '600198.SH': {'code': '600198.SH', 'name': '*ST大唐', 'industry': '通信设备'}, '603555.SH': {'code': '603555.SH', 'name': 'ST贵人', 'industry': '服饰'}, '002739.SZ': {'code': '002739.SZ', 'name': '万达电影', 'industry': '影视音像'}, '601360.SH': {'code': '601360.SH', 'name': '三六零', 'industry': '互联网'}, '601801.SH': {'code': '601801.SH', 'name': '皖新传媒', 'industry': '出版业'}, '000038.SZ': {'code': '000038.SZ', 'name': '深大通', 'industry': '综合类'}, '600138.SH': {'code': '600138.SH', 'name': '中青旅', 'industry': '旅游服务'}, '600100.SH': {'code': '600100.SH', 'name': '同方股份', 'industry': 'IT设备'}, '300251.SZ': {'code': '300251.SZ', 'name': '光线传媒', 'industry': '影视音像'}, '300027.SZ': {'code': '300027.SZ', 'name': '华谊兄弟', 'industry': '影视音像'}, '600037.SH': {'code': '600037.SH', 'name': '歌华有线', 'industry': '影视音像'}, '600173.SH': {'code': '600173.SH', 'name': '卧龙地产', 'industry': '全国地产'}, '300846.SZ': {'code': '300846.SZ', 'name': '首都在线', 'industry': '软件服务'}, '002919.SZ': {'code': '002919.SZ', 'name': '名臣健康', 'industry': '日用化工'}, '002447.SZ': {'code': '002447.SZ', 'name': '*ST晨鑫', 'industry': '互联网'}, '300133.SZ': {'code': '300133.SZ', 'name': '华策影视', 'industry': '影视音像'}, '603000.SH': {'code': '603000.SH', 'name': '人民网', 'industry': '互联网'}, '002261.SZ': {'code': '002261.SZ', 'name': '拓维信息', 'industry': '互联网'}, '002502.SZ': {'code': '002502.SZ', 'name': '鼎龙文化', 'industry': '影视音像'}, '600892.SH': {'code': '600892.SH', 'name': '大晟文化', 'industry': '影视音像'}, '000835.SZ': {'code': '000835.SZ', 'name': '*ST长动', 'industry': '影视音像'}, '601928.SH': {'code': '601928.SH', 'name': '凤凰传媒', 'industry': '出版业'}, '000793.SZ': {'code': '000793.SZ', 'name': '华闻集团', 'industry': '出版业'}, '300518.SZ': {'code': '300518.SZ', 'name': '盛讯达', 'industry': '互联网'}, '300089.SZ': {'code': '300089.SZ', 'name': 'ST文化', 'industry': '文教休闲'}, '002113.SZ': {'code': '002113.SZ', 'name': 'ST天润', 'industry': '互联网'}, '002571.SZ': {'code': '002571.SZ', 'name': '德力股份', 'industry': '玻璃'}, '603444.SH': {'code': '603444.SH', 'name': '吉比特', 'industry': '互联网'}, '002306.SZ': {'code': '002306.SZ', 'name': '中科云网', 'industry': '互联网'}, '300299.SZ': {'code': '300299.SZ', 'name': '富春股份', 'industry': '互联网'}, '002605.SZ': {'code': '002605.SZ', 'name': '姚记科技', 'industry': '互联网'}, '300857.SZ': {'code': '300857.SZ', 'name': '协创数据', 'industry': 'IT设备'}, '600234.SH': {'code': '600234.SH', 'name': '科新发展', 'industry': '综合类'}, '600770.SH': {'code': '600770.SH', 'name': '综艺股份', 'industry': '综合类'}, '000004.SZ': {'code': '000004.SZ', 'name': '国华网安', 'industry': '软件服务'}, '300478.SZ': {'code': '300478.SZ', 'name': '杭州高新', 'industry': '橡胶'}, '002141.SZ': {'code': '002141.SZ', 'name': '贤丰控股', 'industry': '电气设备'}, '600556.SH': {'code': '600556.SH', 'name': '天下秀', 'industry': '互联网'}, '002862.SZ': {'code': '002862.SZ', 'name': '实丰文化', 'industry': '文教休闲'}, '600373.SH': {'code': '600373.SH', 'name': '中文传媒', 'industry': '出版业'}, '000917.SZ': {'code': '000917.SZ', 'name': '电广传媒', 'industry': '影视音像'}, '300315.SZ': {'code': '300315.SZ', 'name': '掌趣科技', 'industry': '互联网'}, '600715.SH': {'code': '600715.SH', 'name': '文投控股', 'industry': '影视音像'}, '000676.SZ': {'code': '000676.SZ', 'name': '智度股份', 'industry': '互联网'}, '603466.SH': {'code': '603466.SH', 'name': '风语筑', 'industry': '文教休闲'}, '600226.SH': {'code': '600226.SH', 'name': 'ST瀚叶', 'industry': '互联网'}, '600652.SH': {'code': '600652.SH', 'name': '*ST游久', 'industry': '互联网'}, '000892.SZ': {'code': '000892.SZ', 'name': '欢瑞世纪', 'industry': '影视音像'}, '002291.SZ': {'code': '002291.SZ', 'name': '星期六', 'industry': '服饰'}, '603258.SH': {'code': '603258.SH', 'name': '电魂网络', 'industry': '互联网'}, '002354.SZ': {'code': '002354.SZ', 'name': '天神娱乐', 'industry': '互联网'}, '300467.SZ': {'code': '300467.SZ', 'name': '迅游科技', 'industry': '互联网'}, '300250.SZ': {'code': '300250.SZ', 'name': '初灵信息', 'industry': '软件服务'}, '002426.SZ': {'code': '002426.SZ', 'name': '胜利精密', 'industry': '元器件'}, '300479.SZ': {'code': '300479.SZ', 'name': '神思电子', 'industry': '软件服务'}, '688686.SH': {'code': '688686.SH', 'name': '奥普特', 'industry': '电器仪表'}, '300545.SZ': {'code': '300545.SZ', 'name': '联得装备', 'industry': '专用机械'}, '300836.SZ': {'code': '300836.SZ', 'name': '佰奥智能', 'industry': '专用机械'}, '300730.SZ': {'code': '300730.SZ', 'name': '科创信息', 'industry': '软件服务'}, '000948.SZ': {'code': '000948.SZ', 'name': '南天信息', 'industry': '软件服务'}, '688787.SH': {'code': '688787.SH', 'name': '海天瑞声', 'industry': '软件服务'}, '300018.SZ': {'code': '300018.SZ', 'name': '中元股份', 'industry': '电气设备'}, '688234.SH': {'code': '688234.SH', 'name': '天岳先进-U', 'industry': '半导体'}, '300373.SZ': {'code': '300373.SZ', 'name': '扬杰科技', 'industry': '半导体'}, '605358.SH': {'code': '605358.SH', 'name': '立昂微', 'industry': '半导体'}, '002430.SZ': {'code': '002430.SZ', 'name': '杭氧股份', 'industry': '化工机械'}, '688689.SH': {'code': '688689.SH', 'name': '银河微电', 'industry': '元器件'}, '600459.SH': {'code': '600459.SH', 'name': '贵研铂业', 'industry': '小金属'}, '600460.SH': {'code': '600460.SH', 'name': '士兰微', 'industry': '半导体'}, '002243.SZ': {'code': '002243.SZ', 'name': '力合科创', 'industry': '塑料'}, '301118.SZ': {'code': '301118.SZ', 'name': '恒光股份', 'industry': '化工原料'}, '603501.SH': {'code': '603501.SH', 'name': '韦尔股份', 'industry': '半导体'}, '688256.SH': {'code': '688256.SH', 'name': '寒武纪-U', 'industry': '元器件'}, '603986.SH': {'code': '603986.SH', 'name': '兆易创新', 'industry': '半导体'}, '002180.SZ': {'code': '002180.SZ', 'name': '纳思达', 'industry': 'IT设备'}, '300604.SZ': {'code': '300604.SZ', 'name': '长川科技', 'industry': '专用机械'}, '003031.SZ': {'code': '003031.SZ', 'name': '中瓷电子', 'industry': '元器件'}, '300480.SZ': {'code': '300480.SZ', 'name': '光力科技', 'industry': '专用机械'}, '600745.SH': {'code': '600745.SH', 'name': '闻泰科技', 'industry': '通信设备'}, '300661.SZ': {'code': '300661.SZ', 'name': '圣邦股份', 'industry': '元器件'}, '603690.SH': {'code': '603690.SH', 'name': '至纯科技', 'industry': '半导体'}, '688106.SH': {'code': '688106.SH', 'name': '金宏气体', 'industry': '化工原料'}, '000100.SZ': {'code': '000100.SZ', 'name': 'TCL科技', 'industry': '元器件'}, '688012.SH': {'code': '688012.SH', 'name': '中微公司', 'industry': '专用机械'}, '002288.SZ': {'code': '002288.SZ', 'name': '超华科技', 'industry': '元器件'}, '688981.SH': {'code': '688981.SH', 'name': '中芯国际', 'industry': '半导体'}, '002516.SZ': {'code': '002516.SZ', 'name': '旷达科技', 'industry': '汽车配件'}, '605111.SH': {'code': '605111.SH', 'name': '新洁能', 'industry': '半导体'}, '688200.SH': {'code': '688200.SH', 'name': '华峰测控', 'industry': '专用机械'}, '002371.SZ': {'code': '002371.SZ', 'name': '北方华创', 'industry': '半导体'}, '300672.SZ': {'code': '300672.SZ', 'name': '国科微', 'industry': '半导体'}, '603290.SH': {'code': '603290.SH', 'name': '斯达半导', 'industry': '半导体'}, '002429.SZ': {'code': '002429.SZ', 'name': '兆驰股份', 'industry': '家用电器'}, '600877.SH': {'code': '600877.SH', 'name': '声光电科', 'industry': '电气设备'}, '603379.SH': {'code': '603379.SH', 'name': '三美股份', 'industry': '化工原料'}, '300223.SZ': {'code': '300223.SZ', 'name': '北京君正', 'industry': '半导体'}, '000062.SZ': {'code': '000062.SZ', 'name': '深圳华强', 'industry': '批发业'}, '002049.SZ': {'code': '002049.SZ', 'name': '紫光国微', 'industry': '元器件'}, '688017.SH': {'code': '688017.SH', 'name': '绿的谐波', 'industry': '机械基件'}, '688662.SH': {'code': '688662.SH', 'name': '富信科技', 'industry': '半导体'}, '600171.SH': {'code': '600171.SH', 'name': '上海贝岭', 'industry': '半导体'}, '002436.SZ': {'code': '002436.SZ', 'name': '兴森科技', 'industry': '元器件'}, '600641.SH': {'code': '600641.SH', 'name': '万业企业', 'industry': '区域地产'}, '600406.SH': {'code': '600406.SH', 'name': '国电南瑞', 'industry': '电气设备'}, '000913.SZ': {'code': '000913.SZ', 'name': '钱江摩托', 'industry': '摩托车'}, '002185.SZ': {'code': '002185.SZ', 'name': '华天科技', 'industry': '半导体'}, '688107.SH': {'code': '688107.SH', 'name': '安路科技-U', 'industry': '半导体'}, '600071.SH': {'code': '600071.SH', 'name': '凤凰光学', 'industry': '元器件'}, '002402.SZ': {'code': '002402.SZ', 'name': '和而泰', 'industry': '元器件'}, '603068.SH': {'code': '603068.SH', 'name': '博通集成', 'industry': '半导体'}, '600667.SH': {'code': '600667.SH', 'name': '太极实业', 'industry': '半导体'}, '300139.SZ': {'code': '300139.SZ', 'name': '晓程科技', 'industry': '元器件'}, '300316.SZ': {'code': '300316.SZ', 'name': '晶盛机电', 'industry': '专用机械'}, '600584.SH': {'code': '600584.SH', 'name': '长电科技', 'industry': '半导体'}, '688126.SH': {'code': '688126.SH', 'name': '沪硅产业-U', 'industry': '半导体'}, '300046.SZ': {'code': '300046.SZ', 'name': '台基股份', 'industry': '半导体'}, '002156.SZ': {'code': '002156.SZ', 'name': '通富微电', 'industry': '半导体'}, '603155.SH': {'code': '603155.SH', 'name': '新亚强', 'industry': '化工原料'}, '688230.SH': {'code': '688230.SH', 'name': '芯导科技', 'industry': '半导体'}, '300671.SZ': {'code': '300671.SZ', 'name': '富满微', 'industry': '半导体'}, '603058.SH': {'code': '603058.SH', 'name': '永吉股份', 'industry': '广告包装'}, '688079.SH': {'code': '688079.SH', 'name': '美迪凯', 'industry': '半导体'}, '688728.SH': {'code': '688728.SH', 'name': '格科微', 'industry': '半导体'}, '300263.SZ': {'code': '300263.SZ', 'name': '隆华科技', 'industry': '专用机械'}, '002579.SZ': {'code': '002579.SZ', 'name': '中京电子', 'industry': '元器件'}, '000936.SZ': {'code': '000936.SZ', 'name': '华西股份', 'industry': '化纤'}, '688396.SH': {'code': '688396.SH', 'name': '华润微', 'industry': '半导体'}, '002975.SZ': {'code': '002975.SZ', 'name': '博杰股份', 'industry': '专用机械'}, '688127.SH': {'code': '688127.SH', 'name': '蓝特光学', 'industry': '元器件'}, '600360.SH': {'code': '600360.SH', 'name': '华微电子', 'industry': '半导体'}, '300123.SZ': {'code': '300123.SZ', 'name': '亚光科技', 'industry': '半导体'}, '300327.SZ': {'code': '300327.SZ', 'name': '中颖电子', 'industry': '半导体'}, '002617.SZ': {'code': '002617.SZ', 'name': '露笑科技', 'industry': '电气设备'}, '688711.SH': {'code': '688711.SH', 'name': '宏微科技', 'industry': '半导体'}, '688099.SH': {'code': '688099.SH', 'name': '晶晨股份', 'industry': '半导体'}, '000818.SZ': {'code': '000818.SZ', 'name': '航锦科技', 'industry': '化工原料'}, '002745.SZ': {'code': '002745.SZ', 'name': '木林森', 'industry': '电气设备'}, '300567.SZ': {'code': '300567.SZ', 'name': '精测电子', 'industry': '电器仪表'}, '300323.SZ': {'code': '300323.SZ', 'name': '华灿光电', 'industry': '半导体'}, '603160.SH': {'code': '603160.SH', 'name': '汇顶科技', 'industry': '元器件'}, '300054.SZ': {'code': '300054.SZ', 'name': '鼎龙股份', 'industry': '化工原料'}, '688598.SH': {'code': '688598.SH', 'name': '金博股份', 'industry': '矿物制品'}, '003026.SZ': {'code': '003026.SZ', 'name': '中晶科技', 'industry': '半导体'}, '002119.SZ': {'code': '002119.SZ', 'name': '康强电子', 'industry': '半导体'}, '300353.SZ': {'code': '300353.SZ', 'name': '东土科技', 'industry': '通信设备'}, '003009.SZ': {'code': '003009.SZ', 'name': '中天火箭', 'industry': '航空'}, '002845.SZ': {'code': '002845.SZ', 'name': '同兴达', 'industry': '元器件'}, '002341.SZ': {'code': '002341.SZ', 'name': '新纶新材', 'industry': '化工原料'}, '002171.SZ': {'code': '002171.SZ', 'name': '楚江新材', 'industry': '铜'}, '002169.SZ': {'code': '002169.SZ', 'name': '智光电气', 'industry': '电气设备'}, '600658.SH': {'code': '600658.SH', 'name': '电子城', 'industry': '园区开发'}, '300613.SZ': {'code': '300613.SZ', 'name': '富瀚微', 'industry': '半导体'}, '603726.SH': {'code': '603726.SH', 'name': '朗迪集团', 'industry': '家用电器'}, '002077.SZ': {'code': '002077.SZ', 'name': '大港股份', 'industry': '半导体'}, '600753.SH': {'code': '600753.SH', 'name': '东方银星', 'industry': '商贸代理'}, '300474.SZ': {'code': '300474.SZ', 'name': '景嘉微', 'industry': '元器件'}, '300184.SZ': {'code': '300184.SZ', 'name': '力源信息', 'industry': '商贸代理'}, '003043.SZ': {'code': '003043.SZ', 'name': '华亚智能', 'industry': '专用机械'}, '002023.SZ': {'code': '002023.SZ', 'name': '海特高新', 'industry': '航空'}, '300708.SZ': {'code': '300708.SZ', 'name': '聚灿光电', 'industry': '半导体'}, '688216.SH': {'code': '688216.SH', 'name': '气派科技', 'industry': '半导体'}, '002046.SZ': {'code': '002046.SZ', 'name': '国机精工', 'industry': '机械基件'}, '300782.SZ': {'code': '300782.SZ', 'name': '卓胜微', 'industry': '元器件'}, '300303.SZ': {'code': '300303.SZ', 'name': '聚飞光电', 'industry': '半导体'}, '300706.SZ': {'code': '300706.SZ', 'name': '阿石创', 'industry': '元器件'}, '600330.SH': {'code': '600330.SH', 'name': '天通股份', 'industry': '元器件'}, '300102.SZ': {'code': '300102.SZ', 'name': '乾照光电', 'industry': '半导体'}, '603938.SH': {'code': '603938.SH', 'name': '三孚股份', 'industry': '化工原料'}, '300283.SZ': {'code': '300283.SZ', 'name': '温州宏丰', 'industry': '电气设备'}, '300814.SZ': {'code': '300814.SZ', 'name': '中富电路', 'industry': '元器件'}, '002428.SZ': {'code': '002428.SZ', 'name': '云南锗业', 'industry': '小金属'}, '688186.SH': {'code': '688186.SH', 'name': '广大特材', 'industry': '特种钢'}, '002054.SZ': {'code': '002054.SZ', 'name': '德美化工', 'industry': '化工原料'}, '600206.SH': {'code': '600206.SH', 'name': '有研新材', 'industry': '半导体'}, '600468.SH': {'code': '600468.SH', 'name': '百利电气', 'industry': '电气设备'}, '300670.SZ': {'code': '300670.SZ', 'name': '大烨智能', 'industry': '电气设备'}, '300405.SZ': {'code': '300405.SZ', 'name': '科隆股份', 'industry': '化工原料'}, '688383.SH': {'code': '688383.SH', 'name': '新益昌', 'industry': '专用机械'}, '688661.SH': {'code': '688661.SH', 'name': '和林微纳', 'industry': '元器件'}, '300376.SZ': {'code': '300376.SZ', 'name': '易事特', 'industry': '电气设备'}, '603688.SH': {'code': '603688.SH', 'name': '石英股份', 'industry': '矿物制品'}, '300322.SZ': {'code': '300322.SZ', 'name': '硕贝德', 'industry': '通信设备'}, '300812.SZ': {'code': '300812.SZ', 'name': '易天股份', 'industry': '专用机械'}, '688328.SH': {'code': '688328.SH', 'name': '深科达', 'industry': '元器件'}, '002655.SZ': {'code': '002655.SZ', 'name': '共达电声', 'industry': '元器件'}, '300183.SZ': {'code': '300183.SZ', 'name': '东软载波', 'industry': '通信设备'}, '600703.SH': {'code': '600703.SH', 'name': '三安光电', 'industry': '半导体'}, '600160.SH': {'code': '600160.SH', 'name': '巨化股份', 'industry': '化工原料'}, '002983.SZ': {'code': '002983.SZ', 'name': '芯瑞达', 'industry': '元器件'}, '603283.SH': {'code': '603283.SH', 'name': '赛腾股份', 'industry': '专用机械'}, '300296.SZ': {'code': '300296.SZ', 'name': '利亚德', 'industry': '半导体'}, '688286.SH': {'code': '688286.SH', 'name': '敏芯股份', 'industry': '元器件'}, '688233.SH': {'code': '688233.SH', 'name': '神工股份', 'industry': '化工原料'}, '603595.SH': {'code': '603595.SH', 'name': '东尼电子', 'industry': '元器件'}, '300903.SZ': {'code': '300903.SZ', 'name': '科翔股份', 'industry': '元器件'}, '002902.SZ': {'code': '002902.SZ', 'name': '铭普光磁', 'industry': '元器件'}, '300053.SZ': {'code': '300053.SZ', 'name': '欧比特', 'industry': '半导体'}, '605588.SH': {'code': '605588.SH', 'name': '冠石科技', 'industry': '半导体'}, '600141.SH': {'code': '600141.SH', 'name': '兴发集团', 'industry': '化工原料'}, '300665.SZ': {'code': '300665.SZ', 'name': '飞鹿股份', 'industry': '染料涂料'}, '603929.SH': {'code': '603929.SH', 'name': '亚翔集成', 'industry': '装修装饰'}, '688082.SH': {'code': '688082.SH', 'name': '盛美上海', 'industry': '半导体'}, '002449.SZ': {'code': '002449.SZ', 'name': '国星光电', 'industry': '半导体'}, '300484.SZ': {'code': '300484.SZ', 'name': '蓝海华腾', 'industry': '电气设备'}, '300831.SZ': {'code': '300831.SZ', 'name': '派瑞股份', 'industry': '元器件'}, '002725.SZ': {'code': '002725.SZ', 'name': '跃岭股份', 'industry': '汽车配件'}, '601908.SH': {'code': '601908.SH', 'name': '京运通', 'industry': '新型电力'}, '603386.SH': {'code': '603386.SH', 'name': '广东骏亚', 'industry': '元器件'}, '000925.SZ': {'code': '000925.SZ', 'name': '众合科技', 'industry': '专用机械'}, '300666.SZ': {'code': '300666.SZ', 'name': '江丰电子', 'industry': '元器件'}, '300395.SZ': {'code': '300395.SZ', 'name': '菲利华', 'industry': '玻璃'}, '300390.SZ': {'code': '300390.SZ', 'name': '天华超净', 'industry': '电气设备'}, '300400.SZ': {'code': '300400.SZ', 'name': '劲拓股份', 'industry': '专用机械'}, '300689.SZ': {'code': '300689.SZ', 'name': '澄天伟业', 'industry': '元器件'}, '300493.SZ': {'code': '300493.SZ', 'name': '润欣科技', 'industry': '通信设备'}, '688551.SH': {'code': '688551.SH', 'name': '科威尔', 'industry': '专用机械'}, '300260.SZ': {'code': '300260.SZ', 'name': '新莱应材', 'industry': '机械基件'}, '300820.SZ': {'code': '300820.SZ', 'name': '英杰电气', 'industry': '电气设备'}, '002346.SZ': {'code': '002346.SZ', 'name': '柘中股份', 'industry': '电气设备'}, '300077.SZ': {'code': '300077.SZ', 'name': '国民技术', 'industry': '半导体'}, '300287.SZ': {'code': '300287.SZ', 'name': '飞利信', 'industry': '软件服务'}, '603933.SH': {'code': '603933.SH', 'name': '睿能科技', 'industry': '商贸代理'}, '300650.SZ': {'code': '300650.SZ', 'name': '太龙股份', 'industry': '电气设备'}, '003002.SZ': {'code': '003002.SZ', 'name': '壶化股份', 'industry': '化工原料'}, '300455.SZ': {'code': '300455.SZ', 'name': '康拓红外', 'industry': '运输设备'}, '002552.SZ': {'code': '002552.SZ', 'name': '宝鼎科技', 'industry': '机械基件'}, '002338.SZ': {'code': '002338.SZ', 'name': '奥普光电', 'industry': '电器仪表'}, '300875.SZ': {'code': '300875.SZ', 'name': '捷强装备', 'industry': '专用机械'}, '300659.SZ': {'code': '300659.SZ', 'name': '中孚信息', 'industry': '软件服务'}, '600410.SH': {'code': '600410.SH', 'name': '华胜天成', 'industry': '软件服务'}, '603809.SH': {'code': '603809.SH', 'name': '豪能股份', 'industry': '汽车配件'}, '002977.SZ': {'code': '002977.SZ', 'name': '天箭科技', 'industry': '通信设备'}, '002654.SZ': {'code': '002654.SZ', 'name': '万润科技', 'industry': '互联网'}, '603665.SH': {'code': '603665.SH', 'name': '康隆达', 'industry': '纺织'}, '300547.SZ': {'code': '300547.SZ', 'name': '川环科技', 'industry': '汽车配件'}, '603267.SH': {'code': '603267.SH', 'name': '鸿远电子', 'industry': '元器件'}, '000825.SZ': {'code': '000825.SZ', 'name': '太钢不锈', 'industry': '特种钢'}, '688682.SH': {'code': '688682.SH', 'name': '霍莱沃', 'industry': '软件服务'}, '688586.SH': {'code': '688586.SH', 'name': '江航装备', 'industry': '航空'}, '603936.SH': {'code': '603936.SH', 'name': '博敏电子', 'industry': '元器件'}, '002684.SZ': {'code': '002684.SZ', 'name': '*ST猛狮', 'industry': '汽车服务'}, '600705.SH': {'code': '600705.SH', 'name': '中航产融', 'industry': '多元金融'}, '002300.SZ': {'code': '002300.SZ', 'name': '太阳电缆', 'industry': '电气设备'}, '000932.SZ': {'code': '000932.SZ', 'name': '华菱钢铁', 'industry': '普钢'}, '600375.SH': {'code': '600375.SH', 'name': '汉马科技', 'industry': '汽车整车'}, '300922.SZ': {'code': '300922.SZ', 'name': '天秦装备', 'industry': '专用机械'}, '300699.SZ': {'code': '300699.SZ', 'name': '光威复材', 'industry': '化工原料'}, '000678.SZ': {'code': '000678.SZ', 'name': '襄阳轴承', 'industry': '汽车配件'}, '002246.SZ': {'code': '002246.SZ', 'name': '北化股份', 'industry': '化工原料'}, '000886.SZ': {'code': '000886.SZ', 'name': '海南高速', 'industry': '路桥'}, '300379.SZ': {'code': '300379.SZ', 'name': '东方通', 'industry': '软件服务'}, '002111.SZ': {'code': '002111.SZ', 'name': '威海广泰', 'industry': '航空'}, '600736.SH': {'code': '600736.SH', 'name': '苏州高新', 'industry': '园区开发'}, '600363.SH': {'code': '600363.SH', 'name': '联创光电', 'industry': '元器件'}, '601989.SH': {'code': '601989.SH', 'name': '中国重工', 'industry': '船舶'}, '688027.SH': {'code': '688027.SH', 'name': '国盾量子', 'industry': '通信设备'}, '000099.SZ': {'code': '000099.SZ', 'name': '中信海直', 'industry': '空运'}, '601208.SH': {'code': '601208.SH', 'name': '东材科技', 'industry': '化工原料'}, '601718.SH': {'code': '601718.SH', 'name': '际华集团', 'industry': '服饰'}, '688568.SH': {'code': '688568.SH', 'name': '中科星图', 'industry': '软件服务'}, '688151.SH': {'code': '688151.SH', 'name': '华强科技', 'industry': '专用机械'}, '300229.SZ': {'code': '300229.SZ', 'name': '拓尔思', 'industry': '软件服务'}, '300354.SZ': {'code': '300354.SZ', 'name': '东华测试', 'industry': '电器仪表'}, '002848.SZ': {'code': '002848.SZ', 'name': '高斯贝尔', 'industry': '家用电器'}, '601118.SH': {'code': '601118.SH', 'name': '海南橡胶', 'industry': '橡胶'}, '603738.SH': {'code': '603738.SH', 'name': '泰晶科技', 'industry': '元器件'}, '300008.SZ': {'code': '300008.SZ', 'name': '天海防务', 'industry': '船舶'}, '603629.SH': {'code': '603629.SH', 'name': '利通电子', 'industry': '元器件'}, '601958.SH': {'code': '601958.SH', 'name': '金钼股份', 'industry': '小金属'}, '601106.SH': {'code': '601106.SH', 'name': '中国一重', 'industry': '工程机械'}, '000800.SZ': {'code': '000800.SZ', 'name': '一汽解放', 'industry': '汽车整车'}, '300185.SZ': {'code': '300185.SZ', 'name': '通裕重工', 'industry': '工程机械'}, '002080.SZ': {'code': '002080.SZ', 'name': '中材科技', 'industry': '化纤'}, '603308.SH': {'code': '603308.SH', 'name': '应流股份', 'industry': '专用机械'}, '000425.SZ': {'code': '000425.SZ', 'name': '徐工机械', 'industry': '工程机械'}, '600685.SH': {'code': '600685.SH', 'name': '中船防务', 'industry': '船舶'}, '600031.SH': {'code': '600031.SH', 'name': '三一重工', 'industry': '工程机械'}, '601698.SH': {'code': '601698.SH', 'name': '中国卫通', 'industry': '电信运营'}, '688002.SH': {'code': '688002.SH', 'name': '睿创微纳', 'industry': '通信设备'}, '300217.SZ': {'code': '300217.SZ', 'name': '东方电热', 'industry': '家用电器'}, '002404.SZ': {'code': '002404.SZ', 'name': '嘉欣丝绸', 'industry': '纺织'}, '600117.SH': {'code': '600117.SH', 'name': '西宁特钢', 'industry': '特种钢'}, '600118.SH': {'code': '600118.SH', 'name': '中国卫星', 'industry': '航空'}, '688561.SH': {'code': '688561.SH', 'name': '奇安信-U', 'industry': '软件服务'}, '603766.SH': {'code': '603766.SH', 'name': '隆鑫通用', 'industry': '摩托车'}, '603678.SH': {'code': '603678.SH', 'name': '火炬电子', 'industry': '元器件'}, '002519.SZ': {'code': '002519.SZ', 'name': '银河电子', 'industry': '通信设备'}, '600271.SH': {'code': '600271.SH', 'name': '航天信息', 'industry': 'IT设备'}, '000599.SZ': {'code': '000599.SZ', 'name': '青岛双星', 'industry': '汽车配件'}, '601611.SH': {'code': '601611.SH', 'name': '中国核建', 'industry': '建筑工程'}, '600482.SH': {'code': '600482.SH', 'name': '中国动力', 'industry': '船舶'}, '300325.SZ': {'code': '300325.SZ', 'name': '*ST德威', 'industry': '塑料'}, '300095.SZ': {'code': '300095.SZ', 'name': '华伍股份', 'industry': '机械基件'}, '000697.SZ': {'code': '000697.SZ', 'name': '炼石航空', 'industry': '航空'}, '600435.SH': {'code': '600435.SH', 'name': '北方导航', 'industry': '专用机械'}, '688227.SH': {'code': '688227.SH', 'name': '品高股份', 'industry': '软件服务'}, '002724.SZ': {'code': '002724.SZ', 'name': '海洋王', 'industry': '半导体'}, '002501.SZ': {'code': '002501.SZ', 'name': '*ST利源', 'industry': '铝'}, '002276.SZ': {'code': '002276.SZ', 'name': '万马股份', 'industry': '电气设备'}, '300938.SZ': {'code': '300938.SZ', 'name': '信测标准', 'industry': '综合类'}, '000801.SZ': {'code': '000801.SZ', 'name': '四川九洲', 'industry': '家用电器'}, '003029.SZ': {'code': '003029.SZ', 'name': '吉大正元', 'industry': '软件服务'}, '600888.SH': {'code': '600888.SH', 'name': '新疆众和', 'industry': '铝'}, '300129.SZ': {'code': '300129.SZ', 'name': '泰胜风能', 'industry': '电气设备'}, '002083.SZ': {'code': '002083.SZ', 'name': '孚日股份', 'industry': '纺织'}, '300470.SZ': {'code': '300470.SZ', 'name': '中密控股', 'industry': '机械基件'}, '600487.SH': {'code': '600487.SH', 'name': '亨通光电', 'industry': '通信设备'}, '002452.SZ': {'code': '002452.SZ', 'name': '长高集团', 'industry': '电气设备'}, '300047.SZ': {'code': '300047.SZ', 'name': '天源迪科', 'industry': '软件服务'}, '002818.SZ': {'code': '002818.SZ', 'name': '富森美', 'industry': '其他商业'}, '600501.SH': {'code': '600501.SH', 'name': '航天晨光', 'industry': '汽车配件'}, '002682.SZ': {'code': '002682.SZ', 'name': '龙洲股份', 'industry': '仓储物流'}, '603166.SH': {'code': '603166.SH', 'name': '福达股份', 'industry': '汽车配件'}, '000066.SZ': {'code': '000066.SZ', 'name': '中国长城', 'industry': 'IT设备'}, '000547.SZ': {'code': '000547.SZ', 'name': '航天发展', 'industry': '通信设备'}, '300397.SZ': {'code': '300397.SZ', 'name': '天和防务', 'industry': '通信设备'}, '688626.SH': {'code': '688626.SH', 'name': '翔宇医疗', 'industry': '医疗保健'}, '002465.SZ': {'code': '002465.SZ', 'name': '海格通信', 'industry': '通信设备'}, '002368.SZ': {'code': '002368.SZ', 'name': '太极股份', 'industry': '软件服务'}, '300762.SZ': {'code': '300762.SZ', 'name': '上海瀚讯', 'industry': '通信设备'}, '600523.SH': {'code': '600523.SH', 'name': '贵航股份', 'industry': '汽车配件'}, '300489.SZ': {'code': '300489.SZ', 'name': '光智科技', 'industry': '铝'}, '600990.SH': {'code': '600990.SH', 'name': '四创电子', 'industry': '通信设备'}, '688011.SH': {'code': '688011.SH', 'name': '新光光电', 'industry': '元器件'}, '688788.SH': {'code': '688788.SH', 'name': '科思科技', 'industry': '通信设备'}, '688305.SH': {'code': '688305.SH', 'name': '科德数控', 'industry': '机床制造'}, '600010.SH': {'code': '600010.SH', 'name': '包钢股份', 'industry': '普钢'}, '300019.SZ': {'code': '300019.SZ', 'name': '硅宝科技', 'industry': '化工原料'}, '603949.SH': {'code': '603949.SH', 'name': '雪龙集团', 'industry': '汽车配件'}, '002130.SZ': {'code': '002130.SZ', 'name': '沃尔核材', 'industry': '电气设备'}, '300542.SZ': {'code': '300542.SZ', 'name': '新晨科技', 'industry': '软件服务'}, '002204.SZ': {'code': '002204.SZ', 'name': '大连重工', 'industry': '专用机械'}, '002167.SZ': {'code': '002167.SZ', 'name': '东方锆业', 'industry': '小金属'}, '688511.SH': {'code': '688511.SH', 'name': '天微电子', 'industry': '元器件'}, '600391.SH': {'code': '600391.SH', 'name': '航发科技', 'industry': '航空'}, '002439.SZ': {'code': '002439.SZ', 'name': '启明星辰', 'industry': '软件服务'}, '300589.SZ': {'code': '300589.SZ', 'name': '江龙船艇', 'industry': '船舶'}, '002420.SZ': {'code': '002420.SZ', 'name': '毅昌科技', 'industry': '家用电器'}, '600400.SH': {'code': '600400.SH', 'name': '红豆股份', 'industry': '服饰'}, '002523.SZ': {'code': '002523.SZ', 'name': '天桥起重', 'industry': '工程机械'}, '300427.SZ': {'code': '300427.SZ', 'name': '红相股份', 'industry': '电气设备'}, '002342.SZ': {'code': '002342.SZ', 'name': '巨力索具', 'industry': '机械基件'}, '002801.SZ': {'code': '002801.SZ', 'name': '微光股份', 'industry': '电气设备'}, '002536.SZ': {'code': '002536.SZ', 'name': '飞龙股份', 'industry': '汽车配件'}, '300041.SZ': {'code': '300041.SZ', 'name': '回天新材', 'industry': '化工原料'}, '002471.SZ': {'code': '002471.SZ', 'name': '中超控股', 'industry': '电气设备'}, '688311.SH': {'code': '688311.SH', 'name': '盟升电子', 'industry': '元器件'}, '300159.SZ': {'code': '300159.SZ', 'name': '新研股份', 'industry': '航空'}, '600879.SH': {'code': '600879.SH', 'name': '航天电子', 'industry': '航空'}, '002540.SZ': {'code': '002540.SZ', 'name': '亚太科技', 'industry': '铝'}, '300581.SZ': {'code': '300581.SZ', 'name': '晨曦航空', 'industry': '航空'}, '688122.SH': {'code': '688122.SH', 'name': '西部超导', 'industry': '小金属'}, '600316.SH': {'code': '600316.SH', 'name': '洪都航空', 'industry': '航空'}, '600893.SH': {'code': '600893.SH', 'name': '航发动力', 'industry': '航空'}, '002406.SZ': {'code': '002406.SZ', 'name': '远东传动', 'industry': '汽车配件'}, '601677.SH': {'code': '601677.SH', 'name': '明泰铝业', 'industry': '铝'}, '603978.SH': {'code': '603978.SH', 'name': '深圳新星', 'industry': '铝'}, '688272.SH': {'code': '688272.SH', 'name': '富吉瑞', 'industry': '元器件'}, '300103.SZ': {'code': '300103.SZ', 'name': '达刚控股', 'industry': '环境保护'}, '000638.SZ': {'code': '000638.SZ', 'name': '*ST万方', 'industry': '软件服务'}, '688722.SH': {'code': '688722.SH', 'name': '同益中', 'industry': '化纤'}, '603859.SH': {'code': '603859.SH', 'name': '能科科技', 'industry': '软件服务'}, '600491.SH': {'code': '600491.SH', 'name': '龙元建设', 'industry': '建筑工程'}, '688597.SH': {'code': '688597.SH', 'name': '煜邦电力', 'industry': '电器仪表'}, '688577.SH': {'code': '688577.SH', 'name': '浙海德曼', 'industry': '机床制造'}, '600378.SH': {'code': '600378.SH', 'name': '昊华科技', 'industry': '化工原料'}, '600764.SH': {'code': '600764.SH', 'name': '中国海防', 'industry': '通信设备'}, '000768.SZ': {'code': '000768.SZ', 'name': '中航西飞', 'industry': '航空'}, '000026.SZ': {'code': '000026.SZ', 'name': '飞亚达', 'industry': '其他商业'}, '002510.SZ': {'code': '002510.SZ', 'name': '天汽模', 'industry': '汽车配件'}, '688619.SH': {'code': '688619.SH', 'name': '罗普特', 'industry': '软件服务'}, '002669.SZ': {'code': '002669.SZ', 'name': '康达新材', 'industry': '化工原料'}, '002249.SZ': {'code': '002249.SZ', 'name': '大洋电机', 'industry': '电气设备'}, '002446.SZ': {'code': '002446.SZ', 'name': '盛路通信', 'industry': '通信设备'}, '600558.SH': {'code': '600558.SH', 'name': '大西洋', 'industry': '钢加工'}, '300629.SZ': {'code': '300629.SZ', 'name': '新劲刚', 'industry': '元器件'}, '002057.SZ': {'code': '002057.SZ', 'name': '中钢天源', 'industry': '元器件'}, '603855.SH': {'code': '603855.SH', 'name': '华荣股份', 'industry': '专用机械'}, '000070.SZ': {'code': '000070.SZ', 'name': '特发信息', 'industry': '通信设备'}, '600072.SH': {'code': '600072.SH', 'name': '中船科技', 'industry': '船舶'}, '300424.SZ': {'code': '300424.SZ', 'name': '航新科技', 'industry': '航空'}, '600192.SH': {'code': '600192.SH', 'name': '长城电工', 'industry': '电气设备'}, '002108.SZ': {'code': '002108.SZ', 'name': '沧州明珠', 'industry': '塑料'}, '002297.SZ': {'code': '002297.SZ', 'name': '博云新材', 'industry': '矿物制品'}, '002771.SZ': {'code': '002771.SZ', 'name': '真视通', 'industry': '软件服务'}, '002438.SZ': {'code': '002438.SZ', 'name': '江苏神通', 'industry': '机械基件'}, '601606.SH': {'code': '601606.SH', 'name': '长城军工', 'industry': '专用机械'}, '600562.SH': {'code': '600562.SH', 'name': '国睿科技', 'industry': '通信设备'}, '002564.SZ': {'code': '002564.SZ', 'name': '天沃科技', 'industry': '建筑工程'}, '603067.SH': {'code': '603067.SH', 'name': '振华股份', 'industry': '化工原料'}, '002544.SZ': {'code': '002544.SZ', 'name': '杰赛科技', 'industry': '通信设备'}, '300491.SZ': {'code': '300491.SZ', 'name': '通合科技', 'industry': '电气设备'}, '603977.SH': {'code': '603977.SH', 'name': '国泰集团', 'industry': '化工原料'}, '001208.SZ': {'code': '001208.SZ', 'name': '华菱线缆', 'industry': '电气设备'}, '300964.SZ': {'code': '300964.SZ', 'name': '本川智能', 'industry': '元器件'}, '300337.SZ': {'code': '300337.SZ', 'name': '银邦股份', 'industry': '铝'}, '600855.SH': {'code': '600855.SH', 'name': '航天长峰', 'industry': '专用机械'}, '300965.SZ': {'code': '300965.SZ', 'name': '恒宇信通', 'industry': '航空'}, '688010.SH': {'code': '688010.SH', 'name': '福光股份', 'industry': '电器仪表'}, '300719.SZ': {'code': '300719.SZ', 'name': '安达维尔', 'industry': '航空'}, '002190.SZ': {'code': '002190.SZ', 'name': '成飞集成', 'industry': '汽车配件'}, '002265.SZ': {'code': '002265.SZ', 'name': '西仪股份', 'industry': '汽车配件'}, '300237.SZ': {'code': '300237.SZ', 'name': '美晨生态', 'industry': '建筑工程'}, '002760.SZ': {'code': '002760.SZ', 'name': '凤形股份', 'industry': '机械基件'}, '002686.SZ': {'code': '002686.SZ', 'name': '亿利达', 'industry': '专用机械'}, '002591.SZ': {'code': '002591.SZ', 'name': '恒大高新', 'industry': '化工原料'}, '301092.SZ': {'code': '301092.SZ', 'name': '争光股份', 'industry': '化工原料'}, '600602.SH': {'code': '600602.SH', 'name': '云赛智联', 'industry': '软件服务'}, '688418.SH': {'code': '688418.SH', 'name': '震有科技', 'industry': '通信设备'}, '300722.SZ': {'code': '300722.SZ', 'name': '新余国科', 'industry': '航空'}, '688685.SH': {'code': '688685.SH', 'name': '迈信林', 'industry': '航空'}, '301050.SZ': {'code': '301050.SZ', 'name': '雷电微力', 'industry': '航空'}, '301041.SZ': {'code': '301041.SZ', 'name': '金百泽', 'industry': '元器件'}, '002504.SZ': {'code': '002504.SZ', 'name': 'ST弘高', 'industry': '装修装饰'}, '002189.SZ': {'code': '002189.SZ', 'name': '中光学', 'industry': '元器件'}, '000687.SZ': {'code': '000687.SZ', 'name': '*ST华讯', 'industry': '通信设备'}, '300416.SZ': {'code': '300416.SZ', 'name': '苏试试验', 'industry': '电器仪表'}, '300297.SZ': {'code': '300297.SZ', 'name': '蓝盾股份', 'industry': '软件服务'}, '002723.SZ': {'code': '002723.SZ', 'name': '金莱特', 'industry': '家用电器'}, '000595.SZ': {'code': '000595.SZ', 'name': '宝塔实业', 'industry': '机械基件'}, '600353.SH': {'code': '600353.SH', 'name': '旭光电子', 'industry': '元器件'}, '300302.SZ': {'code': '300302.SZ', 'name': '同有科技', 'industry': '软件服务'}, '300711.SZ': {'code': '300711.SZ', 'name': '广哈通信', 'industry': '通信设备'}, '000561.SZ': {'code': '000561.SZ', 'name': '烽火电子', 'industry': '通信设备'}, '688081.SH': {'code': '688081.SH', 'name': '兴图新科', 'industry': '软件服务'}, '600150.SH': {'code': '600150.SH', 'name': '中国船舶', 'industry': '船舶'}, '300091.SZ': {'code': '300091.SZ', 'name': '金通灵', 'industry': '机械基件'}, '600456.SH': {'code': '600456.SH', 'name': '宝钛股份', 'industry': '小金属'}, '300900.SZ': {'code': '300900.SZ', 'name': '广联航空', 'industry': '航空'}, '300402.SZ': {'code': '300402.SZ', 'name': '宝色股份', 'industry': '专用机械'}, '300690.SZ': {'code': '300690.SZ', 'name': '双一科技', 'industry': '电气设备'}, '603712.SH': {'code': '603712.SH', 'name': '七一二', 'industry': '通信设备'}, '300227.SZ': {'code': '300227.SZ', 'name': '光韵达', 'industry': '元器件'}, '600303.SH': {'code': '600303.SH', 'name': '曙光股份', 'industry': '汽车整车'}, '600765.SH': {'code': '600765.SH', 'name': '中航重机', 'industry': '航空'}, '300345.SZ': {'code': '300345.SZ', 'name': '华民股份', 'industry': '机械基件'}, '603819.SH': {'code': '603819.SH', 'name': '神力股份', 'industry': '电气设备'}, '600760.SH': {'code': '600760.SH', 'name': '中航沈飞', 'industry': '航空'}, '300775.SZ': {'code': '300775.SZ', 'name': '三角防务', 'industry': '航空'}, '002783.SZ': {'code': '002783.SZ', 'name': '凯龙股份', 'industry': '化工原料'}, '000519.SZ': {'code': '000519.SZ', 'name': '中兵红箭', 'industry': '专用机械'}, '002560.SZ': {'code': '002560.SZ', 'name': '通达股份', 'industry': '电气设备'}, '300696.SZ': {'code': '300696.SZ', 'name': '爱乐达', 'industry': '航空'}, '002254.SZ': {'code': '002254.SZ', 'name': '泰和新材', 'industry': '化纤'}, '002056.SZ': {'code': '002056.SZ', 'name': '横店东磁', 'industry': '元器件'}, '300215.SZ': {'code': '300215.SZ', 'name': '电科院', 'industry': '电气设备'}, '300777.SZ': {'code': '300777.SZ', 'name': '中简科技', 'industry': '化纤'}, '601177.SH': {'code': '601177.SH', 'name': '杭齿前进', 'industry': '机械基件'}, '600592.SH': {'code': '600592.SH', 'name': '龙溪股份', 'industry': '机械基件'}, '688066.SH': {'code': '688066.SH', 'name': '航天宏图', 'industry': '软件服务'}, '600839.SH': {'code': '600839.SH', 'name': '四川长虹', 'industry': '家用电器'}, '300447.SZ': {'code': '300447.SZ', 'name': '全信股份', 'industry': '电气设备'}, '301079.SZ': {'code': '301079.SZ', 'name': '邵阳液压', 'industry': '机械基件'}, '300963.SZ': {'code': '300963.SZ', 'name': '中洲特材', 'industry': '小金属'}, '300527.SZ': {'code': '300527.SZ', 'name': '中船应急', 'industry': '专用机械'}, '002730.SZ': {'code': '002730.SZ', 'name': '电光科技', 'industry': '电气设备'}, '002871.SZ': {'code': '002871.SZ', 'name': '伟隆股份', 'industry': '机械基件'}, '002933.SZ': {'code': '002933.SZ', 'name': '新兴装备', 'industry': '航空'}, '600372.SH': {'code': '600372.SH', 'name': '中航电子', 'industry': '航空'}, '300438.SZ': {'code': '300438.SZ', 'name': '鹏辉能源', 'industry': '电气设备'}, '300324.SZ': {'code': '300324.SZ', 'name': '旋极信息', 'industry': '软件服务'}, '002179.SZ': {'code': '002179.SZ', 'name': '中航光电', 'industry': '元器件'}, '300252.SZ': {'code': '300252.SZ', 'name': '金信诺', 'industry': '通信设备'}, '002272.SZ': {'code': '002272.SZ', 'name': '川润股份', 'industry': '机械基件'}, '300265.SZ': {'code': '300265.SZ', 'name': '通光线缆', 'industry': '电气设备'}, '600580.SH': {'code': '600580.SH', 'name': '卧龙电驱', 'industry': '电气设备'}, '300560.SZ': {'code': '300560.SZ', 'name': '中富通', 'industry': '通信设备'}, '300847.SZ': {'code': '300847.SZ', 'name': '中船汉光', 'industry': '化工原料'}, '603169.SH': {'code': '603169.SH', 'name': '兰石重装', 'industry': '专用机械'}, '300862.SZ': {'code': '300862.SZ', 'name': '蓝盾光电', 'industry': '电器仪表'}, '002708.SZ': {'code': '002708.SZ', 'name': '光洋股份', 'industry': '汽车配件'}, '300352.SZ': {'code': '300352.SZ', 'name': '北信源', 'industry': '软件服务'}, '000534.SZ': {'code': '000534.SZ', 'name': '万泽股份', 'industry': '生物制药'}, '600967.SH': {'code': '600967.SH', 'name': '内蒙一机', 'industry': '运输设备'}, '300351.SZ': {'code': '300351.SZ', 'name': '永贵电器', 'industry': '运输设备'}, '600172.SH': {'code': '600172.SH', 'name': '黄河旋风', 'industry': '矿物制品'}, '300490.SZ': {'code': '300490.SZ', 'name': '华自科技', 'industry': '电气设备'}, '300471.SZ': {'code': '300471.SZ', 'name': '厚普股份', 'industry': '专用机械'}, '300036.SZ': {'code': '300036.SZ', 'name': '超图软件', 'industry': '软件服务'}, '002837.SZ': {'code': '002837.SZ', 'name': '英维克', 'industry': '专用机械'}, '600148.SH': {'code': '600148.SH', 'name': '长春一东', 'industry': '汽车配件'}, '688776.SH': {'code': '688776.SH', 'name': '国光电气', 'industry': '元器件'}, '688033.SH': {'code': '688033.SH', 'name': '天宜上佳', 'industry': '运输设备'}, '300414.SZ': {'code': '300414.SZ', 'name': '中光防雷', 'industry': '通信设备'}, '300210.SZ': {'code': '300210.SZ', 'name': '森远股份', 'industry': '专用机械'}, '002253.SZ': {'code': '002253.SZ', 'name': '川大智胜', 'industry': '软件服务'}, '300419.SZ': {'code': '300419.SZ', 'name': '浩丰科技', 'industry': '软件服务'}, '601126.SH': {'code': '601126.SH', 'name': '四方股份', 'industry': '电气设备'}, '300680.SZ': {'code': '300680.SZ', 'name': '隆盛科技', 'industry': '汽车配件'}, '600399.SH': {'code': '600399.SH', 'name': '抚顺特钢', 'industry': '特种钢'}, '300563.SZ': {'code': '300563.SZ', 'name': '神宇股份', 'industry': '通信设备'}, '002651.SZ': {'code': '002651.SZ', 'name': '利君股份', 'industry': '专用机械'}, '300067.SZ': {'code': '300067.SZ', 'name': '安诺其', 'industry': '染料涂料'}, '300971.SZ': {'code': '300971.SZ', 'name': '博亚精工', 'industry': '机械基件'}, '002182.SZ': {'code': '002182.SZ', 'name': '云海金属', 'industry': '小金属'}, '002765.SZ': {'code': '002765.SZ', 'name': '蓝黛科技', 'industry': '元器件'}, '300350.SZ': {'code': '300350.SZ', 'name': '华鹏飞', 'industry': '仓储物流'}, '002149.SZ': {'code': '002149.SZ', 'name': '西部材料', 'industry': '小金属'}, '688333.SH': {'code': '688333.SH', 'name': '铂力特', 'industry': '机械基件'}, '002096.SZ': {'code': '002096.SZ', 'name': '南岭民爆', 'industry': '化工原料'}, '600038.SH': {'code': '600038.SH', 'name': '中直股份', 'industry': '航空'}, '300593.SZ': {'code': '300593.SZ', 'name': '新雷能', 'industry': '电气设备'}, '002985.SZ': {'code': '002985.SZ', 'name': '北摩高科', 'industry': '航空'}, '000738.SZ': {'code': '000738.SZ', 'name': '航发控制', 'industry': '航空'}, '300428.SZ': {'code': '300428.SZ', 'name': '立中集团', 'industry': '汽车配件'}, '300092.SZ': {'code': '300092.SZ', 'name': '科新机电', 'industry': '专用机械'}, '605222.SH': {'code': '605222.SH', 'name': '起帆电缆', 'industry': '电气设备'}, '002298.SZ': {'code': '002298.SZ', 'name': '中电兴发', 'industry': '软件服务'}, '603516.SH': {'code': '603516.SH', 'name': '淳中科技', 'industry': '通信设备'}, '600590.SH': {'code': '600590.SH', 'name': '泰豪科技', 'industry': '电气设备'}, '300084.SZ': {'code': '300084.SZ', 'name': '海默科技', 'industry': '专用机械'}, '300817.SZ': {'code': '300817.SZ', 'name': '双飞股份', 'industry': '机械基件'}, '002231.SZ': {'code': '002231.SZ', 'name': '奥维通信', 'industry': '通信设备'}, '300065.SZ': {'code': '300065.SZ', 'name': '海兰信', 'industry': '船舶'}, '600480.SH': {'code': '600480.SH', 'name': '凌云股份', 'industry': '汽车配件'}, '300157.SZ': {'code': '300157.SZ', 'name': '恒泰艾普', 'industry': '石油开采'}, '688456.SH': {'code': '688456.SH', 'name': '有研粉材', 'industry': '铜'}, '300845.SZ': {'code': '300845.SZ', 'name': '捷安高科', 'industry': '软件服务'}, '002176.SZ': {'code': '002176.SZ', 'name': '江特电机', 'industry': '电气设备'}, '300306.SZ': {'code': '300306.SZ', 'name': '远方信息', 'industry': '电器仪表'}, '600343.SH': {'code': '600343.SH', 'name': '航天动力', 'industry': '航空'}, '300830.SZ': {'code': '300830.SZ', 'name': '金现代', 'industry': '软件服务'}, '300301.SZ': {'code': '300301.SZ', 'name': '长方集团', 'industry': '半导体'}, '300597.SZ': {'code': '300597.SZ', 'name': '吉大通信', 'industry': '通信设备'}, '300591.SZ': {'code': '300591.SZ', 'name': '万里马', 'industry': '服饰'}, '002025.SZ': {'code': '002025.SZ', 'name': '航天电器', 'industry': '元器件'}, '300626.SZ': {'code': '300626.SZ', 'name': '华瑞股份', 'industry': '电气设备'}, '002361.SZ': {'code': '002361.SZ', 'name': '神剑股份', 'industry': '化工原料'}, '300887.SZ': {'code': '300887.SZ', 'name': '谱尼测试', 'industry': '综合类'}, '300600.SZ': {'code': '300600.SZ', 'name': '国瑞科技', 'industry': '船舶'}, '600260.SH': {'code': '600260.SH', 'name': 'ST凯乐', 'industry': '通信设备'}, '002335.SZ': {'code': '002335.SZ', 'name': '科华数据', 'industry': '电气设备'}, '300213.SZ': {'code': '300213.SZ', 'name': '佳讯飞鸿', 'industry': '通信设备'}, '002013.SZ': {'code': '002013.SZ', 'name': '中航机电', 'industry': '航空'}, '300733.SZ': {'code': '300733.SZ', 'name': '西菱动力', 'industry': '汽车配件'}, '300799.SZ': {'code': '300799.SZ', 'name': '左江科技', 'industry': '软件服务'}, '300553.SZ': {'code': '300553.SZ', 'name': '集智股份', 'industry': '电器仪表'}, '600416.SH': {'code': '600416.SH', 'name': '湘电股份', 'industry': '电气设备'}, '300034.SZ': {'code': '300034.SZ', 'name': '钢研高纳', 'industry': '航空'}, '002756.SZ': {'code': '002756.SZ', 'name': '永兴材料', 'industry': '特种钢'}, '688800.SH': {'code': '688800.SH', 'name': '瑞可达', 'industry': '元器件'}, '300855.SZ': {'code': '300855.SZ', 'name': '图南股份', 'industry': '钢加工'}, '300440.SZ': {'code': '300440.SZ', 'name': '运达科技', 'industry': '软件服务'}, '000400.SZ': {'code': '000400.SZ', 'name': '许继电气', 'industry': '电气设备'}, '300311.SZ': {'code': '300311.SZ', 'name': '任子行', 'industry': '软件服务'}, '301018.SZ': {'code': '301018.SZ', 'name': '申菱环境', 'industry': '专用机械'}, '002935.SZ': {'code': '002935.SZ', 'name': '天奥电子', 'industry': '航空'}, '002411.SZ': {'code': '002411.SZ', 'name': '延安必康', 'industry': '化学制药'}, '300366.SZ': {'code': '300366.SZ', 'name': '创意信息', 'industry': '软件服务'}, '600184.SH': {'code': '600184.SH', 'name': '光电股份', 'industry': '专用机械'}, '605598.SH': {'code': '605598.SH', 'name': '上海港湾', 'industry': '建筑工程'}, '605123.SH': {'code': '605123.SH', 'name': '派克新材', 'industry': '航空'}, '601890.SH': {'code': '601890.SH', 'name': '亚星锚链', 'industry': '船舶'}, '301213.SZ': {'code': '301213.SZ', 'name': '观想科技', 'industry': '软件服务'}, '000922.SZ': {'code': '000922.SZ', 'name': '佳电股份', 'industry': '电气设备'}, '688636.SH': {'code': '688636.SH', 'name': '智明达', 'industry': '元器件'}, '000887.SZ': {'code': '000887.SZ', 'name': '中鼎股份', 'industry': '汽车配件'}, '300810.SZ': {'code': '300810.SZ', 'name': '中科海讯', 'industry': '船舶'}, '002777.SZ': {'code': '002777.SZ', 'name': '久远银海', 'industry': '软件服务'}, '600992.SH': {'code': '600992.SH', 'name': '贵绳股份', 'industry': '钢加工'}, '600862.SH': {'code': '600862.SH', 'name': '中航高科', 'industry': '航空'}, '688110.SH': {'code': '688110.SH', 'name': '东芯股份', 'industry': '半导体'}, '000581.SZ': {'code': '000581.SZ', 'name': '威孚高科', 'industry': '汽车配件'}, '688601.SH': {'code': '688601.SH', 'name': '力芯微', 'industry': '半导体'}, '688262.SH': {'code': '688262.SH', 'name': '国芯科技', 'industry': '半导体'}, '688655.SH': {'code': '688655.SH', 'name': '迅捷兴', 'industry': '元器件'}, '301099.SZ': {'code': '301099.SZ', 'name': '雅创电子', 'industry': '批发业'}, '002475.SZ': {'code': '002475.SZ', 'name': '立讯精密', 'industry': '元器件'}, '002962.SZ': {'code': '002962.SZ', 'name': '五方光电', 'industry': '元器件'}, '002217.SZ': {'code': '002217.SZ', 'name': '合力泰', 'industry': '元器件'}, '002138.SZ': {'code': '002138.SZ', 'name': '顺络电子', 'industry': '元器件'}, '300285.SZ': {'code': '300285.SZ', 'name': '国瓷材料', 'industry': '陶瓷'}, '002859.SZ': {'code': '002859.SZ', 'name': '洁美科技', 'industry': '元器件'}, '300975.SZ': {'code': '300975.SZ', 'name': '商络电子', 'industry': '商贸代理'}, '300408.SZ': {'code': '300408.SZ', 'name': '三环集团', 'industry': '元器件'}, '300319.SZ': {'code': '300319.SZ', 'name': '麦捷科技', 'industry': '元器件'}, '000532.SZ': {'code': '000532.SZ', 'name': '华金资本', 'industry': '多元金融'}, '300811.SZ': {'code': '300811.SZ', 'name': '铂科新材', 'industry': '元器件'}, '600237.SH': {'code': '600237.SH', 'name': '铜峰电子', 'industry': '元器件'}, '002922.SZ': {'code': '002922.SZ', 'name': '伊戈尔', 'industry': '电气设备'}, '002199.SZ': {'code': '002199.SZ', 'name': '东晶电子', 'industry': '元器件'}, '300594.SZ': {'code': '300594.SZ', 'name': '朗进科技', 'industry': '运输设备'}, '300506.SZ': {'code': '300506.SZ', 'name': '名家汇', 'industry': '建筑工程'}, '601616.SH': {'code': '601616.SH', 'name': '广电电气', 'industry': '电气设备'}, '603212.SH': {'code': '603212.SH', 'name': '赛伍技术', 'industry': '塑料'}, '300588.SZ': {'code': '300588.SZ', 'name': '熙菱信息', 'industry': '软件服务'}, '300561.SZ': {'code': '300561.SZ', 'name': '汇金科技', 'industry': '软件服务'}, '002657.SZ': {'code': '002657.SZ', 'name': '中科金财', 'industry': '软件服务'}, '002987.SZ': {'code': '002987.SZ', 'name': '京北方', 'industry': '软件服务'}, '600756.SH': {'code': '600756.SH', 'name': '浪潮软件', 'industry': '软件服务'}, '002153.SZ': {'code': '002153.SZ', 'name': '石基信息', 'industry': '软件服务'}, '002453.SZ': {'code': '002453.SZ', 'name': '华软科技', 'industry': '软件服务'}, '300368.SZ': {'code': '300368.SZ', 'name': '汇金股份', 'industry': 'IT设备'}, '600734.SH': {'code': '600734.SH', 'name': '*ST实达', 'industry': 'IT设备'}, '688023.SH': {'code': '688023.SH', 'name': '安恒信息', 'industry': '软件服务'}, '300033.SZ': {'code': '300033.SZ', 'name': '同花顺', 'industry': '软件服务'}, '688777.SH': {'code': '688777.SH', 'name': '中控技术', 'industry': '软件服务'}, '688039.SH': {'code': '688039.SH', 'name': '当虹科技', 'industry': '软件服务'}, '600446.SH': {'code': '600446.SH', 'name': '金证股份', 'industry': '软件服务'}, '300551.SZ': {'code': '300551.SZ', 'name': '古鳌科技', 'industry': 'IT设备'}, '600654.SH': {'code': '600654.SH', 'name': 'ST中安', 'industry': '软件服务'}, '000977.SZ': {'code': '000977.SZ', 'name': '浪潮信息', 'industry': 'IT设备'}, '688111.SH': {'code': '688111.SH', 'name': '金山办公', 'industry': '软件服务'}, '688618.SH': {'code': '688618.SH', 'name': '三旺通信', 'industry': '通信设备'}, '300682.SZ': {'code': '300682.SZ', 'name': '朗新科技', 'industry': '软件服务'}, '603383.SH': {'code': '603383.SH', 'name': '顶点软件', 'industry': '软件服务'}, '002925.SZ': {'code': '002925.SZ', 'name': '盈趣科技', 'industry': '元器件'}, '002052.SZ': {'code': '002052.SZ', 'name': 'ST同洲', 'industry': '家用电器'}, '688369.SH': {'code': '688369.SH', 'name': '致远互联', 'industry': '软件服务'}, '600570.SH': {'code': '600570.SH', 'name': '恒生电子', 'industry': '软件服务'}, '688078.SH': {'code': '688078.SH', 'name': '龙软科技', 'industry': '软件服务'}, '002410.SZ': {'code': '002410.SZ', 'name': '广联达', 'industry': '软件服务'}, '600588.SH': {'code': '600588.SH', 'name': '用友网络', 'industry': '软件服务'}, '688188.SH': {'code': '688188.SH', 'name': '柏楚电子', 'industry': '软件服务'}, '688095.SH': {'code': '688095.SH', 'name': '福昕软件', 'industry': '软件服务'}, '600589.SH': {'code': '600589.SH', 'name': 'ST榕泰', 'industry': '塑料'}, '000158.SZ': {'code': '000158.SZ', 'name': '常山北明', 'industry': '软件服务'}, '300674.SZ': {'code': '300674.SZ', 'name': '宇信科技', 'industry': '软件服务'}, '600797.SH': {'code': '600797.SH', 'name': '浙大网新', 'industry': '软件服务'}, '688559.SH': {'code': '688559.SH', 'name': '海目星', 'industry': '专用机械'}, '600536.SH': {'code': '600536.SH', 'name': '中国软件', 'industry': '软件服务'}, '603927.SH': {'code': '603927.SH', 'name': '中科软', 'industry': '软件服务'}, '000555.SZ': {'code': '000555.SZ', 'name': '神州信息', 'industry': '软件服务'}, '603039.SH': {'code': '603039.SH', 'name': '泛微网络', 'industry': '软件服务'}, '002912.SZ': {'code': '002912.SZ', 'name': '中新赛克', 'industry': '软件服务'}, '688109.SH': {'code': '688109.SH', 'name': '品茗股份', 'industry': '软件服务'}, '300380.SZ': {'code': '300380.SZ', 'name': '安硕信息', 'industry': '软件服务'}, '688168.SH': {'code': '688168.SH', 'name': '安博通', 'industry': '软件服务'}, '300205.SZ': {'code': '300205.SZ', 'name': '天喻信息', 'industry': '通信设备'}, '300348.SZ': {'code': '300348.SZ', 'name': '长亮科技', 'industry': '软件服务'}, '688030.SH': {'code': '688030.SH', 'name': '山石网科', 'industry': '软件服务'}, '300935.SZ': {'code': '300935.SZ', 'name': '盈建科', 'industry': '软件服务'}, '600131.SH': {'code': '600131.SH', 'name': '国网信通', 'industry': '通信设备'}, '603660.SH': {'code': '603660.SH', 'name': '苏州科达', 'industry': '通信设备'}, '688118.SH': {'code': '688118.SH', 'name': '普元信息', 'industry': '软件服务'}, '002819.SZ': {'code': '002819.SZ', 'name': '东方中科', 'industry': '电器仪表'}, '600624.SH': {'code': '600624.SH', 'name': '复旦复华', 'industry': '化学制药'}, '300996.SZ': {'code': '300996.SZ', 'name': '普联软件', 'industry': '软件服务'}, '300290.SZ': {'code': '300290.SZ', 'name': '荣科科技', 'industry': '软件服务'}, '002622.SZ': {'code': '002622.SZ', 'name': '融钰集团', 'industry': '电气设备'}, '300525.SZ': {'code': '300525.SZ', 'name': '博思软件', 'industry': '软件服务'}, '300803.SZ': {'code': '300803.SZ', 'name': '指南针', 'industry': '软件服务'}, '300078.SZ': {'code': '300078.SZ', 'name': '思创医惠', 'industry': '软件服务'}, '300851.SZ': {'code': '300851.SZ', 'name': '交大思诺', 'industry': '运输设备'}, '002474.SZ': {'code': '002474.SZ', 'name': '榕基软件', 'industry': '软件服务'}, '600845.SH': {'code': '600845.SH', 'name': '宝信软件', 'industry': '软件服务'}, '002869.SZ': {'code': '002869.SZ', 'name': '金溢科技', 'industry': '通信设备'}, '300469.SZ': {'code': '300469.SZ', 'name': '信息发展', 'industry': '软件服务'}, '688038.SH': {'code': '688038.SH', 'name': '中科通达', 'industry': '软件服务'}, '688365.SH': {'code': '688365.SH', 'name': '光云科技', 'industry': '软件服务'}, '603106.SH': {'code': '603106.SH', 'name': '恒银科技', 'industry': 'IT设备'}, '300448.SZ': {'code': '300448.SZ', 'name': '浩云科技', 'industry': '软件服务'}, '603990.SH': {'code': '603990.SH', 'name': '麦迪科技', 'industry': '软件服务'}, '688083.SH': {'code': '688083.SH', 'name': '中望软件', 'industry': '软件服务'}, '688232.SH': {'code': '688232.SH', 'name': '新点软件', 'industry': '软件服务'}, '600455.SH': {'code': '600455.SH', 'name': '博通股份', 'industry': '文教休闲'}, '003007.SZ': {'code': '003007.SZ', 'name': '直真科技', 'industry': '软件服务'}, '300168.SZ': {'code': '300168.SZ', 'name': '万达信息', 'industry': '软件服务'}, '300271.SZ': {'code': '300271.SZ', 'name': '华宇软件', 'industry': '软件服务'}, '688318.SH': {'code': '688318.SH', 'name': '财富趋势', 'industry': '软件服务'}, '300085.SZ': {'code': '300085.SZ', 'name': '银之杰', 'industry': '软件服务'}, '605398.SH': {'code': '605398.SH', 'name': '新炬网络', 'industry': '软件服务'}, '300557.SZ': {'code': '300557.SZ', 'name': '理工光科', 'industry': '电器仪表'}, '603636.SH': {'code': '603636.SH', 'name': '南威软件', 'industry': '软件服务'}, '301001.SZ': {'code': '301001.SZ', 'name': '凯淳股份', 'industry': '互联网'}, '300378.SZ': {'code': '300378.SZ', 'name': '鼎捷软件', 'industry': '软件服务'}, '300369.SZ': {'code': '300369.SZ', 'name': '绿盟科技', 'industry': '软件服务'}, '300559.SZ': {'code': '300559.SZ', 'name': '佳发教育', 'industry': '软件服务'}, '603496.SH': {'code': '603496.SH', 'name': '恒为科技', 'industry': 'IT设备'}, '300365.SZ': {'code': '300365.SZ', 'name': '恒华科技', 'industry': '软件服务'}, '300253.SZ': {'code': '300253.SZ', 'name': '卫宁健康', 'industry': '软件服务'}, '603232.SH': {'code': '603232.SH', 'name': '格尔软件', 'industry': '软件服务'}, '688060.SH': {'code': '688060.SH', 'name': '云涌科技', 'industry': '软件服务'}, '300451.SZ': {'code': '300451.SZ', 'name': '创业慧康', 'industry': '软件服务'}, '688004.SH': {'code': '688004.SH', 'name': '博汇科技', 'industry': '软件服务'}, '688579.SH': {'code': '688579.SH', 'name': '山大地纬', 'industry': '软件服务'}, '301178.SZ': {'code': '301178.SZ', 'name': '天亿马', 'industry': '软件服务'}, '300523.SZ': {'code': '300523.SZ', 'name': '辰安科技', 'industry': '软件服务'}, '002195.SZ': {'code': '002195.SZ', 'name': '二三四五', 'industry': '软件服务'}, '300925.SZ': {'code': '300925.SZ', 'name': '法本信息', 'industry': '软件服务'}, '300687.SZ': {'code': '300687.SZ', 'name': '赛意信息', 'industry': '软件服务'}, '002279.SZ': {'code': '002279.SZ', 'name': '久其软件', 'industry': '软件服务'}, '300513.SZ': {'code': '300513.SZ', 'name': '恒实科技', 'industry': '软件服务'}, '300096.SZ': {'code': '300096.SZ', 'name': '易联众', 'industry': '软件服务'}, '300377.SZ': {'code': '300377.SZ', 'name': '赢时胜', 'industry': '软件服务'}, '300579.SZ': {'code': '300579.SZ', 'name': '数字认证', 'industry': '软件服务'}, '300330.SZ': {'code': '300330.SZ', 'name': '华虹计通', 'industry': '软件服务'}, '300465.SZ': {'code': '300465.SZ', 'name': '高伟达', 'industry': '软件服务'}, '300624.SZ': {'code': '300624.SZ', 'name': '万兴科技', 'industry': '软件服务'}, '301185.SZ': {'code': '301185.SZ', 'name': '鸥玛软件', 'industry': '软件服务'}, '600601.SH': {'code': '600601.SH', 'name': 'ST方科', 'industry': 'IT设备'}, '600476.SH': {'code': '600476.SH', 'name': '湘邮科技', 'industry': '软件服务'}, '002995.SZ': {'code': '002995.SZ', 'name': '天地在线', 'industry': '互联网'}, '300872.SZ': {'code': '300872.SZ', 'name': '天阳科技', 'industry': '软件服务'}, '688258.SH': {'code': '688258.SH', 'name': '卓易信息', 'industry': '软件服务'}, '300182.SZ': {'code': '300182.SZ', 'name': '捷成股份', 'industry': '影视音像'}, '688555.SH': {'code': '688555.SH', 'name': '泽达易盛', 'industry': '软件服务'}, '300468.SZ': {'code': '300468.SZ', 'name': '四方精创', 'industry': '软件服务'}, '301006.SZ': {'code': '301006.SZ', 'name': '迈拓股份', 'industry': '电器仪表'}, '688058.SH': {'code': '688058.SH', 'name': '宝兰德', 'industry': '软件服务'}, '300170.SZ': {'code': '300170.SZ', 'name': '汉得信息', 'industry': '软件服务'}, '300605.SZ': {'code': '300605.SZ', 'name': '恒锋信息', 'industry': '软件服务'}, '300608.SZ': {'code': '300608.SZ', 'name': '思特奇', 'industry': '软件服务'}, '600355.SH': {'code': '600355.SH', 'name': '精伦电子', 'industry': '元器件'}, '600571.SH': {'code': '600571.SH', 'name': '信雅达', 'industry': '软件服务'}, '300344.SZ': {'code': '300344.SZ', 'name': '立方数科', 'industry': '软件服务'}, '300645.SZ': {'code': '300645.SZ', 'name': '正元智慧', 'industry': '软件服务'}, '300166.SZ': {'code': '300166.SZ', 'name': '东方国信', 'industry': '软件服务'}, '300541.SZ': {'code': '300541.SZ', 'name': '先进数通', 'industry': '软件服务'}, '300245.SZ': {'code': '300245.SZ', 'name': '天玑科技', 'industry': '软件服务'}, '300386.SZ': {'code': '300386.SZ', 'name': '飞天诚信', 'industry': '软件服务'}, '002280.SZ': {'code': '002280.SZ', 'name': '联络互动', 'industry': '软件服务'}, '300235.SZ': {'code': '300235.SZ', 'name': '方直科技', 'industry': '软件服务'}, '002417.SZ': {'code': '002417.SZ', 'name': '深南股份', 'industry': '软件服务'}, '301085.SZ': {'code': '301085.SZ', 'name': '亚康股份', 'industry': '软件服务'}, '603189.SH': {'code': '603189.SH', 'name': '网达软件', 'industry': '软件服务'}, '601929.SH': {'code': '601929.SH', 'name': '吉视传媒', 'industry': '影视音像'}, '002916.SZ': {'code': '002916.SZ', 'name': '深南电路', 'industry': '元器件'}, '688533.SH': {'code': '688533.SH', 'name': '上声电子', 'industry': '汽车配件'}, '688049.SH': {'code': '688049.SH', 'name': '炬芯科技-U', 'industry': '半导体'}, '000651.SZ': {'code': '000651.SZ', 'name': '格力电器', 'industry': '家用电器'}, '688536.SH': {'code': '688536.SH', 'name': '思瑞浦', 'industry': '半导体'}, '002241.SZ': {'code': '002241.SZ', 'name': '歌尔股份', 'industry': '元器件'}, '688766.SH': {'code': '688766.SH', 'name': '普冉股份', 'industry': '半导体'}, '000063.SZ': {'code': '000063.SZ', 'name': '中兴通讯', 'industry': '通信设备'}, '300571.SZ': {'code': '300571.SZ', 'name': '平治信息', 'industry': '互联网'}, '688008.SH': {'code': '688008.SH', 'name': '澜起科技', 'industry': '半导体'}, '600651.SH': {'code': '600651.SH', 'name': '飞乐音响', 'industry': '电器仪表'}, '688001.SH': {'code': '688001.SH', 'name': '华兴源创', 'industry': '专用机械'}, '000803.SZ': {'code': '000803.SZ', 'name': '北清环能', 'industry': '环境保护'}, '688055.SH': {'code': '688055.SH', 'name': '龙腾光电', 'industry': '元器件'}, '600329.SH': {'code': '600329.SH', 'name': '中新药业', 'industry': '中成药'}, '603019.SH': {'code': '603019.SH', 'name': '中科曙光', 'industry': 'IT设备'}, '002236.SZ': {'code': '002236.SZ', 'name': '大华股份', 'industry': '电器仪表'}, '600060.SH': {'code': '600060.SH', 'name': '海信视像', 'industry': '家用电器'}, '688259.SH': {'code': '688259.SH', 'name': '创耀科技', 'industry': '半导体'}, '688608.SH': {'code': '688608.SH', 'name': '恒玄科技', 'industry': '半导体'}, '002618.SZ': {'code': '002618.SZ', 'name': '*ST丹邦', 'industry': '元器件'}, '600525.SH': {'code': '600525.SH', 'name': '长园集团', 'industry': '电气设备'}, '603893.SH': {'code': '603893.SH', 'name': '瑞芯微', 'industry': '半导体'}, '600498.SH': {'code': '600498.SH', 'name': '烽火通信', 'industry': '通信设备'}, '603803.SH': {'code': '603803.SH', 'name': '瑞斯康达', 'industry': '通信设备'}, '600820.SH': {'code': '600820.SH', 'name': '隧道股份', 'industry': '建筑工程'}, '002281.SZ': {'code': '002281.SZ', 'name': '光迅科技', 'industry': '通信设备'}, '688595.SH': {'code': '688595.SH', 'name': '芯海科技', 'industry': '半导体'}, '002851.SZ': {'code': '002851.SZ', 'name': '麦格米特', 'industry': '电气设备'}, '600834.SH': {'code': '600834.SH', 'name': '申通地铁', 'industry': '公共交通'}, '002245.SZ': {'code': '002245.SZ', 'name': '蔚蓝锂芯', 'industry': '电气设备'}, '300370.SZ': {'code': '300370.SZ', 'name': 'ST安控', 'industry': '电器仪表'}, '300866.SZ': {'code': '300866.SZ', 'name': '安克创新', 'industry': '元器件'}, '688508.SH': {'code': '688508.SH', 'name': '芯朋微', 'industry': '半导体'}, '300570.SZ': {'code': '300570.SZ', 'name': '太辰光', 'industry': '元器件'}, '688798.SH': {'code': '688798.SH', 'name': '艾为电子', 'industry': '半导体'}, '300211.SZ': {'code': '300211.SZ', 'name': '亿通科技', 'industry': '通信设备'}, '688123.SH': {'code': '688123.SH', 'name': '聚辰股份', 'industry': '半导体'}, '688699.SH': {'code': '688699.SH', 'name': '明微电子', 'industry': '半导体'}, '688368.SH': {'code': '688368.SH', 'name': '晶丰明源', 'industry': '半导体'}, '300349.SZ': {'code': '300349.SZ', 'name': '金卡智能', 'industry': '电器仪表'}, '002191.SZ': {'code': '002191.SZ', 'name': '劲嘉股份', 'industry': '广告包装'}, '300548.SZ': {'code': '300548.SZ', 'name': '博创科技', 'industry': '元器件'}, '002328.SZ': {'code': '002328.SZ', 'name': '新朋股份', 'industry': '汽车配件'}, '002542.SZ': {'code': '002542.SZ', 'name': '中化岩土', 'industry': '建筑工程'}, '002963.SZ': {'code': '002963.SZ', 'name': '豪尔赛', 'industry': '装修装饰'}, '002344.SZ': {'code': '002344.SZ', 'name': '海宁皮城', 'industry': '商品城'}, '603985.SH': {'code': '603985.SH', 'name': '恒润股份', 'industry': '机械基件'}, '300660.SZ': {'code': '300660.SZ', 'name': '江苏雷利', 'industry': '电气设备'}, '300536.SZ': {'code': '300536.SZ', 'name': '农尚环境', 'industry': '建筑工程'}, '300739.SZ': {'code': '300739.SZ', 'name': '明阳电路', 'industry': '元器件'}, '002553.SZ': {'code': '002553.SZ', 'name': '南方轴承', 'industry': '汽车配件'}, '300005.SZ': {'code': '300005.SZ', 'name': '探路者', 'industry': '服饰'}, '300824.SZ': {'code': '300824.SZ', 'name': '北鼎股份', 'industry': '家用电器'}, '605365.SH': {'code': '605365.SH', 'name': '立达信', 'industry': '家用电器'}, '002213.SZ': {'code': '002213.SZ', 'name': '大为股份', 'industry': '汽车配件'}, '000672.SZ': {'code': '000672.SZ', 'name': '上峰水泥', 'industry': '水泥'}, '002137.SZ': {'code': '002137.SZ', 'name': '实益达', 'industry': '通信设备'}, '603421.SH': {'code': '603421.SH', 'name': '鼎信通讯', 'industry': '通信设备'}, '605117.SH': {'code': '605117.SH', 'name': '德业股份', 'industry': '家用电器'}, '300120.SZ': {'code': '300120.SZ', 'name': '经纬辉开', 'industry': '元器件'}, '603519.SH': {'code': '603519.SH', 'name': '立霸股份', 'industry': '家用电器'}, '688385.SH': {'code': '688385.SH', 'name': '复旦微电', 'industry': '半导体'}, '300101.SZ': {'code': '300101.SZ', 'name': '振芯科技', 'industry': '通信设备'}, '688018.SH': {'code': '688018.SH', 'name': '乐鑫科技', 'industry': '半导体'}, '688138.SH': {'code': '688138.SH', 'name': '清溢光电', 'industry': '元器件'}, '300562.SZ': {'code': '300562.SZ', 'name': '乐心医疗', 'industry': '医疗保健'}, '300079.SZ': {'code': '300079.SZ', 'name': '数码视讯', 'industry': '通信设备'}, '600105.SH': {'code': '600105.SH', 'name': '永鼎股份', 'industry': '通信设备'}, '300392.SZ': {'code': '300392.SZ', 'name': '腾信股份', 'industry': '互联网'}, '300590.SZ': {'code': '300590.SZ', 'name': '移为通信', 'industry': '通信设备'}, '300042.SZ': {'code': '300042.SZ', 'name': '朗科科技', 'industry': 'IT设备'}, '002148.SZ': {'code': '002148.SZ', 'name': '北纬科技', 'industry': '互联网'}, '603322.SH': {'code': '603322.SH', 'name': '超讯通信', 'industry': '通信设备'}, '300531.SZ': {'code': '300531.SZ', 'name': '优博讯', 'industry': '软件服务'}, '688313.SH': {'code': '688313.SH', 'name': '仕佳光子', 'industry': '通信设备'}, '300514.SZ': {'code': '300514.SZ', 'name': '友讯达', 'industry': '电器仪表'}, '688135.SH': {'code': '688135.SH', 'name': '利扬芯片', 'industry': '半导体'}, '002201.SZ': {'code': '002201.SZ', 'name': '正威新材', 'industry': '玻璃'}, '688589.SH': {'code': '688589.SH', 'name': '力合微', 'industry': '半导体'}, '002960.SZ': {'code': '002960.SZ', 'name': '青鸟消防', 'industry': '专用机械'}, '688100.SH': {'code': '688100.SH', 'name': '威胜信息', 'industry': '通信设备'}, '000056.SZ': {'code': '000056.SZ', 'name': '皇庭国际', 'industry': '房产服务'}, '300333.SZ': {'code': '300333.SZ', 'name': '兆日科技', 'industry': '软件服务'}, '300121.SZ': {'code': '300121.SZ', 'name': '阳谷华泰', 'industry': '化工原料'}, '002027.SZ': {'code': '002027.SZ', 'name': '分众传媒', 'industry': '影视音像'}, '300144.SZ': {'code': '300144.SZ', 'name': '宋城演艺', 'industry': '旅游景点'}, '002735.SZ': {'code': '002735.SZ', 'name': '王子新材', 'industry': '塑料'}, '600289.SH': {'code': '600289.SH', 'name': 'ST信通', 'industry': '软件服务'}, '300038.SZ': {'code': '300038.SZ', 'name': '*ST数知', 'industry': '互联网'}, '300312.SZ': {'code': '300312.SZ', 'name': '*ST邦讯', 'industry': '通信设备'}, '000008.SZ': {'code': '000008.SZ', 'name': '神州高铁', 'industry': '运输设备'}, '603533.SH': {'code': '603533.SH', 'name': '掌阅科技', 'industry': '互联网'}, '000829.SZ': {'code': '000829.SZ', 'name': '天音控股', 'industry': '其他商业'}, '002619.SZ': {'code': '002619.SZ', 'name': '*ST艾格', 'industry': '互联网'}, '300632.SZ': {'code': '300632.SZ', 'name': '光莆股份', 'industry': '半导体'}, '603610.SH': {'code': '603610.SH', 'name': '麒盛科技', 'industry': '家居用品'}, '688665.SH': {'code': '688665.SH', 'name': '四方光电', 'industry': '电器仪表'}, '603662.SH': {'code': '603662.SH', 'name': '柯力传感', 'industry': '电器仪表'}, '300286.SZ': {'code': '300286.SZ', 'name': '安科瑞', 'industry': '电器仪表'}, '301008.SZ': {'code': '301008.SZ', 'name': '宏昌科技', 'industry': '家用电器'}, '688051.SH': {'code': '688051.SH', 'name': '佳华科技', 'industry': '软件服务'}, '300897.SZ': {'code': '300897.SZ', 'name': '山科智能', 'industry': '电器仪表'}, '688296.SH': {'code': '688296.SH', 'name': '和达科技', 'industry': '软件服务'}, '603158.SH': {'code': '603158.SH', 'name': '腾龙股份', 'industry': '汽车配件'}, '603121.SH': {'code': '603121.SH', 'name': '华培动力', 'industry': '汽车配件'}, '300889.SZ': {'code': '300889.SZ', 'name': '爱克股份', 'industry': '电气设备'}, '300417.SZ': {'code': '300417.SZ', 'name': '南华仪器', 'industry': '电器仪表'}, '300259.SZ': {'code': '300259.SZ', 'name': '新天科技', 'industry': '电器仪表'}, '300701.SZ': {'code': '300701.SZ', 'name': '森霸传感', 'industry': '元器件'}, '603286.SH': {'code': '603286.SH', 'name': '日盈电子', 'industry': '汽车配件'}, '000665.SZ': {'code': '000665.SZ', 'name': '湖北广电', 'industry': '影视音像'}, '603138.SH': {'code': '603138.SH', 'name': '海量数据', 'industry': '软件服务'}, '002316.SZ': {'code': '002316.SZ', 'name': '亚联发展', 'industry': '软件服务'}, '600996.SH': {'code': '600996.SH', 'name': '贵广网络', 'industry': '影视音像'}, '300603.SZ': {'code': '300603.SZ', 'name': '立昂技术', 'industry': '通信设备'}, '603887.SH': {'code': '603887.SH', 'name': '城地香江', 'industry': '软件服务'}, '688509.SH': {'code': '688509.SH', 'name': '正元地信', 'industry': '软件服务'}, '603056.SH': {'code': '603056.SH', 'name': '德邦股份', 'industry': '仓储物流'}, '603881.SH': {'code': '603881.SH', 'name': '数据港', 'industry': '电信运营'}, '002238.SZ': {'code': '002238.SZ', 'name': '天威视讯', 'industry': '影视音像'}, '000034.SZ': {'code': '000034.SZ', 'name': '神州数码', 'industry': '综合类'}, '600126.SH': {'code': '600126.SH', 'name': '杭钢股份', 'industry': '普钢'}, '300274.SZ': {'code': '300274.SZ', 'name': '阳光电源', 'industry': '电气设备'}, '600936.SH': {'code': '600936.SH', 'name': '广西广电', 'industry': '影视音像'}, '688390.SH': {'code': '688390.SH', 'name': '固德威', 'industry': '电气设备'}, '002396.SZ': {'code': '002396.SZ', 'name': '星网锐捷', 'industry': '通信设备'}, '601728.SH': {'code': '601728.SH', 'name': '中国电信', 'industry': '电信运营'}, '002340.SZ': {'code': '002340.SZ', 'name': '格林美', 'industry': '小金属'}, '688158.SH': {'code': '688158.SH', 'name': '优刻得-W', 'industry': '互联网'}, '300059.SZ': {'code': '300059.SZ', 'name': '东方财富', 'industry': '证券'}, '600941.SH': {'code': '600941.SH', 'name': '中国移动', 'industry': '电信运营'}, '300738.SZ': {'code': '300738.SZ', 'name': '奥飞数据', 'industry': '电信运营'}, '300383.SZ': {'code': '300383.SZ', 'name': '光环新网', 'industry': '电信运营'}, '002301.SZ': {'code': '002301.SZ', 'name': '齐心集团', 'industry': '文教休闲'}, '002757.SZ': {'code': '002757.SZ', 'name': '南兴股份', 'industry': '专用机械'}, '688588.SH': {'code': '688588.SH', 'name': '凌志软件', 'industry': '软件服务'}, '600225.SH': {'code': '600225.SH', 'name': '*ST松江', 'industry': '区域地产'}, '002984.SZ': {'code': '002984.SZ', 'name': '森麒麟', 'industry': '汽车配件'}, '000971.SZ': {'code': '000971.SZ', 'name': 'ST高升', 'industry': '互联网'}, '600751.SH': {'code': '600751.SH', 'name': '海航科技', 'industry': '商贸代理'}, '000851.SZ': {'code': '000851.SZ', 'name': '高鸿股份', 'industry': '通信设备'}, '300454.SZ': {'code': '300454.SZ', 'name': '深信服', 'industry': '软件服务'}, '300895.SZ': {'code': '300895.SZ', 'name': '铜牛信息', 'industry': '软件服务'}, '002400.SZ': {'code': '002400.SZ', 'name': '省广集团', 'industry': '广告包装'}, '601789.SH': {'code': '601789.SH', 'name': '宁波建工', 'industry': '建筑工程'}, '002315.SZ': {'code': '002315.SZ', 'name': '焦点科技', 'industry': '互联网'}, '688316.SH': {'code': '688316.SH', 'name': '青云科技-U', 'industry': '软件服务'}, '300768.SZ': {'code': '300768.SZ', 'name': '迪普科技', 'industry': '软件服务'}, '002929.SZ': {'code': '002929.SZ', 'name': '润建股份', 'industry': '通信设备'}, '300212.SZ': {'code': '300212.SZ', 'name': '易华录', 'industry': '软件服务'}, '300578.SZ': {'code': '300578.SZ', 'name': '会畅通讯', 'industry': '通信设备'}, '002546.SZ': {'code': '002546.SZ', 'name': '新联电子', 'industry': '电气设备'}, '300017.SZ': {'code': '300017.SZ', 'name': '网宿科技', 'industry': '电信运营'}, '002093.SZ': {'code': '002093.SZ', 'name': '国脉科技', 'industry': '电信运营'}, '002822.SZ': {'code': '002822.SZ', 'name': '中装建设', 'industry': '装修装饰'}, '002197.SZ': {'code': '002197.SZ', 'name': '证通电子', 'industry': '电器仪表'}, '603003.SH': {'code': '603003.SH', 'name': '龙宇燃油', 'industry': '石油贸易'}, '002123.SZ': {'code': '002123.SZ', 'name': '梦网科技', 'industry': '互联网'}, '688228.SH': {'code': '688228.SH', 'name': '开普云', 'industry': '互联网'}, '300175.SZ': {'code': '300175.SZ', 'name': '朗源股份', 'industry': '食品'}, '600831.SH': {'code': '600831.SH', 'name': '广电网络', 'industry': '影视音像'}, '002649.SZ': {'code': '002649.SZ', 'name': '博彦科技', 'industry': '软件服务'}, '002467.SZ': {'code': '002467.SZ', 'name': '二六三', 'industry': '电信运营'}, '000815.SZ': {'code': '000815.SZ', 'name': '美利云', 'industry': '造纸'}, '002955.SZ': {'code': '002955.SZ', 'name': '鸿合科技', 'industry': 'IT设备'}, '002642.SZ': {'code': '002642.SZ', 'name': '荣联科技', 'industry': '软件服务'}, '300921.SZ': {'code': '300921.SZ', 'name': '南凌科技', 'industry': '互联网'}, '600869.SH': {'code': '600869.SH', 'name': '远东股份', 'industry': '电气设备'}, '300231.SZ': {'code': '300231.SZ', 'name': '银信科技', 'industry': '软件服务'}, '300248.SZ': {'code': '300248.SZ', 'name': '新开普', 'industry': '软件服务'}, '300870.SZ': {'code': '300870.SZ', 'name': '欧陆通', 'industry': '元器件'}, '600481.SH': {'code': '600481.SH', 'name': '双良节能', 'industry': '机械基件'}, '002993.SZ': {'code': '002993.SZ', 'name': '奥海科技', 'industry': '元器件'}, '300232.SZ': {'code': '300232.SZ', 'name': '洲明科技', 'industry': '半导体'}, '600509.SH': {'code': '600509.SH', 'name': '天富能源', 'industry': '火力发电'}, '300745.SZ': {'code': '300745.SZ', 'name': '欣锐科技', 'industry': '汽车配件'}, '688187.SH': {'code': '688187.SH', 'name': '时代电气', 'industry': '运输设备'}, '688556.SH': {'code': '688556.SH', 'name': '高测股份', 'industry': '专用机械'}, '000576.SZ': {'code': '000576.SZ', 'name': '甘化科工', 'industry': '食品'}}

