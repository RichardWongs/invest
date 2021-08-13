# 导入需要的模块
import json

import requests
from datetime import date,datetime,timedelta
from bs4 import BeautifulSoup
import re
import math
import numpy as np
import os
os.chdir(__file__.replace("fund.py", ''))


def write_file(content):
    filename = __file__.replace('.py', '.log')
    with open(filename, 'a', encoding="utf-8") as f:
        f.write(content)


def get_html(code, start_date, end_date, page=1, per=20):
    url = 'http://fund.eastmoney.com/f10/F10DataApi.aspx?type=lsjz&code={0}&page={1}&sdate={2}&edate={3}&per={4}'.format(
        code, page, start_date, end_date, per)
    rsp = requests.get(url)
    html = rsp.text
    return html
 
 
def get_fund(code, start_date=str(date.today()-timedelta(30)), end_date=str(date.today()), page=1, per=20):
    # 获取html
    html = get_html(code, start_date, end_date, page, per)
    print(html)
    soup = BeautifulSoup(html, 'html.parser')
    # 获取总页数
    pattern = re.compile('pages:(.*),')
    result = re.search(pattern, html).group(1)
    total_page = int(result)
    # 获取表头信息
    heads = []
    for head in soup.findAll("th"):
        heads.append(head.contents[0])
 
    # 数据存取列表
    records = []
    # 获取每一页的数据
    current_page = 1
    while current_page <= total_page:
        html = get_html(code, start_date, end_date, current_page, per)
        soup = BeautifulSoup(html, 'html.parser')
        # 获取数据
        for row in soup.findAll("tbody")[0].findAll("tr"):
            row_records = []
            for record in row.findAll('td'):
                val = record.contents
                # 处理空值
                if val == []:
                    row_records.append(np.nan)
                else:
                    row_records.append(val[0])
            # 记录数据
            records.append(row_records)
        # 下一页
        current_page = current_page + 1
 
    record_data = []
    for record in records:
        # print(record[3].replace("%", ""))
        record_data.append(record[3].replace("%", ""))
    return list(reversed([float(i) for i in record_data]))


def get_style_index(index_code):
    url = f"http://hq.cnindex.com.cn/market/market/getIndexDailyDataWithDataFormat"
    begin_time = date.today() - timedelta(days=30)
    end_time = date.today()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36"
    }
    params = {
        "indexCode": index_code,
        "startDate": begin_time,
        "endDate": end_time,
        "frequency": "day"
    }
    response = requests.get(url,headers=headers, params=params).json()
    data = response.get("data").get("data")
    records_data = []
    for i in data:
        records_data.append(float(i[7].replace("%", "")))
    records_data = list(reversed(records_data))
    return records_data


def output_six_style_index_info(fund_code, fund_name=None):
    index_detail = {
        "大盘成长": {
            "code": 399372,
            "name": "大盘成长",
            "30_days_applies": []
        },
        "大盘价值": {
            "code": 399373,
            "name": "大盘价值",
            "30_days_applies": []
        },
        "中盘成长": {
            "code": 399374,
            "name": "中盘成长",
            "30_days_applies": []
        },
        "中盘价值": {
            "code": 399375,
            "name": "中盘价值",
            "30_days_applies": []
        },
        "小盘成长": {
            "code": 399376,
            "name": "小盘成长",
            "30_days_applies": []
        },
        "小盘价值": {
            "code": 399377,
            "name": "小盘价值",
            "30_days_applies": []
        }
    }
    for k,v in index_detail.items():
        code = v.get("code")
        v["30_days_applies"] = get_style_index(code)
        # print(k, v)
    fund_applies = get_fund(fund_code)
    print(f"{fund_name} 风格相关系数")
    for k, v in index_detail.items():
        print(k, round(correlation(fund_applies, v.get("30_days_applies")), 2))
    return index_detail


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


def get_all_fund_list():
    url = "http://fund.eastmoney.com/js/fundcode_search.js"
    response = requests.get(url)
    response = response.text.split("=")[1].replace(';', '')
    response = json.loads(response)
    funds = []
    for i in response:
        if i[3] in ('混合型', '股票型'):
            tmp = {}
            tmp['code'] = i[0]
            tmp['name'] = i[2]
            funds.append(tmp)
    return funds



if __name__ == '__main__':
    get_all_fund_list()
