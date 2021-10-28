# encoding: utf-8
# 股票异常情况监控
import logging
from datetime import date, timedelta
import requests, json, time
from RPS.stock_pool import NEW_STOCK_LIST
from RPS.quantitative_screening import institutions_holding_rps_stock, biggest_decline_calc


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


def get_industry_by_code(code):
    assert '.SZ' not in str(code) or '.SH' not in str(code)
    assert str(code)[0] in ('0', '3', '6')
    code = f"{code}.SH" if str(code).startswith('6') else f"{code}.SZ"
    return NEW_STOCK_LIST[code]['industry']


def TRI(high, low, close):
    return round(max(high-low, abs(high-close), abs(low-close)), 3)


def ATR(kline: list):
    for i in range(len(kline)):
        kline[i]['TRI'] = TRI(high=kline[i]['high'], low=kline[i]['low'], close=kline[i]['last_close'])
    kline = EMA_V2(EMA_V2(kline, days=10, key='TRI', out_key='ATR_10'), days=20, key='TRI', out_key='ATR_20')
    return kline


def Compact_Structure(kline: list):
    # 根据方差值判断个股结构紧凑程度
    N = 20
    for i in range(len(kline)):
        if i > 0:
            kline[i]['v'] = kline[i]['close']/kline[i-1]['close']-1
        if i > N:
            tmp = []
            for j in range(i, i-N, -1):
                tmp.append(kline[j]['v'])
            kline[i]['variance'] = round(variance(tmp) * 1000, 2)
    for i in range(len(kline)):
        if 'v' in kline[i].keys():
            del kline[i]['v']
    return kline


def get_stock_kline_with_indicators(code, is_index=False, period=101, limit=120):
    # 添加技术指标布林线,布林线宽度
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
                        for j in range(i - 1, i - (day+1), -1):
                            tenth_volume.append(new_data[j]['volume'])
                        new_data[i]['10th_largest'] = max(tenth_volume)
                        new_data[i]['10th_minimum'] = min(tenth_volume)
                        new_data[i]['avg_volume'] = sum(tenth_volume) / len(tenth_volume)
                        new_data[i]['volume_ratio'] = round(new_data[i]['volume'] / new_data[i]['avg_volume'], 2)
                    if i >= 50:
                        tmp = []
                        for j in range(i, i-50, -1):
                            tmp.append(new_data[j]['close'])
                        new_data[i]['ma50'] = round(sum(tmp)/len(tmp), 2)
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
        print(i)
        pool.append({'day': i[0], 'open': i[1], 'close': i[4], 'high': i[2], 'low': i[3],
                     'last_close': i[5], 'applies': i[6], 'volume': i[7]})
    pool = pool[::-1]
    day = 10
    for i in range(len(pool)):
        pool[i]['TRI'] = TRI(pool[i]['high'], pool[i]['low'], pool[i]['last_close'])
        if i > day:
            tenth_volume = []
            for j in range(i - 1, i - (day+1), -1):
                tenth_volume.append(pool[j]['volume'])
            pool[i]['10th_largest'] = max(tenth_volume)
            pool[i]['10th_minimum'] = min(tenth_volume)
            pool[i]['avg_volume'] = sum(tenth_volume) / len(tenth_volume)
            pool[i]['volume_ratio'] = round(pool[i]['volume'] / pool[i]['avg_volume'], 2)
        if i >= 50:
            tmp = []
            for j in range(i, i-50, -1):
                tmp.append(pool[j]['close'])
            pool[i]['ma50'] = sum(tmp)/len(tmp)
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


def MA(kline, N):
    assert len(kline) >= N
    for i in range(len(kline)):
        if i >= N:
            tmp = []
            for j in range(i, i-N, -1):
                tmp.append(kline[j]['close'])
            kline[i][f'MA{N}'] = round(sum(tmp)/len(tmp), 2)
    return kline


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


def TRIX(kline: list):
    N, M = 12, 20
    kline = EMA_V2(EMA_V2(EMA_V2(kline, N), N, key=f'ema{N}'), N, key=f'ema{N}')
    for i in range(len(kline)):
        if i > 0:
            kline[i]['TRIX'] = round((kline[i][f'ema{N}'] - kline[i-1][f'ema{N}'])/kline[i-1][f'ema{N}'] * 100, 2)
        if i >= M:
            tmp = []
            for j in range(i, i-M, -1):
                tmp.append(kline[j]['TRIX'])
            kline[i]['TRIXMA'] = round(sum(tmp)/len(tmp), 2)
    return kline


