# encoding: utf-8
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
                return new_data[1:]
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


def KDJ(kline: list):
    day = 9
    for i in range(1, len(kline)):
        if i >= day:
            Cn = kline[i]['close']
            prices = []
            for j in range(i, i-day, -1):
                prices.append(kline[j]['high'])
                prices.append(kline[j]['low'])
            Hn = max(prices)
            Ln = min(prices)
            RSV = (Cn-Ln)/(Hn-Ln)*100
            K = 2/3*kline[i-1]['K']+1/3*RSV
            D = 2/3*kline[i-1]['D']+1/3*K
            J = 3*K-2*D
            kline[i]['K'], kline[i]['D'], kline[i]['J'] = round(K, 2), round(D, 2), round(J, 2)
        else:
            kline[i]['K'], kline[i]['D'] = 50, 50
    for i in range(len(kline)):
        if 'K' in kline[i].keys():
            if kline[i]['K'] > kline[i]['D'] and kline[i-1]['K'] < kline[i-1]['D']:
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
            for j in range(i, i-number, -1):
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
            emas[i] = ((days-1)*emas[i-1]+2*cps[i])/(days+1)
    return emas


def EMA_V2(cps, days):
    emas = cps.copy()
    for i in range(len(cps)):
        if i == 0:
            emas[i][f'ema{days}'] = cps[i]['close']
        if i > 0:
            emas[i][f'ema{days}'] = ((days-1)*emas[i-1][f'ema{days}']+2*cps[i]['close'])/(days+1)
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
    TR = EMA_V2(EMA_V2(EMA_V2(data, N), N), N)
    trix = []
    for i in range(len(TR)):
        if i > 0:
            trix.append(round((TR[i] - TR[i-1])/TR[i-1]*100, 2))
    matrix = []
    for i in range(len(trix)):
        if i >= M:
            tmp = []
            for j in range(i, i-M, -1):
                tmp.append(trix[j])
            matrix.append(round(sum(tmp)/len(tmp), 2))
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
    for i in range(1, len(kline)+1):
        x.append(kline[i-1]['close'])
        y.append(i)
        points.append({'x': kline[i-1]['close'], 'y': i})
    x_mean = sum(x)/len(x)
    y_mean = sum(y)/len(y)
    tmp = [k*v for k, v in zip(x, y)]
    x_y_mean = sum(tmp)/len(tmp)
    tmp = [i**2 for i in x]
    x_square_mean = sum(tmp)/len(tmp)
    m = (x_y_mean - x_mean * y_mean) / (x_square_mean - x_mean ** 2)
    b = y_mean - m * x_mean
    for i in points:
        i['y_predict'] = m * i['x'] + b
        i['square_error'] = (i['y'] - i['y_predict'])**2
        i['square_from_mean_y'] = (i['y'] - y_mean)**2
    SE_line = sum([i['square_error'] for i in points])
    SE_y_mean = sum([i['square_from_mean_y'] for i in points])
    R_square = 1 - SE_line/SE_y_mean
    # print(f"R_Square: {round(R_square, 2)}\t斜率: {round(m, 2)}\t截距: {round(b, 2)}")
    return {'R_Square': round(R_square, 2), 'slope': round(m, 2), 'intercept': round(b, 2)}


def KDJ_test(code):
    data = get_stock_kline_with_indicators(code)
    data = KDJ(data)
    for i in range(len(data)):
        if 'K' in data[i].keys():
            if data[i]['K'] > data[i]['D'] and data[i-1]['K'] < data[i-1]['D']:
                print(data[i])


def BooleanLine_test(code):
    data = get_stock_kline_with_indicators(code, limit=250)
    for i in range(len(data)):
        if 'BBW' in data[i].keys() and i-2 > 20:
            if data[i]['BBW'] > data[i-1]['BBW'] > data[i-2]['BBW']:
                if round(data[i]['close']/data[i-5]['close']-1, 2) > 0.08:
                    print(f"前五天涨幅: {round(data[i]['close']/data[i-5]['close']-1, 2)}\t后二十天涨幅: {round(data[i+20]['close']/data[i]['close']-1, 2)}")
                    print(data[i])


