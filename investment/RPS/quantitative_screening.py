# encoding: utf-8
# 量化选股流程  思路来源: 陶博士
import copy
import os
import pandas as pd
import tushare as ts
from datetime import date, timedelta
import logging
from momentum import NEW_STOCK_LIST
from RPS.foreign_capital_increase import foreign_capital_filter, foreignCapitalHoldingV2
from security import get_interval_yield, get_stock_kline_with_volume

pro = ts.pro_api("b625f0b90069039346d199aa3c0d5bc53fd47212437337b45ba87487")


def get_fund_holdings(quarter, year=date.today().year):
    # 基金持股
    from RPS.bak_stock_pool import fund_pool as pool
    return pool
    logging.warning("查询基金持股数据")
    pool = set()
    data = ts.fund_holdings(year=year, quarter=quarter)
    for i in data.values:
        code = i[7]
        name = i[3]
        fundHoldingdRatio = float(i[6])
        if fundHoldingdRatio >= 3:
            pool.add((code, name))
    logging.warning(f"机构持股: {pool}")
    return pool


def get_RPS_stock_pool():
    # 根据RPS值进行第一步筛选
    os.chdir("../RPS")
    logging.warning("根据RPS查询股池")
    pool = set()
    files = ['RPS_50_V2.csv', 'RPS_120_V2.csv', 'RPS_250_V2.csv']
    for file in files:
        df = pd.read_csv(file, encoding='utf-8')
        for i in df.values:
            if i[-1] >= 90:
                pool.add((i[0].split('.')[0], i[1]))
    logging.warning(f"高RPS股票池:\t{len(pool)}\t{pool}")
    return pool


def get_all_RPS_stock_pool(days=None):
    # 根据RPS值进行第一步筛选
    os.chdir("../RPS")
    pool = set()
    if not days:
        files = ['RPS_20_V2.csv', 'RPS_50_V2.csv', 'RPS_120_V2.csv', 'RPS_250_V2.csv']
    else:
        files = [f"RPS_{i}_V2.csv" for i in days]
    for file in files:
        df = pd.read_csv(file, encoding='utf-8')
        for i in df.values:
            if i[-1] >= 85:
                pool.add((i[0].split('.')[0], i[1]))
    pool2 = []
    for i in pool:
        pool2.append({'code': i[0], 'name': i[1]})
    logging.warning(f"高RPS股票池:\t{len(pool)}\t{pool}")
    return pool2


def get_close(code):
    # 按照日期范围获取股票交易日期,收盘价
    start = int(str(date.today() - timedelta(days=365)).replace('-', ''))
    end = int(str(date.today()).replace('-', ''))
    df = pro.daily(ts_code=code, start_date=start, end_date=end, fields='trade_date,close')
    # 将交易日期设置为索引值
    df.index = pd.to_datetime(df.trade_date)
    df = df.sort_index()
    closes = []
    [closes.append(i[1]) for i in df.values]
    if len(closes) < 1:
        logging.error(code, closes)
    close = closes[-1]
    highest = max(closes[:-1])
    momentum = round(close / highest, 3)
    interval_yield = round((closes[-1] - closes[0]) / closes[0] * 100, 2)
    return {'code': code, 'interval_yield': interval_yield, 'momentum': momentum}


def close_one_year_high(pool):
    # 接近一年新高
    logging.warning("股价接近一年新高")
    result = []
    for i in pool:
        data = get_interval_yield(i['code'])
        if data['momentum'] > 0.9:
            result.append(i)
    return result


def stock_pool_filter_process():
    rps_pool = get_RPS_stock_pool()     # 股价相对强度RPS优先一切
    fund_pool = get_fund_holdings(quarter=2)
    foreign_capital_pool = foreignCapitalHoldingV2()
    pool = fund_pool.union(foreign_capital_pool)    # 基金持股3% + 北向持股三千万
    pool = [i for i in pool if i in rps_pool]
    pool = [{'code': i[0], 'name': i[1]} for i in pool]
    logging.warning(f"基金持股3% + 北向持股三千万: {pool}")
    fc_add = foreign_capital_filter()  # 外资增仓
    pool = [i for i in pool if i in fc_add]
    logging.warning(f"外资最近一个月增持超过一亿或1%流通股: {pool}")
    pool = close_one_year_high(pool)    # 股价接近一年新高
    logging.warning(f"基金持股3% + 北向持股三千万 + 外资增持 + 股价接近一年新高: {pool}")
    return pool


def institutions_holding_rps_stock():
    # 中长期高RPS且机构持股
    rps_pool = get_RPS_stock_pool()
    fund_pool = get_fund_holdings(quarter=3)
    foreign_capital_pool = foreignCapitalHoldingV2()
    pool = fund_pool.union(foreign_capital_pool)
    pool = [i for i in pool if i in rps_pool]
    pool = [{'code': i[0], 'name': i[1]} for i in pool]
    logging.warning(f"中长期高RPS且机构持股:\t{len(pool)}\t{pool}")
    return pool