def DMA(kline: list):
    N, M = 10, 50
    for i in range(len(kline)):
        if i >= 10:
            tmp = []
            for j in range(i, i-N, -1):
                tmp.append(kline[j]['close'])
            kline[i][f'ma{N}'] = sum(tmp)/len(tmp)
        if i >= M:
            tmp2 = []
            for j in range(i, i-M, -1):
                tmp2.append(kline[j]['close'])
            kline[i][f'ma{M}'] = sum(tmp2)/len(tmp2)
            kline[i]['DMA'] = round(kline[i][f'ma{N}']-kline[i][f'ma{M}'], 2)
        if i >= M+N:
            tmp3 = []
            for j in range(i, i-N, -1):
                tmp3.append(kline[j]['DMA'])
            kline[i]['AMA'] = round(sum(tmp3)/len(tmp3), 2)
        if f'ma{N}' in kline[i].keys():
            del kline[i][f'ma{N}']
        if f'ma{M}' in kline[i].keys():
            del kline[i][f'ma{M}']
    return kline[M+N:]


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
            for j in range(i, i-3, -1):
                tmp.append(kline[j]['close'])
            kline[i]['ma3'] = sum(tmp)/len(tmp)
        if i >= 6:
            tmp = []
            for j in range(i, i-6, -1):
                tmp.append(kline[j]['close'])
            kline[i]['ma6'] = sum(tmp)/len(tmp)
        if i >= 12:
            tmp = []
            for j in range(i, i-12, -1):
                tmp.append(kline[j]['close'])
            kline[i]['ma12'] = sum(tmp)/len(tmp)
        if i >= 24:
            tmp = []
            for j in range(i, i-24, -1):
                tmp.append(kline[j]['close'])
            kline[i]['ma24'] = sum(tmp)/len(tmp)
    for i in range(len(kline)):
        if i >= 24:
            kline[i]['BBI'] = round((kline[i]['ma3'] + kline[i]['ma6'] + kline[i]['ma12'] + kline[i]['ma24'])/4, 2)
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
    N, M = 12, 26
    kline = EMA_V2(EMA_V2(EMA_V2(kline, days=N), days=M), days=50)
    for i in range(len(kline)):
        kline[i]['DIF'] = kline[i][f'ema{N}'] - kline[i][f'ema{M}']
    kline = EMA_V2(kline, days=9, key='DIF', out_key='DEA')
    for i in range(len(kline)):
        kline[i]['MACD'] = 2 * (kline[i]['DIF'] - kline[i]['DEA'])
        if i > 0:
            if kline[i]['MACD'] > kline[i-1]['MACD']:
                kline[i]['macd_direction'] = 'UP'
            else:
                kline[i]['macd_direction'] = 'DOWN'
    return kline


def WAD(kline: list):
    # 威廉多空力度线
    for i in range(len(kline)):
        if i > 0:
            kline[i]['TRL'] = min(kline[i-1]['close'], kline[i]['low'])
            kline[i]['TRH'] = max(kline[i-1]['close'], kline[i]['high'])
            if kline[i]['close'] > kline[i-1]['close']:
                kline[i]['AD'] = kline[i]['close'] - kline[i]['TRL']
            if kline[i]['close'] < kline[i-1]['close']:
                kline[i]['AD'] = kline[i]['close'] - kline[i]['TRH']
            if kline[i]['close'] == kline[i-1]['close']:
                kline[i]['AD'] = 0
            kline[i]['WAD'] = round(kline[i]['AD'] + kline[i-1]['WAD'], 2)
        else:
            kline[i]['WAD'] = 0
        if i >= 30:
            tmp = []
            for j in range(i, i-30, -1):
                tmp.append(kline[j]['WAD'])
            kline[i]['MAWAD'] = round(sum(tmp)/len(tmp), 2)
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
            kline[i]['PV'] = kline[i]['close']/kline[i-1]['close'] if kline[i]['volume'] > kline[i-1]['volume'] else 1
            kline[i]['NV'] = kline[i]['close']/kline[i-1]['close'] if kline[i]['volume'] < kline[i-1]['volume'] else 1
            kline[i]['PVI'] = kline[i-1]['PVI'] * kline[i]['PV']
            kline[i]['NVI'] = kline[i-1]['NVI'] * kline[i]['NV']
        if i >= N:
            tmp_pvi = []
            tmp_nvi = []
            for j in range(i, i-N, -1):
                tmp_pvi.append(kline[j]['PVI'])
                tmp_nvi.append(kline[j]['NVI'])
            kline[i]['MA_PVI'] = round(sum(tmp_pvi)/len(tmp_pvi), 2)
            kline[i]['MA_NVI'] = round(sum(tmp_nvi)/len(tmp_nvi), 2)
    return kline[N:]