def RVI(kline: list):
    N = 10
    for i in range(len(kline)):
        kline[i]['Co'] = kline[i]['close'] - kline[i]['open']
        kline[i]['HL'] = kline[i]['high'] - kline[i]['low']
        if i >= 3:
            kline[i]['V1'] = (kline[i]['Co'] + 2 * kline[i-1]['Co'] + 2 * kline[i-2]['Co'] + kline[i-3]['Co'])/6
            kline[i]['V2'] = (kline[i]['HL'] + 2 * kline[i - 1]['HL'] + 2 * kline[i - 2]['HL'] + kline[i - 3]['HL'])/6
        if i >= N + 3:
            tmp1, tmp2 = [], []
            for j in range(i, i-N, -1):
                tmp1.append(kline[j]['V1'])
                tmp2.append(kline[j]['V2'])
            S1 = sum(tmp1)
            S2 = sum(tmp2)
            kline[i]['RVI'] = S1/S2
        if i >= N + 6:
            kline[i]['RVIS'] = (kline[i]['RVI'] + 2*kline[i-1]['RVI'] + 2*kline[i-2]['RVI'] + kline[i-3]['RVI'])/6
    return kline


def Keltner(kline: list):
    basic_price = [(i['close']+i['high']+i['low'])/3 for i in kline]
    mid = EMA(basic_price, 20)
    print(len(kline), len(mid))
    for i in range(len(kline)):
        if 'ATR_20' in kline[i].keys():
            kline[i]['mid_line'] = mid[i]
            kline[i]['on_line'] = mid[i] + kline[i]['ATR_20']
            kline[i]['under_line'] = mid[i] - kline[i]['ATR_20']
    return kline


def linear_regression_filter(pool):
    for i in pool:
        kline = get_stock_kline_with_indicators(i['code'], limit=120)
        r = Linear_Regression(kline)
        i['R_Square'] = r['R_Square']
        i['slope'] = r['slope']
        i['intercept'] = r['intercept']
    return sorted(p, key=lambda x: x['R_Square'], reverse=True)