def institutions_holding_rps_stock_short():
    # 短期高RPS&机构外资持股
    file = "../RPS/RPS_20_V2.csv"
    rps_pool = set()
    df = pd.read_csv(file, encoding='utf-8')
    for i in df.values:
        if i[-1] >= 87:
            rps_pool.add((i[0].split('.')[0], i[1]))
    fund_pool = get_fund_holdings(quarter=3)
    foreign_capital_pool = foreignCapitalHoldingV2()
    pool = fund_pool.union(foreign_capital_pool)
    pool = [i for i in pool if i in rps_pool]
    pool = [{'code': i[0], 'name': i[1]} for i in pool]
    logging.warning(f"短期高RPS且机构持股:\t{len(pool)}\t{pool}")
    return pool


def biggest_decline_calc(kline: list):
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
    biggest_decline = round((high - low)/high * 100, 2)
    # logging.warning(f"最高: {high}\t最低: {low}\t当前: {close}\tbiggest_decline: {biggest_decline}")
    return biggest_decline


def select_biggest_decline():
    pool = institutions_holding_rps_stock()
    target = []
    for i in pool:
        data = get_stock_kline_with_volume(i['code'], limit=120)
        close = data[-1]['close']
        max_price = {'day': '', 'high': 0}
        for j in data:
            if j['high'] > max_price['high']:
                max_price['day'] = j['day']
                max_price['high'] = j['high']
        high = max_price['high']
        for j in range(len(data)):
            if max_price['day'] == data[j]['day']:
                data = data[j:]
                break
        low = min([j['low'] for j in data])
        biggest_decline = round((high - low)/high * 100, 2)
        if biggest_decline <= 50:
            target.append({'code': i['code'], 'name': i['name'], 'highest': high, 'lowest': low, 'current_price': close, 'biggest_decline': biggest_decline})
            logging.warning(f"code: {i['code']}\tname: {i['name']}\t最高: {high}\t最低: {low}\t当前: {close}\tbiggest_decline: {biggest_decline}")
    return target


def Daily_New_High():
    # 创新高及接近新高个股查询
    filename = "../RPS/daily_data.csv"
    df = pd.read_csv(filename, encoding="utf-8")
    data = df.columns[1:]
    target, second_target = [], []
    for i in range(len(data)):
        closes = df.iloc[:, i+1].values
        result = {'code': data[i], 'name': "", 'industry': "", 'close': closes[-1], 'max': max(closes)}
        result['name'] = NEW_STOCK_LIST[result['code']]['name']
        result['industry'] = NEW_STOCK_LIST[result['code']]['industry']
        if result['close'] == result['max']:
            target.append(result)
        if result['close'] >= result['max'] * 0.9:
            second_target.append(result)
    logging.warning(f"今日创新高个股数量&详情: {len(target)}\t{target}")
    logging.warning(f"接近一年新高: {len(second_target)}\t{second_target}")
    industries = [i['industry'] for i in target]
    industrySet = set(industries)
    industry_distribution = []
    for i in industrySet:
        industry_distribution.append({'industry': i, 'count': industries.count(i)})
    industry_distribution = sorted(industry_distribution, key=lambda x: x['count'], reverse=True)
    logging.warning(f"创新高行业分布&详情: {industry_distribution}")
    for i in second_target:
        i['code'] = i['code'].split('.')[0]
    return second_target


def institutions_holding_rps_stock_whole_cycle():
    # 长中短期高RPS&机构持股股池
    os.chdir("../RPS")
    file = "RPS_20_V2.csv"
    rps_pool = []
    df = pd.read_csv(file, encoding='utf-8')
    for i in df.values:
        if i[-1] >= 87:
            rps_pool.append({'code': i[0].split('.')[0], 'name': i[1]})
    pool = institutions_holding_rps_stock()
    target = [i for i in pool if i in rps_pool]
    logging.warning(f"长中短期高RPS&机构持股股池:\t{len(target)}\t{target}")
    return target


def institutions_holding():
    fund_pool = get_fund_holdings(quarter=3)
    foreign_pool = foreignCapitalHoldingV2()
    pool = []
    for i in fund_pool.union(foreign_pool):
        pool.append({'code': i[0], 'name': i[1]})
    logging.warning(f"机构&外资持股: {len(pool)}\t{pool}")
    return pool


def select_high_rps_stock(days=None):
    pool = []
    data = get_all_RPS_stock_pool(days)
    for i in data:
        i['code'] = f"{i['code']}.SH" if str(i['code']).startswith('6') else f"{i['code']}.SZ"
        pool.append(i)
    logging.warning(f"高RPS股票池:\t{len(pool)}\t{pool}")
    return pool