def PVT(kline: list):
    for i in range(len(kline)):
        if i > 0:
            kline[i]['PVT'] = (kline[i]['close'] - kline[i-1]['close'])/kline[i-1]['close']*kline[i]['VOL']
        if i > 1:
            kline[i]['PVT'] = kline[i]['PVT'] + kline[i-1]['PVT']
            if kline[i]['close'] < kline[i-1]['close'] and kline[i]['PVT'] > kline[i-1]['PVT']:
                kline[i]['PVT_SIG'] = "BUY"
            if kline[i]['close'] > kline[i-1]['close'] and kline[i]['PVT'] < kline[i-1]['PVT']:
                kline[i]['PVT_SIG'] = "SELL"
    return kline[1:]


def OBV(kline: list):
    for i in range(len(kline)):
        if i == 0:
            kline[i]['OBV'] = kline[i]['volume']
        else:
            if kline[i]['close'] > kline[i-1]['close']:
                kline[i]['OBV'] = kline[i-1]['OBV'] + kline[i]['volume']
            elif kline[i]['close'] < kline[i-1]['close']:
                kline[i]['OBV'] = kline[i-1]['OBV'] - kline[i]['volume']
            else:
                pass
    return kline


def Force_Index(kline: list):
    N, M = 2, 13
    for i in range(len(kline)):
        if i > 0:
            kline[i]['FI'] = kline[i]['VOL'] * (kline[i]['close'] - kline[i-1]['close'])
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
            DIRECTION = abs(kline[i]['close'] - kline[i-N]['close'])   # 方向
            tmp = []
            for j in range(i, i-N, -1):
                tmp.append(abs(kline[j]['close']-kline[j-1]['close']))
            VOLATILITY = sum(tmp)  # 波动率
            ER = abs(DIRECTION/VOLATILITY)    # 效率
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
            direction[i] = kline[i]['close'] - kline[i-N]['close']
    volatility = [0 for _ in range(len(kline))]
    delt = [0 for _ in range(len(kline))]
    for i in range(1, len(kline)):
        delt[i] = abs(kline[i]['close'] - kline[i-1]['close'])
    for i in range(N-1, len(kline)):
        sum = 0
        for j in range(N):
            sum = sum + delt[i-N+1+j]
        volatility[i] = sum

    fastest = 2/(NF + 1)
    slowest = 2/(NS + 1)

    ER = [0 for _ in range(len(kline))]
    smooth = [0 for _ in range(len(kline))]
    c = [0 for _ in range(len(kline))]

    for i in range(N, len(kline)):
        ER[i] = abs(direction[i]/volatility[i])
        smooth[i] = ER[i] * (fastest - slowest) + slowest
        c[i] = smooth[i] * smooth[i]

    ama = [0 for _ in range(len(kline))]
    ama[N-1] = kline[N-1]['close']
    for i in range(N, len(kline)):
        ama[i] = ama[i-1] + c[i] * (kline[i]['close'] - ama[i-1])
        kline[i]['KAMA'] = round(ama[i], 2)
    return kline[N:]


def pocket_protection(kline: list):
    close = kline[-1]['close']
    max_5 = max([i['close'] for i in kline[-5:]])
    ma50 = kline[-1]['ma50']
    if biggest_decline_calc(kline) < 50 and close == max_5 and close > ma50:
        # 半年内最大跌幅小于50% 收盘价创5日新高 收盘价大于50日均价
        if (kline[-1]['applies'] >= 5 and kline[-1]['volume'] > kline[-1]['10th_largest']) or kline[-1]['applies'] > 9.9:
            # 当日涨幅大于5%,成交量超过最近10日最大成交量 股价当日涨停则成交量不做要求
            return True