p = [{'code': '300316', 'name': '晶盛机电', 'value': 0.8, 'R_Square': 0.93, 'slope': 2.48, 'intercept': -66.37}, {'code': '002812', 'name': '恩捷股份', 'value': 0.93, 'R_Square': 0.92, 'slope': 0.5, 'intercept': -42.51}, {'code': '600884', 'name': '杉杉股份', 'value': 0.93, 'R_Square': 0.91, 'slope': 4.48, 'intercept': -46.75}, {'code': '000683', 'name': '远兴能源', 'value': 0.78, 'R_Square': 0.9, 'slope': 10.16, 'intercept': -3.47}, {'code': '600641', 'name': '万业企业', 'value': 0.97, 'R_Square': 0.9, 'slope': 6.93, 'intercept': -72.51}, {'code': '603185', 'name': '上机数控', 'value': 0.75, 'R_Square': 0.89, 'slope': 0.51, 'intercept': -41.1}, {'code': '600580', 'name': '卧龙电驱', 'value': 0.95, 'R_Square': 0.89, 'slope': 21.14, 'intercept': -207.51}, {'code': '000887', 'name': '中鼎股份', 'value': 0.85, 'R_Square': 0.89, 'slope': 13.25, 'intercept': -113.75}, {'code': '600500', 'name': '中化国际', 'value': 0.91, 'R_Square': 0.89, 'slope': 17.47, 'intercept': -74.95}, {'code': '000301', 'name': '东方盛虹', 'value': 0.76, 'R_Square': 0.88, 'slope': 4.63, 'intercept': -41.01}, {'code': '600348', 'name': '华阳股份', 'value': 0.79, 'R_Square': 0.88, 'slope': 10.63, 'intercept': -29.94}, {'code': '002497', 'name': '雅化集团', 'value': 0.81, 'R_Square': 0.87, 'slope': 5.09, 'intercept': -72.12}, {'code': '601865', 'name': '福莱特', 'value': 0.81, 'R_Square': 0.87, 'slope': 3.23, 'intercept': -62.35}, {'code': '300073', 'name': '当升科技', 'value': 0.92, 'R_Square': 0.86, 'slope': 2.47, 'intercept': -94.48}, {'code': '002091', 'name': '江苏国泰', 'value': 0.83, 'R_Square': 0.86, 'slope': 10.02, 'intercept': -42.96}, {'code': '601908', 'name': '京运通', 'value': 0.82, 'R_Square': 0.86, 'slope': 19.17, 'intercept': -122.24}, {'code': '601222', 'name': '林洋能源', 'value': 0.91, 'R_Square': 0.85, 'slope': 14.75, 'intercept': -69.59}, {'code': '601699', 'name': '潞安环能', 'value': 0.84, 'R_Square': 0.84, 'slope': 10.56, 'intercept': -65.54}, {'code': '600111', 'name': '北方稀土', 'value': 0.82, 'R_Square': 0.82, 'slope': 2.27, 'intercept': -12.72}, {'code': '000830', 'name': '鲁西化工', 'value': 0.93, 'R_Square': 0.82, 'slope': 11.59, 'intercept': -157.14}, {'code': '601117', 'name': '中国化学', 'value': 0.79, 'R_Square': 0.82, 'slope': 13.21, 'intercept': -55.22}, {'code': '600958', 'name': '东方证券', 'value': 0.89, 'R_Square': 0.81, 'slope': 10.14, 'intercept': -56.54}, {'code': '600141', 'name': '兴发集团', 'value': 0.9, 'R_Square': 0.81, 'slope': 3.02, 'intercept': -11.58}, {'code': '000825', 'name': '太钢不锈', 'value': 0.9, 'R_Square': 0.8, 'slope': 15.9, 'intercept': -68.31}, {'code': '600582', 'name': '天地科技', 'value': 0.92, 'R_Square': 0.8, 'slope': 44.42, 'intercept': -128.45}, {'code': '000960', 'name': '锡业股份', 'value': 0.86, 'R_Square': 0.79, 'slope': 10.16, 'intercept': -111.46}, {'code': '002048', 'name': '宁波华翔', 'value': 0.91, 'R_Square': 0.79, 'slope': 13.99, 'intercept': -206.86}, {'code': '600307', 'name': '酒钢宏兴', 'value': 0.92, 'R_Square': 0.79, 'slope': 74.35, 'intercept': -127.77}, {'code': '000983', 'name': '山西焦煤', 'value': 0.8, 'R_Square': 0.78, 'slope': 11.47, 'intercept': -31.84}, {'code': '002268', 'name': '卫 士 通', 'value': 0.84, 'R_Square': 0.78, 'slope': 3.06, 'intercept': -18.7}, {'code': '600010', 'name': '包钢股份', 'value': 0.91, 'R_Square': 0.77, 'slope': 38.96, 'intercept': -25.65}, {'code': '300037', 'name': '新宙邦', 'value': 0.95, 'R_Square': 0.77, 'slope': 1.42, 'intercept': -83.01}, {'code': '603260', 'name': '合盛硅业', 'value': 0.83, 'R_Square': 0.77, 'slope': 0.5, 'intercept': 9.72}, {'code': '601958', 'name': '金钼股份', 'value': 0.85, 'R_Square': 0.76, 'slope': 26.86, 'intercept': -127.7}, {'code': '603659', 'name': '璞泰来', 'value': 0.93, 'R_Square': 0.75, 'slope': 1.0, 'intercept': -66.75}, {'code': '002408', 'name': '齐翔腾达', 'value': 0.96, 'R_Square': 0.75, 'slope': 13.65, 'intercept': -104.31}, {'code': '000488', 'name': '晨鸣纸业', 'value': 0.68, 'R_Square': 0.75, 'slope': -23.42, 'intercept': 274.13}, {'code': '600623', 'name': '华谊集团', 'value': 0.89, 'R_Square': 0.75, 'slope': 15.41, 'intercept': -90.43}, {'code': '002709', 'name': '天赐材料', 'value': 0.91, 'R_Square': 0.74, 'slope': 1.27, 'intercept': -71.54}, {'code': '002002', 'name': '鸿达兴业', 'value': 0.97, 'R_Square': 0.74, 'slope': 32.71, 'intercept': -90.41}, {'code': '600970', 'name': '中材国际', 'value': 0.88, 'R_Square': 0.74, 'slope': 18.54, 'intercept': -129.98}, {'code': '300474', 'name': '景嘉微', 'value': 0.89, 'R_Square': 0.74, 'slope': 1.95, 'intercept': -119.73}, {'code': '603379', 'name': '三美股份', 'value': 0.86, 'R_Square': 0.74, 'slope': 5.33, 'intercept': -51.29}, {'code': '601106', 'name': '中国一重', 'value': 0.94, 'R_Square': 0.73, 'slope': 59.76, 'intercept': -134.45}, {'code': '000959', 'name': '首钢股份', 'value': 0.84, 'R_Square': 0.73, 'slope': 26.19, 'intercept': -96.0}, {'code': '002340', 'name': '格林美', 'value': 0.9, 'R_Square': 0.72, 'slope': 19.97, 'intercept': -156.43}, {'code': '600711', 'name': '盛屯矿业', 'value': 0.85, 'R_Square': 0.72, 'slope': 14.85, 'intercept': -69.12}, {'code': '600160', 'name': '巨化股份', 'value': 0.93, 'R_Square': 0.72, 'slope': 10.92, 'intercept': -62.13}, {'code': '601600', 'name': '中国铝业', 'value': 0.91, 'R_Square': 0.7, 'slope': 20.03, 'intercept': -55.8}, {'code': '603077', 'name': '和邦生物', 'value': 0.88, 'R_Square': 0.7, 'slope': 38.19, 'intercept': -28.67}, {'code': '600808', 'name': '马钢股份', 'value': 0.85, 'R_Square': 0.7, 'slope': 32.17, 'intercept': -83.06}, {'code': '002080', 'name': '中材科技', 'value': 0.94, 'R_Square': 0.69, 'slope': 5.24, 'intercept': -76.43}, {'code': '300682', 'name': '朗新科技', 'value': 0.99, 'R_Square': 0.69, 'slope': 15.53, 'intercept': -220.24}, {'code': '600089', 'name': '特变电工', 'value': 0.88, 'R_Square': 0.68, 'slope': 5.64, 'intercept': -25.41}, {'code': '601866', 'name': '中远海发', 'value': 0.95, 'R_Square': 0.68, 'slope': 51.18, 'intercept': -117.73}, {'code': '000768', 'name': '中航西飞', 'value': 0.84, 'R_Square': 0.67, 'slope': 8.63, 'intercept': -178.74}, {'code': '600018', 'name': '上港集团', 'value': 0.98, 'R_Square': 0.67, 'slope': 60.09, 'intercept': -242.73}, {'code': '600259', 'name': '广晟有色', 'value': 0.84, 'R_Square': 0.67, 'slope': 3.22, 'intercept': -74.8}, {'code': '600246', 'name': '万通发展', 'value': 0.99, 'R_Square': 0.67, 'slope': 25.95, 'intercept': -160.28}, {'code': '000630', 'name': '铜陵有色', 'value': 0.81, 'R_Square': 0.66, 'slope': 43.96, 'intercept': -84.73}, {'code': '002203', 'name': '海亮股份', 'value': 0.95, 'R_Square': 0.66, 'slope': 40.24, 'intercept': -371.22}, {'code': '000568', 'name': '泸州老窖', 'value': 0.54, 'R_Square': 0.65, 'slope': -0.82, 'intercept': 242.17}, {'code': '600256', 'name': '广汇能源', 'value': 0.87, 'R_Square': 0.65, 'slope': 17.57, 'intercept': -13.41}, {'code': '600022', 'name': '山东钢铁', 'value': 0.95, 'R_Square': 0.65, 'slope': 108.47, 'intercept': -150.56}, {'code': '601877', 'name': '正泰电器', 'value': 0.87, 'R_Square': 0.63, 'slope': 2.7, 'intercept': -45.29}, {'code': '000629', 'name': '攀钢钒钛', 'value': 0.91, 'R_Square': 0.63, 'slope': 32.91, 'intercept': -33.84}, {'code': '601669', 'name': '中国电建', 'value': 0.98, 'R_Square': 0.62, 'slope': 18.28, 'intercept': -27.85}, {'code': '600395', 'name': '盘江股份', 'value': 0.82, 'R_Square': 0.62, 'slope': 20.01, 'intercept': -99.4}, {'code': '601615', 'name': '明阳智能', 'value': 0.91, 'R_Square': 0.61, 'slope': 9.08, 'intercept': -105.06}, {'code': '002092', 'name': '中泰化学', 'value': 0.89, 'R_Square': 0.61, 'slope': 12.3, 'intercept': -78.7}, {'code': '600008', 'name': '首创环保', 'value': 1.0, 'R_Square': 0.61, 'slope': 84.51, 'intercept': -213.27}, {'code': '600188', 'name': '兖州煤业', 'value': 0.87, 'R_Square': 0.6, 'slope': 5.04, 'intercept': -27.15}, {'code': '600755', 'name': '厦门国贸', 'value': 0.92, 'R_Square': 0.6, 'slope': 36.45, 'intercept': -218.39}, {'code': '002010', 'name': '传化智联', 'value': 0.97, 'R_Square': 0.6, 'slope': 25.5, 'intercept': -132.2}, {'code': '601666', 'name': '平煤股份', 'value': 0.95, 'R_Square': 0.6, 'slope': 17.31, 'intercept': -68.8}, {'code': '300861', 'name': '美畅股份', 'value': 0.88, 'R_Square': 0.59, 'slope': 2.67, 'intercept': -132.48}, {'code': '000807', 'name': '云铝股份', 'value': 0.8, 'R_Square': 0.58, 'slope': 9.65, 'intercept': -74.11}, {'code': '600068', 'name': '葛洲坝', 'value': 0.98, 'R_Square': 0.58, 'slope': 34.76, 'intercept': -208.47}, {'code': '000758', 'name': '中色股份', 'value': 0.86, 'R_Square': 0.58, 'slope': 35.88, 'intercept': -139.08}, {'code': '601139', 'name': '深圳燃气', 'value': 0.84, 'R_Square': 0.58, 'slope': 13.36, 'intercept': -48.73}, {'code': '000776', 'name': '广发证券', 'value': 0.91, 'R_Square': 0.57, 'slope': 8.97, 'intercept': -90.62}, {'code': '600673', 'name': '东阳光', 'value': 0.95, 'R_Square': 0.57, 'slope': 15.25, 'intercept': -27.12}, {'code': '601179', 'name': '中国西电', 'value': 0.95, 'R_Square': 0.56, 'slope': 32.77, 'intercept': -90.78}, {'code': '002013', 'name': '中航机电', 'value': 0.94, 'R_Square': 0.55, 'slope': 18.2, 'intercept': -137.05}, {'code': '601127', 'name': '小康股份', 'value': 0.84, 'R_Square': 0.55, 'slope': 1.75, 'intercept': -44.19}, {'code': '300122', 'name': '智飞生物', 'value': 0.69, 'R_Square': 0.54, 'slope': -1.38, 'intercept': 308.96}, {'code': '601618', 'name': '中国中冶', 'value': 0.84, 'R_Square': 0.53, 'slope': 32.85, 'intercept': -58.59}, {'code': '300072', 'name': '三聚环保', 'value': 0.87, 'R_Square': 0.53, 'slope': 52.37, 'intercept': -257.49}, {'code': '300759', 'name': '康龙化成', 'value': 0.87, 'R_Square': 0.51, 'slope': 1.08, 'intercept': -144.76}, {'code': '000039', 'name': '中集集团', 'value': 0.92, 'R_Square': 0.51, 'slope': 16.64, 'intercept': -225.2}, {'code': '600782', 'name': '新钢股份', 'value': 0.82, 'R_Square': 0.5, 'slope': 20.28, 'intercept': -81.6}, {'code': '601608', 'name': '中信重工', 'value': 0.99, 'R_Square': 0.49, 'slope': 35.82, 'intercept': -76.51}, {'code': '600642', 'name': '申能股份', 'value': 0.97, 'R_Square': 0.48, 'slope': 61.7, 'intercept': -315.62}, {'code': '600787', 'name': '中储股份', 'value': 0.99, 'R_Square': 0.48, 'slope': 31.84, 'intercept': -120.0}, {'code': '600497', 'name': '驰宏锌锗', 'value': 0.86, 'R_Square': 0.47, 'slope': 46.02, 'intercept': -170.96}, {'code': '601168', 'name': '西部矿业', 'value': 0.83, 'R_Square': 0.45, 'slope': 14.38, 'intercept': -146.64}, {'code': '000400', 'name': '许继电气', 'value': 0.93, 'R_Square': 0.45, 'slope': 8.23, 'intercept': -63.2}, {'code': '002821', 'name': '凯莱英', 'value': 0.94, 'R_Square': 0.42, 'slope': 0.59, 'intercept': -154.48}, {'code': '002266', 'name': '浙富控股', 'value': 0.97, 'R_Square': 0.42, 'slope': 32.19, 'intercept': -122.26}, {'code': '000027', 'name': '深圳能源', 'value': 0.72, 'R_Square': 0.41, 'slope': -22.63, 'intercept': 271.53}, {'code': '600985', 'name': '淮北矿业', 'value': 0.86, 'R_Square': 0.41, 'slope': 13.08, 'intercept': -102.33}, {'code': '600809', 'name': '山西汾酒', 'value': 0.62, 'R_Square': 0.4, 'slope': -0.31, 'intercept': 176.56}, {'code': '002202', 'name': '金风科技', 'value': 0.88, 'R_Square': 0.4, 'slope': 12.5, 'intercept': -106.88}, {'code': '600875', 'name': '东方电气', 'value': 0.98, 'R_Square': 0.4, 'slope': 9.63, 'intercept': -60.79}, {'code': '000739', 'name': '普洛药业', 'value': 0.94, 'R_Square': 0.39, 'slope': 7.01, 'intercept': -146.05}, {'code': '000591', 'name': '太阳能', 'value': 0.97, 'R_Square': 0.39, 'slope': 22.49, 'intercept': -97.26}, {'code': '600150', 'name': '中国船舶', 'value': 0.96, 'R_Square': 0.38, 'slope': 6.16, 'intercept': -51.46}, {'code': '002610', 'name': '爱康科技', 'value': 0.83, 'R_Square': 0.36, 'slope': 21.26, 'intercept': -0.18}, {'code': '002128', 'name': '露天煤业', 'value': 0.95, 'R_Square': 0.36, 'slope': 11.41, 'intercept': -69.3}, {'code': '600795', 'name': '国电电力', 'value': 1.0, 'R_Square': 0.35, 'slope': 96.91, 'intercept': -176.35}, {'code': '600516', 'name': '方大炭素', 'value': 0.89, 'R_Square': 0.35, 'slope': 13.6, 'intercept': -66.43}, {'code': '600011', 'name': '华能国际', 'value': 1.0, 'R_Square': 0.35, 'slope': 21.19, 'intercept': -36.17}, {'code': '002064', 'name': '华峰化学', 'value': 0.77, 'R_Square': 0.35, 'slope': 20.07, 'intercept': -200.42}, {'code': '600777', 'name': '新潮能源', 'value': 0.86, 'R_Square': 0.35, 'slope': 61.55, 'intercept': -44.17}, {'code': '600312', 'name': '平高电气', 'value': 0.96, 'R_Square': 0.35, 'slope': 24.13, 'intercept': -96.65}, {'code': '000937', 'name': '冀中能源', 'value': 0.86, 'R_Square': 0.35, 'slope': 15.67, 'intercept': -9.75}, {'code': '601898', 'name': '中煤能源', 'value': 0.92, 'R_Square': 0.34, 'slope': 25.66, 'intercept': -132.4}, {'code': '603225', 'name': '新凤鸣', 'value': 0.84, 'R_Square': 0.34, 'slope': 11.18, 'intercept': -155.28}, {'code': '601857', 'name': '中国石油', 'value': 0.97, 'R_Square': 0.33, 'slope': 46.45, 'intercept': -162.27}, {'code': '002353', 'name': '杰瑞股份', 'value': 0.87, 'R_Square': 0.33, 'slope': 4.77, 'intercept': -128.03}, {'code': '000709', 'name': '河钢股份', 'value': 0.94, 'R_Square': 0.33, 'slope': 76.43, 'intercept': -145.22}, {'code': '601016', 'name': '节能风电', 'value': 0.93, 'R_Square': 0.33, 'slope': 32.26, 'intercept': -77.53}, {'code': '600273', 'name': '嘉化能源', 'value': 0.87, 'R_Square': 0.33, 'slope': 15.04, 'intercept': -84.91}, {'code': '601005', 'name': '重庆钢铁', 'value': 0.88, 'R_Square': 0.32, 'slope': 64.62, 'intercept': -110.07}, {'code': '000898', 'name': '鞍钢股份', 'value': 0.85, 'R_Square': 0.32, 'slope': 35.64, 'intercept': -110.13}, {'code': '000933', 'name': '神火股份', 'value': 0.88, 'R_Square': 0.31, 'slope': 10.26, 'intercept': -60.96}, {'code': '002110', 'name': '三钢闽光', 'value': 0.88, 'R_Square': 0.3, 'slope': 16.93, 'intercept': -81.52}, {'code': '600873', 'name': '梅花生物', 'value': 0.98, 'R_Square': 0.29, 'slope': 43.16, 'intercept': -207.06}, {'code': '600871', 'name': '石化油服', 'value': 0.91, 'R_Square': 0.29, 'slope': 111.11, 'intercept': -171.48}, {'code': '600157', 'name': '永泰能源', 'value': 0.91, 'R_Square': 0.27, 'slope': 88.27, 'intercept': -88.57}, {'code': '600968', 'name': '海油发展', 'value': 0.9, 'R_Square': 0.27, 'slope': 93.88, 'intercept': -188.16}, {'code': '300059', 'name': '东方财富', 'value': 0.85, 'R_Square': 0.26, 'slope': 8.19, 'intercept': -200.74}, {'code': '002028', 'name': '思源电气', 'value': 0.94, 'R_Square': 0.26, 'slope': 4.95, 'intercept': -89.88}, {'code': '600027', 'name': '华电国际', 'value': 0.98, 'R_Square': 0.25, 'slope': 40.16, 'intercept': -84.54}, {'code': '601598', 'name': '中国外运', 'value': 0.95, 'R_Square': 0.25, 'slope': 45.35, 'intercept': -163.75}, {'code': '603456', 'name': '九洲药业', 'value': 0.96, 'R_Square': 0.24, 'slope': 5.46, 'intercept': -182.72}, {'code': '601800', 'name': '中国交建', 'value': 0.89, 'R_Square': 0.24, 'slope': 19.84, 'intercept': -79.44}, {'code': '000883', 'name': '湖北能源', 'value': 0.83, 'R_Square': 0.23, 'slope': -32.4, 'intercept': 216.0}, {'code': '300725', 'name': '药石科技', 'value': 0.94, 'R_Square': 0.22, 'slope': 0.95, 'intercept': -92.36}, {'code': '603198', 'name': '迎驾贡酒', 'value': 0.89, 'R_Square': 0.22, 'slope': 3.06, 'intercept': -66.66}, {'code': '601225', 'name': '陕西煤业', 'value': 0.97, 'R_Square': 0.2, 'slope': 11.16, 'intercept': -73.45}, {'code': '600019', 'name': '宝钢股份', 'value': 0.86, 'R_Square': 0.18, 'slope': 14.07, 'intercept': -57.94}, {'code': '000799', 'name': '酒鬼酒', 'value': 0.94, 'R_Square': 0.16, 'slope': 0.5, 'intercept': -52.17}, {'code': '600039', 'name': '四川路桥', 'value': 0.99, 'R_Square': 0.16, 'slope': 18.02, 'intercept': -65.18}, {'code': '600863', 'name': '内蒙华电', 'value': 1.0, 'R_Square': 0.16, 'slope': 34.05, 'intercept': -26.28}, {'code': '601985', 'name': '中国核电', 'value': 0.95, 'R_Square': 0.14, 'slope': 22.62, 'intercept': -60.2}, {'code': '600507', 'name': '方大特钢', 'value': 0.84, 'R_Square': 0.14, 'slope': -12.73, 'intercept': 163.65}, {'code': '601991', 'name': '大唐发电', 'value': 1.0, 'R_Square': 0.13, 'slope': 74.86, 'intercept': -140.32}, {'code': '603489', 'name': '八方股份', 'value': 0.93, 'R_Square': 0.12, 'slope': 0.63, 'intercept': -79.0}, {'code': '600021', 'name': '上海电力', 'value': 1.0, 'R_Square': 0.12, 'slope': 14.36, 'intercept': -44.96}, {'code': '601611', 'name': '中国核建', 'value': 0.97, 'R_Square': 0.12, 'slope': 12.96, 'intercept': -40.74}, {'code': '600567', 'name': '山鹰国际', 'value': 0.93, 'R_Square': 0.11, 'slope': -61.16, 'intercept': 275.96}, {'code': '002597', 'name': '金禾实业', 'value': 0.79, 'R_Square': 0.1, 'slope': 3.1, 'intercept': -47.07}, {'code': '600740', 'name': '山西焦化', 'value': 0.81, 'R_Square': 0.1, 'slope': 6.59, 'intercept': 18.77}, {'code': '600989', 'name': '宝丰能源', 'value': 0.84, 'R_Square': 0.09, 'slope': 7.93, 'intercept': -64.13}, {'code': '600886', 'name': '国投电力', 'value': 0.96, 'R_Square': 0.09, 'slope': -17.81, 'intercept': 231.48}, {'code': '600236', 'name': '桂冠电力', 'value': 0.95, 'R_Square': 0.09, 'slope': 26.19, 'intercept': -81.22}, {'code': '603259', 'name': '药明康德', 'value': 0.8, 'R_Square': 0.07, 'slope': -0.7, 'intercept': 164.96}, {'code': '600733', 'name': '北汽蓝谷', 'value': 0.61, 'R_Square': 0.07, 'slope': -4.2, 'intercept': 116.43}, {'code': '000778', 'name': '新兴铸管', 'value': 0.96, 'R_Square': 0.07, 'slope': 32.63, 'intercept': -73.98}, {'code': '600025', 'name': '华能水电', 'value': 0.93, 'R_Square': 0.07, 'slope': 19.58, 'intercept': -52.95}, {'code': '601058', 'name': '赛轮轮胎', 'value': 0.86, 'R_Square': 0.05, 'slope': -13.23, 'intercept': 188.52}, {'code': '000537', 'name': '广宇发展', 'value': 1.0, 'R_Square': 0.05, 'slope': 4.72, 'intercept': 33.47}, {'code': '600956', 'name': '新天绿能', 'value': 0.91, 'R_Square': 0.05, 'slope': 5.01, 'intercept': -7.27}, {'code': '600406', 'name': '国电南瑞', 'value': 0.91, 'R_Square': 0.04, 'slope': 2.18, 'intercept': -5.07}, {'code': '002004', 'name': '华邦健康', 'value': 0.88, 'R_Square': 0.04, 'slope': 8.22, 'intercept': 7.91}, {'code': '603885', 'name': '吉祥航空', 'value': 0.87, 'R_Square': 0.04, 'slope': -5.3, 'intercept': 138.63}, {'code': '600688', 'name': '上海石化', 'value': 0.91, 'R_Square': 0.02, 'slope': 11.84, 'intercept': 16.16}, {'code': '000717', 'name': '韶钢松山', 'value': 0.9, 'R_Square': 0.02, 'slope': 9.9, 'intercept': 9.26}, {'code': '600339', 'name': '中油工程', 'value': 0.94, 'R_Square': 0.02, 'slope': 28.19, 'intercept': -21.41}, {'code': '600176', 'name': '中国巨石', 'value': 0.7, 'R_Square': 0.01, 'slope': 2.23, 'intercept': 21.51}, {'code': '600674', 'name': '川投能源', 'value': 0.92, 'R_Square': 0.01, 'slope': 5.11, 'intercept': -0.63}, {'code': '600282', 'name': '南钢股份', 'value': 0.89, 'R_Square': 0.01, 'slope': 9.74, 'intercept': 21.2}, {'code': '300347', 'name': '泰格医药', 'value': 0.81, 'R_Square': 0.0, 'slope': -0.1, 'intercept': 75.87}, {'code': '601088', 'name': '中国神华', 'value': 0.96, 'R_Square': 0.0, 'slope': -0.25, 'intercept': 64.93}, {'code': '600426', 'name': '华鲁恒升', 'value': 0.71, 'R_Square': 0.0, 'slope': -0.29, 'intercept': 70.24}, {'code': '600362', 'name': '江西铜业', 'value': 0.81, 'R_Square': 0.0, 'slope': 0.83, 'intercept': 39.02}, {'code': '601838', 'name': '成都银行', 'value': 0.85, 'R_Square': 0.0, 'slope': -1.47, 'intercept': 77.83}, {'code': '603127', 'name': '昭衍新药', 'value': 0.74, 'R_Square': 0.0, 'slope': 0.04, 'intercept': 53.78}, {'code': '002532', 'name': '天山铝业', 'value': 0.83, 'R_Square': 0.0, 'slope': 1.74, 'intercept': 42.36}, {'code': '601003', 'name': '柳钢股份', 'value': 0.91, 'R_Square': 0.0, 'slope': 1.23, 'intercept': 51.61}]
