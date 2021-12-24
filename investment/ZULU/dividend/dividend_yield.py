import copy
import logging
import os
import time
import requests
import json
import pickle
from parse import *
from ZULU import share_pool


def get_quarter_report(_date):
    # 获取上市公司最新季度报告,持续跟踪
    quarter_report_list = {}
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
                            if i['ASSIGNDSCRPT'] and i['ASSIGNDSCRPT'] != "不分配不转增":
                                quarter_report_list[i['SECURITY_CODE']] = i
                                print(i)
    target_file = f"{_date}.bin"
    if target_file in os.listdir(os.curdir):
        os.remove(target_file)
    with open(target_file, 'wb') as f:
        f.write(pickle.dumps(quarter_report_list))
    return quarter_report_list


def get_current_year_all_quarter_report(year):
    date_list = [f"{year}-03-31", f"{year}-06-30", f"{year}-09-30", f"{year}-12-31"]
    for _date in date_list:
        time.sleep(5)
        get_quarter_report(_date)


def get_stock_share_out_bonus():
    # 获取该年度个股的分红派息信息
    stocks = {}
    target = []
    for i in share_pool:
        stocks[i] = {2016: [], 2017: [], 2018: [], 2019: [], 2020: [], }
    years = [2016, 2017, 2018, 2019, 2020]
    for year in years:
        files = [f"{year}-03-31", f"{year}-06-30", f"{year}-09-30", f"{year}-12-31"]
        for file in files:
            with open(f"{file}.bin", 'rb') as f:
                f = f.read()
                content = pickle.loads(f)
                for k, v in content.items():
                    stocks[k][year].append(v)
    stocks_bak = copy.copy(stocks)
    for k, v in stocks.items():
        if not (v[2016] and v[2017] and v[2018] and v[2019] and v[2020]):
            del stocks_bak[k]
    for k, v in stocks_bak.items():
        target.append({'code': k, 'name': v[2020][0]['SECURITY_NAME_ABBR']})
    return target


def extract_dividend_detail(s: str):
    sendCount = 0
    turnCount = 0
    cash = 0
    if "送" in s:
        profile = search("送{send:f}", s)
        sendCount = profile["send"]
    if "转" in s:
        profile = search("转{turn:f}", s)
        turnCount = profile["turn"]
    if "派" in s:
        profile = search("派{dividend:f}", s)
        cash = profile["dividend"]
    logging.warning(f"送股:{sendCount}\t转股:{turnCount}\t派息:{cash}")
    return {'sendCount': sendCount, 'turnCount': turnCount, 'cash': cash}


def get_dividend_by_code(code):
    os.chdir("D:/GIT/invest/investment/ZULU/dividend/")
    code = str(code).split('.')[0]
    files = ['2020-03-31.bin', '2020-06-30.bin', '2020-09-30.bin', '2020-12-31.bin']
    target = []
    for file in files:
        with open(file, 'rb') as f:
            content = pickle.loads(f.read())
            if code in content.keys():
                target.append(content[code])
    return target


stocks = get_stock_share_out_bonus()
for i in stocks[:10]:
    print(get_dividend_by_code(i['code']))

