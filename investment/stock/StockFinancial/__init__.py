import logging
import os
import time
import json
import pickle
import requests
from datetime import date, timedelta
from RPS.stock_pool import STOCK_LIST
from monitor.whole_market import RedisConn


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


res = read_research_report()
req = read_quarter_report()
target = [i for i in req if i in res]
print(len(target), target)


