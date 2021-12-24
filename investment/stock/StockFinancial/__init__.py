# 美图模式量化过程 信息来源: 老杜
import copy
import logging
import os
import sys
import time
import json
import pickle
import pandas as pd
import requests
from datetime import date, timedelta
from RPS.stock_pool import STOCK_LIST
from monitor.whole_market import RedisConn
from monitor import get_stock_kline_with_indicators, MA_V2, BooleanLine


def get_research_report(code):
    # 获取个股研报数据
    time.sleep(0.5)
    beginTime = date.today() - timedelta(days=60)
    endTime = date.today()
    timestamp = int(time.time()*1000)
    url = f"http://reportapi.eastmoney.com/report/list?cb=datatable4737182&pageNo=1&pageSize=50&code={code}&industryCode=*&industry=*&rating=*&ratingchange=*&beginTime={beginTime}&endTime={endTime}&fields=&qType=0&_={timestamp}"
    response = requests.get(url)
    response = response.text.replace('datatable4737182', '')
    response = response[1:-1]
    response = json.loads(response)
    if 'data' in response.keys():
        response = response.get('data')
        return response if response else None
    return None


def save_research_report_to_redis():
    # 从东方财富网下载个股机构研报,并以二进制文件保存到本地,建议每周更新一次即可
    target = {}
    count = 1
    client = RedisConn()
    for i in STOCK_LIST:
        code = i['code'].split('.')[0]
        data = get_research_report(code)
        if data:
            print(count, data)
            client.set(f"stock:research:{i['code']}", json.dumps(data))
            count += 1


def read_research_report_from_redis():
    target = {}
    client = RedisConn()
    keys = client.keys(f"stock:research:*")
    for i in keys:
        code = i.decode().split(':')[-1].split('.')[0]
        target[code] = json.loads(client.get(i))
    with open("All_research_report.bin", "wb") as f:
        f.write(pickle.dumps(target))


def read_research_report():
    result = []
    with open("All_research_report.bin", "rb") as f:
        content = f.read()
        content = pickle.loads(content)
        for k, v in content.items():
            result.append({'code': k, 'name': v[0]['stockName']})
    return result


def get_quarter_report(_date=None):
    # 获取上市公司最新季度报告,持续跟踪
    quarter_report_list = {}
    _date = "2021-09-30"
    pageSize = 50
    for pageNumber in range(1, 250):
        timestamp = int(time.time()*1000)
        callback = f"jQuery112307840667802626824_{timestamp}"
        url = f"http://datacenter-web.eastmoney.com/api/data/get?callback={callback}&st=UPDATE_DATE%2CSECURITY_CODE&sr=-1%2C-1&ps={pageSize}&p={pageNumber}&type=RPT_LICO_FN_CPD&sty=ALL&token=894050c76af8597a853f5b408b759f5d&filter=(REPORTDATE%3D%27{_date}%27)"
        response = requests.get(url)
        response = response.text.replace(f"{callback}(", '')[:-2]
        response = json.loads(response)
        if 'result' in response.keys():
            response = response['result']
            if response:
                if 'data' in response.keys():
                    response = response['data']
                    for i in response:
                        if i['SECURITY_CODE'][0] in ('0', '3', '6'):
                            quarter_report_list[i['SECURITY_CODE']] = i
    target_file = f"All_quarter_report.bin"
    if target_file in os.listdir(os.curdir):
        os.remove(target_file)
    with open(target_file, 'wb') as f:
        f.write(pickle.dumps(quarter_report_list))


def read_quarter_report():
    os.chdir("D:/GIT/invest/investment/stock/StockFinancial/")
    result = []
    with open("All_quarter_report.bin", 'rb') as f:
        content = f.read()
        content = pickle.loads(content)
        count = 1
        for code, v in content.items():
            name = v['SECURITY_NAME_ABBR']
            YSTBZZ = v['YSTZ']
            YSHBZZ = v['YSHZ']
            JLRTBZZ = v['SJLTZ']
            JLRHBZZ = v['SJLHZ']
            if YSTBZZ and JLRTBZZ:
                if YSTBZZ > 0 and JLRTBZZ > 0:
                    # logging.warning(f"{count}\tCODE:{code}\t名称:{name}\t营收同比增长:{YSTBZZ}\t营收环比增长:{YSHBZZ}\t净利润同比增长:{JLRTBZZ}\t净利润环比增长:{JLRHBZZ}")
                    result.append({'code': code, 'name': name})
                    count += 1
    return result


def get_rps_stock_list():
    from RPS.stock_pool import NEW_STOCK_LIST
    files = ['../../RPS/RPS_50_V2.csv', '../../RPS/RPS_120_V2.csv', '../../RPS/RPS_250_V2.csv']
    pool = copy.copy(NEW_STOCK_LIST)
    df = pd.read_csv(files[0], encoding="utf-8")
    for i in df.values:
        pool[i[0]]['rps50'] = i[-1]
    df = pd.read_csv(files[1], encoding="utf-8")
    for i in df.values:
        pool[i[0]]['rps120'] = i[-1]
    df = pd.read_csv(files[2], encoding="utf-8")
    for i in df.values:
        pool[i[0]]['rps250'] = i[-1]
        del pool[i[0]]['list_date']
    return pool


def get_rps_by_code(code, pool=None):
    if not pool:
        pool = get_rps_stock_list()
    if '.SZ' not in str(code) or '.SH' not in str(code) and str(code)[0] in ('0', '3', '6'):
        code = f"{code}.SH" if str(code).startswith('6') else f"{code}.SZ"
    return pool[code]


def is_below_longer(kline: list):
    for i in kline:
        if i['low'] < i['ma150'] or i['low'] < i['ma200']:
            return True
    return False


def Trend_Template():
    # 趋势模板(股票魔法师第一部)
    # res = read_research_report()
    req = read_quarter_report()
    pool = [i for i in req]
    client = RedisConn()
    counter = 1
    rps = get_rps_stock_list()
    for i in pool:
        # kline = get_stock_kline_with_indicators(i['code'], limit=250)
        # if kline and len(kline) > 200:
        #     i['kline'] = MA_V2(MA_V2(MA_V2(kline, 50), 150), 200)
        #     client.set(f"stock:daily:{i['code']}", json.dumps(i))
        #     print(counter, i['name'])
        #     counter += 1
        # continue
        # 查询行情数据存储至redis中
        redis_data = client.get(f"stock:daily:{i['code']}")
        if redis_data:
            kline = json.loads(redis_data)['kline']
            highest = max([i['high'] for i in kline])
            lowest = min([i['low'] for i in kline])
            close = kline[-1]['close']
            if close > kline[-1]['ma50'] > kline[-1]['ma150'] > kline[-1]['ma200'] > kline[-20]['ma200']:
                if close > lowest * 1.3 and close > highest * 0.75:
                    i = get_rps_by_code(code=i['code'], pool=rps)
                    logging.warning(f"{counter}\t{i}")
                    counter += 1


def BeautyFigure():
    req = read_quarter_report()
    client = RedisConn()
    counter = 1
    for i in req:
        redis_data = client.get(f"stock:daily:{i['code']}")
        if redis_data:
            kline = json.loads(redis_data)['kline']
            kline = BooleanLine(kline)
            if kline[-1]['BBW'] < 0.2 and is_below_longer(kline[-66:]) and kline[-1]['close'] > kline[-1]['ma150'] > kline[-1]['ma200']:
                logging.warning(f"{counter}\t{i}")
                counter += 1


# BeautyFigure()
# read_quarter_report()
