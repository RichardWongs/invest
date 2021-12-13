import time
import requests
import json
import re
import numpy as np
from datetime import datetime, date, timedelta
from bs4 import BeautifulSoup
from monitor import EMA_V2


def get_html(code, start_date, end_date, page=1, per=20):
    url = 'http://fund.eastmoney.com/f10/F10DataApi.aspx?type=lsjz&code={0}&page={1}&sdate={2}&edate={3}&per={4}'.format(
        code, page, start_date, end_date, per)
    rsp = requests.get(url)
    html = rsp.text
    return html


def get_fund(code, start_date=str(date.today() - timedelta(180)), end_date=str(date.today()), page=1, per=20):
    # time.sleep(3)
    # 获取html
    html = get_html(code, start_date, end_date, page, per)
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
    records = list(reversed(records))
    # print(records)
    record_data = []
    for i in range(len(records)):
        tmp = {}
        tmp['day'] = records[i][0]
        tmp['cumulative_close'] = float(records[i][2])
        tmp['unit_close'] = float(records[i][1])
        if i > 0:
            tmp['last_cumulative_close'] = float(records[i - 1][2])
            tmp['last_unit_close'] = float(records[i - 1][1])
            tmp['applies'] = round(float(records[i][2]) - float(records[i - 1][2]), 4)
            tmp['applies_rate'] = round(
                (float(records[i][2]) - float(records[i - 1][2])) / float(records[i - 1][2]) * 100, 2)
        record_data.append(tmp)
    if len(record_data) > 0:
        del record_data[0]
    record_data = EMA_V2(EMA_V2(record_data, days=50, key="unit_close", out_key=f"ema50_unit_close"), days=150, key="unit_close", out_key="ema150_unit_close")
    record_data = EMA_V2(EMA_V2(record_data, days=50, key="cumulative_close", out_key=f"ema50_cumulative_close"), days=150, key="cumulative_close", out_key="ema150_cumulative_close")
    return record_data


def get_fund_yield(code, year=date.year, quarter=None, month=None):
    # 查询某只基金的阶段收益
    if month in (1, 3, 5, 7, 8, 10, 12):
        end_day = 31
    elif month in (4, 6, 9, 11):
        end_day = 30
    else:
        end_day = 29 if year % 4 == 0 else 28

    if quarter and quarter in (1, 2, 3, 4):
        if quarter == 1:
            start_date = datetime(year, 1, 1).strftime("%Y-%m-%d")
            end_date = datetime(year, 3, 31).strftime("%Y-%m-%d")
        elif quarter == 2:
            start_date = datetime(year, 4, 1).strftime("%Y-%m-%d")
            end_date = datetime(year, 6, 30).strftime("%Y-%m-%d")
        elif quarter == 3:
            start_date = datetime(year, 7, 1).strftime("%Y-%m-%d")
            end_date = datetime(year, 9, 30).strftime("%Y-%m-%d")
        else:
            start_date = datetime(year, 10, 1).strftime("%Y-%m-%d")
            end_date = datetime(year, 12, 31).strftime("%Y-%m-%d")
    elif year and month:
        start_date = datetime(year, month, 1).strftime("%Y-%m-%d")
        end_date = datetime(year, month, end_day).strftime("%Y-%m-%d")
    else:
        start_date = datetime(year-1, 12, 31).strftime("%Y-%m-%d")
        end_date = datetime(year, 12, 31).strftime("%Y-%m-%d")
    data = get_fund(code, start_date, end_date)
    if data:
        unit_yield = round((data[-1]['unit_close']-data[0]['last_unit_close'])/data[0]['last_unit_close']*100, 2)
        cumulative_yield = round((data[-1]['cumulative_close']-data[0]['last_cumulative_close'])/data[0]['last_cumulative_close']*100, 2)
        yields = unit_yield if unit_yield > cumulative_yield else cumulative_yield
        return yields
    else:
        return None


def get_fund_year_yield(code, years=3):
    # 查询某只基金N年以来的总收益
    year, month, day = datetime.today().year, datetime.today().month, datetime.today().day
    start_date = str(datetime(year-years, month, day))
    end_date = str(datetime.today())
    data = get_fund(code, start_date, end_date)
    if data:
        unit_yield = round((data[-1]['unit_close']-data[0]['last_unit_close'])/data[0]['last_unit_close']*100, 2)
        cumulative_yield = round((data[-1]['cumulative_close']-data[0]['last_cumulative_close'])/data[0]['last_cumulative_close']*100, 2)
        yields = unit_yield if unit_yield > cumulative_yield else cumulative_yield
        return yields
    else:
        return None


def get_all_fund_list():
    url = "http://fund.eastmoney.com/js/fundcode_search.js"
    response = requests.get(url)
    response = response.text.split("=")[1].replace(';', '')
    response = json.loads(response)
    # print(response)
    funds = []
    for i in response:
        tmp = {'code': i[0], 'name': i[2], 'type': i[3]}
        funds.append(tmp)
    return funds



