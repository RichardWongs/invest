import os
import time
import requests
import json
import pickle
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
    target_file = f"dividend/{_date}.bin"
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


stocks = {}
for i in share_pool:
    stocks[i] = []
files = ["2020-03-31", "2020-06-30", "2020-09-30", "2020-12-31"]
for file in files:
    with open(f"dividend/{file}.bin", 'rb') as f:
        f = f.read()
        content = pickle.loads(f)
    for k, v in content.items():
        stocks[k].append(v)
for k, v in stocks.items():
    if v and len(v) > 1:
        # print(k, v)
        print(len(v))
