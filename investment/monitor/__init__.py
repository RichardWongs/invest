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


pool = [{'code': '601117', 'name': '中国化学', 'pe': 10.6, 'peg': 0.31, 'growth': 33.9}, {'code': '601677', 'name': '明泰铝业', 'pe': 12.35, 'peg': 0.34, 'growth': 36.05}, {'code': '600483', 'name': '福能股份', 'pe': 12.16, 'peg': 0.35, 'growth': 34.97}, {'code': '603979', 'name': '金诚信', 'pe': 20.05, 'peg': 0.37, 'growth': 54.31}, {'code': '002149', 'name': '西部材料', 'pe': 34.62, 'peg': 0.37, 'growth': 92.59}, {'code': '300035', 'name': '中科电气', 'pe': 40.86, 'peg': 0.49, 'growth': 83.74}, {'code': '603599', 'name': '广信股份', 'pe': 14.47, 'peg': 0.49, 'growth': 29.65}, {'code': '600438', 'name': '通威股份', 'pe': 22.81, 'peg': 0.49, 'growth': 46.35}, {'code': '688599', 'name': '天合光能', 'pe': 34.77, 'peg': 0.52, 'growth': 66.9}, {'code': '603855', 'name': '华荣股份', 'pe': 16.97, 'peg': 0.53, 'growth': 32.25}, {'code': '002459', 'name': '晶澳科技', 'pe': 32.91, 'peg': 0.55, 'growth': 60.34}, {'code': '601615', 'name': '明阳智能', 'pe': 18.94, 'peg': 0.65, 'growth': 29.15}, {'code': '601618', 'name': '中国中冶', 'pe': 10.56, 'peg': 0.66, 'growth': 15.93}, {'code': '603279', 'name': '景津环保', 'pe': 19.42, 'peg': 0.67, 'growth': 29.06}, {'code': '300031', 'name': '宝通科技', 'pe': 15.22, 'peg': 0.67, 'growth': 22.55}, {'code': '002832', 'name': '比音勒芬', 'pe': 20.09, 'peg': 0.73, 'growth': 27.69}, {'code': '002129', 'name': '中环股份', 'pe': 38.63, 'peg': 0.73, 'growth': 52.67}, {'code': '002080', 'name': '中材科技', 'pe': 19.27, 'peg': 0.76, 'growth': 25.3}, {'code': '688128', 'name': '中国电研', 'pe': 28.1, 'peg': 0.77, 'growth': 36.65}, {'code': '002539', 'name': '云图控股', 'pe': 24.98, 'peg': 0.79, 'growth': 31.48}, {'code': '300223', 'name': '北京君正', 'pe': 63.8, 'peg': 0.83, 'growth': 77.21}, {'code': '688598', 'name': '金博股份', 'pe': 52.35, 'peg': 0.87, 'growth': 59.96}, {'code': '002531', 'name': '天顺风能', 'pe': 21.14, 'peg': 0.88, 'growth': 23.93}, {'code': '601225', 'name': '陕西煤业', 'pe': 8.16, 'peg': 0.9, 'growth': 9.03}, {'code': '688516', 'name': '奥特维', 'pe': 50.91, 'peg': 0.93, 'growth': 54.8}, {'code': '002049', 'name': '紫光国微', 'pe': 55.06, 'peg': 0.93, 'growth': 59.13}, {'code': '002812', 'name': '恩捷股份', 'pe': 75.87, 'peg': 0.99, 'growth': 76.62}]


def BooleanLine_test(code):
    data = get_stock_kline_with_indicators(code, limit=250)
    for i in range(len(data)):
        if 'BBW' in data[i].keys() and i-2 > 20:
            if data[i]['BBW'] > data[i-1]['BBW'] > data[i-2]['BBW']:
                if round(data[i]['close']/data[i-5]['close']-1, 2) > 0.08:
                    print(f"前五天涨幅: {round(data[i]['close']/data[i-5]['close']-1, 2)}\t后二十天涨幅: {round(data[i+20]['close']/data[i]['close']-1, 2)}")
                    print(data[i])


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


def KDJ_test(code):
    data = get_stock_kline_with_indicators(code)
    data = KDJ(data)
    for i in range(len(data)):
        if 'K' in data[i].keys():
            if data[i]['K'] > data[i]['D'] and data[i-1]['K'] < data[i-1]['D']:
                print(data[i])


def EMA(cps, days):
    emas = cps.copy()
    for i in range(len(cps)):
        if i == 0:
            emas[i] = cps[i]
        if i > 0:
            emas[i] = ((days-1)*emas[i-1]+2*cps[i])/(days+1)
    return emas


def WMS(kline):
    pass


def TRIX(data):
    N, M = 12, 20
    closes = [i['close'] for i in data]
    TR = EMA(EMA(EMA(closes, N), N), N)
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
    print(f"R_Square: {round(R_square, 2)}\t斜率: {round(m, 2)}\t截距: {round(b, 2)}")
    return {'R_Square': round(R_square, 2), 'slope': round(m, 2), 'intercept': round(b, 2)}


kline = get_stock_kline_with_indicators('002812', limit=120)
Linear_Regression(kline)


