# encoding: utf-8
import logging
import pickle
import time
import json
import redis
import requests
from RPS.RPS_DATA import pro
from monitor import EMA_V2, BooleanLine, Linear_Regression
from RPS.stock_pool import STOCK_LIST


def RedisConn():
    client = redis.Redis(host="192.168.124.20", port=6379, db=0)
    return client


class SecurityException(BaseException):
    pass


def get_stock_kline_with_indicators(code, is_index=False, period=101, limit=120):
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
                # new_data = {}
                for i in r:
                    i = {'day': i[0], 'open': float(i[1]), 'close': float(i[2]),
                         'high': float(i[3]), 'low': float(i[4]), 'VOL': int(i[5]),
                         'volume': float(i[6]), 'applies': float(i[8])}
                    new_data.append(i)
                    # new_data[i['day'].replace('-', '')] = i
                return new_data
    except SecurityException() as e:
        print(e)
        return None


def get_benchmark():
    # 获取业绩基准 年&月
    weeks = 53
    logging.warning("查询指数基准...")
    benchmark, benchmark_month = 0, 0
    for index_code in ['399006', '399300', '399905', '000016']:
        index_data = get_stock_kline_with_indicators(index_code, is_index=True, period=102, limit=120)
        index_yield = round((index_data[-1]['close'] - index_data[-weeks]['close']) / index_data[-weeks]['close'] * 100, 2)
        index_month_yield = round((index_data[-1]['close'] - index_data[-5]['close']) / index_data[-5]['close'] * 100,
                                  2)
        if index_yield > benchmark:
            benchmark = index_yield
        if index_month_yield > benchmark_month:
            benchmark_month = index_month_yield
    logging.warning(f"52周涨幅: {benchmark}\t月涨幅: {benchmark_month}")
    return benchmark, benchmark_month


def select_whole_market_stock():
    df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,industry,list_date')
    codes = df.ts_code.values
    names = df.name.values
    industrys = df.industry.values
    stock_list = []
    for code, name, industry in zip(codes, names, industrys):
        tmp = {'code': code, 'name': name, 'industry': industry}
        stock_list.append(tmp)
    return stock_list


def save_whole_market_data_to_redis():
    result = {}
    counter = 0
    client = RedisConn()
    for i in STOCK_LIST[4000:]:
        counter += 1
        print(i, counter)
        code = i['code'].split('.')[0]
        data = get_stock_kline_with_indicators(code, period=102, limit=120)
        tmp = {'code': code, 'name': i['name'], 'industry': i['industry'], 'kline': data}
        result[code] = tmp
        client.set(f"stock:weekly:{code}", json.dumps(tmp))


def save_market_data_from_redis():
    filename = "weekly_kline.bin"
    with open(filename, 'wb') as f:
        klines = []
        client = RedisConn()
        keys = client.keys("stock:weekly:*")
        for k in keys:
            data = client.get(k).decode()
            data = json.loads(data)
            if not data['kline']:
                print(data['code'])
                continue
            data['kline'] = EMA_V2(EMA_V2(data['kline'], days=10), days=30)
            klines.append(data)
        f.write(pickle.dumps(klines))


def read_weekly_kline():
    weeks = 53
    target = []
    with open("weekly_kline.bin", 'rb') as f:
        content = f.read()
        content = pickle.loads(content)
        counter = 1
        benchmark, month_benchmark = get_benchmark()
        for i in content:
            kline = WeekVolumeCalc(i['kline'])
            if len(kline) >= weeks:
                stock_year_applies = round((kline[-1]["close"] - kline[-weeks]['close']) / kline[-weeks]['close'] * 100, 2)
                # stock_month_applies = round((kline[-1]["close"] - kline[-5]['close']) / kline[-5]['close'] * 100, 2)
                if stock_year_applies >= benchmark:  # and stock_month_applies >= month_benchmark:
                    if kline[-1]['close'] > kline[-1]['ema30'] > kline[-2]['ema30']:
                        # kline = BooleanLine(kline)
                        # if kline[-1]["BBW"] > kline[-2]['BBW'] >= kline[-3]['BBW']:
                        # i['kline'] = kline[-1]
                        # print(f"{counter}\t年涨幅:{stock_year_applies}\t{i}")
                        counter += 1
                        target.append(i)
    return target


def read_monthly_kline(month):
    with open("monthly_kline.bin", 'rb') as f:
        content = f.read()
    content = pickle.loads(content)
    counter = 1
    result = []
    for i in content:
        if month in i['kline'].keys():
            result.append({'code': i['code'], 'name': i['name'], 'volume': i["kline"][month]["volume"]})
            counter += 1
    result = sorted(result, key=lambda x: x['volume'], reverse=True)
    return result


def VolumeStatistical(month):
    data = read_monthly_kline(month=month)
    totalVolume = sum([i['volume'] for i in data])
    topCount = int(len(data)*0.05)
    topCountVolume = sum([i['volume'] for i in data[:topCount]])
    topCountStock = [i['name'] for i in data[:topCount]]
    logging.warning(f"日期: {month}\t全市场总成交量: {totalVolume}\t成交量前5%个股总成交量: {topCountVolume}\t成交量占比: {round(topCountVolume/totalVolume, 2)}\t{len(topCountStock)}\t{topCountStock}")


def WeekVolumeCalc(kline: list, N=10):
    for i in range(len(kline)):
        if i > N:
            tenth_volume = []
            for j in range(i-1, i-(N+1), -1):
                tenth_volume.append(kline[j]['volume'])
            kline[i]['10th_largest'] = max(tenth_volume)
            kline[i]['10th_minimum'] = min(tenth_volume)
            kline[i]['avg_volume'] = sum(tenth_volume) / len(tenth_volume)
            kline[i]['volume_ratio'] = round(kline[i]['volume'] / kline[i]['avg_volume'], 2)
    return kline


def weekly_liner_regression():
    # 使用线性回归函数查询个股周K数据
    weeks = 53
    target = []
    with open("weekly_kline.bin", 'rb') as f:
        content = f.read()
        content = pickle.loads(content)
        benchmark, month_benchmark = get_benchmark()
        for i in content:
            if len(i['kline']) >= weeks:
                kline = EMA_V2(EMA_V2(i['kline'], 5), 10)
                stock_year_applies = round((kline[-1]["close"] - kline[-weeks]['close']) / kline[-weeks]['close'] * 100, 2)
                if stock_year_applies >= benchmark:
                    lr = Linear_Regression(kline[-8:], key="ema10")
                    i['R_Square'], i['slope'], i['intercept'] = lr['R_Square'], lr['slope'], lr['intercept']
                    i['src'] = [i['ema5'] for i in kline[-8:]]
                    i['kline'] = i['kline'][-1]
                    if i['slope'] > 0 and i['R_Square'] > 0.8:
                        target.append(i)
    return sorted(target, key=lambda x: x['R_Square'], reverse=True)


if __name__ == "__main__":
    # save_whole_market_data_to_redis()
    save_market_data_from_redis()