def BIAS(kline: list):
    N = 18
    A1 = 0.15
    for i in range(len(kline)):
        if i >= N:
            tmp = []
            for j in range(i, i-N, -1):
                tmp.append(kline[j]['close'])
            kline[i]['BIAS1'] = round(kline[i]['close']/(sum(tmp)/len(tmp)) - 1, 2)
            kline[i]['BIAS2'] = kline[i]['BIAS1'] * (1 + A1)
            kline[i]['BIAS3'] = kline[i]['BIAS1'] * (1 - A1)
    return kline


def ARBR(kline: list):
    N = 42
    for i in range(len(kline)):
        if i >= N:
            AR1, AR2 = [], []
            for j in range(i, i-N, -1):
                AR1.append(kline[j]['high'] - kline[j]['close'])
                AR2.append(kline[j]['open'] - kline[j]['low'])
            kline[i]['AR'] = round(sum(AR1)/sum(AR2), 2)
        if i > N:
            BR1, BR2 = [], []
            for j in range(i, i-N, -1):
                BR1.append(kline[j]['high'] - kline[j-1]['close'])
                BR2.append(kline[j-1]['close'] - kline[j]['low'])
            kline[i]['BR'] = round(sum(BR1)/sum(BR2), 2)
    return kline[N:]


def MTM(kline: list):
    N, M = 2, 30
    for i in range(len(kline)):
        if i >= N:
            kline[i]['MTM'] = round(kline[i]['close'] - kline[i-N]['close'], 2)
    kline = kline[N:]
    for i in range(len(kline)):
        if i >= M:
            tmp = []
            for j in range(i, i-M, -1):
                tmp.append(kline[j]['MTM'])
            kline[i]['MTMMA'] = round(sum(tmp)/len(tmp), 2)
    return kline[M:]


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


def stock_filter_by_MACD_and_BBI():
    logging.warning(f"stock filter by MACD and BBI !")
    pool = institutions_holding_rps_stock()
    result = []
    for i in pool:
        data = get_stock_kline_with_indicators(i['code'], limit=150)
        data = ATR(data)
        data = BBI(MACD(data))
        biggest_decline = biggest_decline_calc(data)
        if data[-1]['DIF'] > data[-1]['DEA'] and data[-2]['DIF'] < data[-2]['DEA'] and data[-1]['close'] > data[-1]['BBI']:
            i['industry'] = get_industry_by_code(i['code'])
            result.append(i)
            logging.warning(f"{i}\t半年内最大跌幅: {biggest_decline}")
    return result


def stock_filter_by_BooleanLine():
    logging.warning(f"stock filter by BooleanLine !")
    pool = institutions_holding_rps_stock()
    result = []
    for i in pool:
        data = get_stock_kline_with_indicators(i['code'], limit=150)
        data = ATR(data)
        data = BooleanLine(data)
        biggest_decline = biggest_decline_calc(data)
        if 0.2 >= data[-1]['BBW'] > data[-2]['BBW'] >= data[-3]['BBW']:
            i['BBW'] = data[-1]['BBW']
            i['week_applies'] = round((data[-1]['close'] - data[-5]['last_close'])/data[-5]['last_close']*100, 2)
            if i['week_applies'] > 0:
                i['industry'] = get_industry_by_code(i['code'])
                result.append(i)
                logging.warning(f"{i}\t半年内最大跌幅: {biggest_decline}")
    return result


def stock_filter_by_WAD():
    logging.warning(f"stock filter by WAD !")
    pool = institutions_holding_rps_stock()
    result = []
    for i in pool:
        data = get_stock_kline_with_indicators(i['code'], limit=180)
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


def stock_filter_by_MACD_and_BBI_test(code):
    data = get_market_data(code, start_date=20210101)
    data = BBI(MACD(data))
    for i in range(len(data)):
        if 'BBI' in data[i].keys():
            if data[i]['DIF'] > data[i]['DEA'] and data[i-1]['DIF'] < data[i-1]['DEA'] and data[i]['close'] > data[i]['BBI']:
                logging.warning(data[i])


def stock_filter_by_WAD_test(code):
    data = get_stock_kline_with_indicators(code, limit=250)
    data = WAD(data)
    for i in range(len(data)):
        if i > 0 and i+3 < len(data) and data[i]['WAD'] > data[i]['MAWAD'] and data[i-1]['WAD'] < data[i-1]['MAWAD']:
            logging.warning(f"{data[i]['day']}\t{data[i]['applies']}\t第二天:{data[i+1]['applies']}\t第三天:{data[i+2]['applies']}\t第四天:{data[i+3]['applies']}")


def stock_filter_by_Compact_Structure():
    # 股价结构紧凑
    pool = institutions_holding_rps_stock()
    result = []
    for i in pool:
        data = get_stock_kline_with_indicators(i['code'])
        data = Compact_Structure(data)
        i['variance'] = data[-1]['variance']
        result.append(i)
        logging.warning(i)
    return sorted(result, key=lambda x: x['variance'], reverse=True)


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
    return round((total_count - count)/total_count, 2)


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
    N, M = 13, 26
    ATR_parameter = 20
    kline = EMA_V2(EMA_V2(ATR(kline), N), M)
    for i in range(len(kline)):
        kline[i]['+1ATR'] = round(kline[i][f'ema{M}'] + kline[i][f'ATR_{ATR_parameter}'], 2)
        kline[i]['+2ATR'] = round(kline[i][f'ema{M}'] + 2 * kline[i][f'ATR_{ATR_parameter}'], 2)
        kline[i]['+3ATR'] = round(kline[i][f'ema{M}'] + 3 * kline[i][f'ATR_{ATR_parameter}'], 2)
        kline[i]['-1ATR'] = round(kline[i][f'ema{M}'] - kline[i][f'ATR_{ATR_parameter}'], 2)
        kline[i]['-2ATR'] = round(kline[i][f'ema{M}'] - 2 * kline[i][f'ATR_{ATR_parameter}'], 2)
        kline[i]['-3ATR'] = round(kline[i][f'ema{M}'] - 3 * kline[i][f'ATR_{ATR_parameter}'], 2)
    return kline


class Channel:

    def __init__(self, code, name="UNKONW"):
        self.code = code
        self.name = name
        self.kline = get_stock_kline_with_indicators(code)
        self.channel_trade_system()

    def channel_trade_system(self):
        N, M = 13, 26
        self.kline = EMA_V2(EMA_V2(self.kline, N), M)
        up_channel_coefficients, down_channel_coefficients = self.find_channel_coefficients()
        logging.warning(f"code: {self.code}\tname: {self.name}\t"
                        f"up_channel_coefficients:{up_channel_coefficients}\t"
                        f"down_channel_coefficients:{down_channel_coefficients}")
        for i in range(len(self.kline)):
            self.kline[i]['up_channel'] = self.kline[i][f'ema{M}'] + up_channel_coefficients * self.kline[i][f'ema{M}']
            self.kline[i]['down_channel'] = self.kline[i][f'ema{M}'] - down_channel_coefficients * self.kline[i][f'ema{M}']

    def calc_coefficients(self, M=26, up_channel_coefficients=0.05, down_channel_coefficients=0.05):
        up_count, down_count = 0, 0
        total_count = len(self.kline)
        for i in range(len(self.kline)):
            self.kline[i]['up_channel'] = self.kline[i][f'ema{M}'] + up_channel_coefficients * self.kline[i][f'ema{M}']
            self.kline[i]['down_channel'] = self.kline[i][f'ema{M}'] - down_channel_coefficients * self.kline[i][f'ema{M}']
        for i in range(len(self.kline)):
            if self.kline[i]['close'] > self.kline[i]['up_channel']:
                up_count += 1
            if self.kline[i]['close'] < self.kline[i]['down_channel']:
                down_count += 1
        return round((total_count - up_count)/total_count, 2), round((total_count - down_count)/total_count, 2)

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
        return round(up_channel_coefficients, 2), round(down_channel_coefficients, 2)


# stock_filter_by_MACD_and_BBI()
# stock_filter_by_BooleanLine()
# stock_filter_by_WAD()
# stock_filter_by_pocket_protection()




