# encoding: utf-8
# 外资增持或新进的个股查询
import os
import time
import requests
import json
from bs4 import BeautifulSoup
from datetime import date, timedelta
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from security.stock_pool import whole_pool
import opencc
import logging
import tushare as ts

cc = opencc.OpenCC('t2s')
chrome_options = Options()
chrome_options.add_argument("--headless")
pro = ts.pro_api("b625f0b90069039346d199aa3c0d5bc53fd47212437337b45ba87487")


def foreignCapitalHoldingV2():
    # 外资持股清单(持股市值超过3000万)
    from RPS.bak_stock_pool import foreign_capital_pool
    return foreign_capital_pool
    logging.warning("查询外资持股数据")
    pageSize = 500
    timestamp = int(time.time()*1000)
    day = get_recent_trade_date(day=date.today()-timedelta(days=1))
    response_list = []
    for pageNumber in range(1, 6):
        url = f"http://datacenter-web.eastmoney.com/api/data/v1/get?callback=jQuery112308889432631368941_{timestamp}&sortColumns=ADD_MARKET_CAP&sortTypes=-1&pageSize={pageSize}&pageNumber={pageNumber}&reportName=RPT_MUTUAL_STOCK_NORTHSTA&columns=ALL&source=WEB&client=WEB&filter=(TRADE_DATE%3D%27{day}%27)(INTERVAL_TYPE%3D%221%22)"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36"
        }
        r = requests.get(url, headers=headers)
        response = r.text.split('(')[1].split(')')[0]
        response = json.loads(response)
        if response:
            if response.get('result'):
                response = response.get('result').get('data')
                response = sorted(response, key=lambda x: x['HOLD_MARKET_CAP'], reverse=True)
                response_list += response
    foreignCapital_pool = set()
    for i in response_list:
        code = i.get('SECURITY_CODE')
        name = i.get('SECURITY_NAME')
        holding_market_value = i.get('HOLD_MARKET_CAP')
        if holding_market_value > 0.3:
            foreignCapital_pool.add((code, name))
    logging.warning(f"东方财富查询外资持仓: {foreignCapital_pool}")
    return foreignCapital_pool


def query_share_capital():
    # 查询外资持股的股价和流通股本
    pageSize = 500
    timestamp = int(time.time()*1000)
    day = get_recent_trade_date(day=date.today()-timedelta(days=1))
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36"
    }
    response_list = []
    for pageNumber in range(1, 6):
        url = f"http://datacenter-web.eastmoney.com/api/data/v1/get?callback=jQuery112308889432631368941_{timestamp}&sortColumns=ADD_MARKET_CAP&sortTypes=-1&pageSize={pageSize}&pageNumber={pageNumber}&reportName=RPT_MUTUAL_STOCK_NORTHSTA&columns=ALL&source=WEB&client=WEB&filter=(TRADE_DATE%3D%27{day}%27)(INTERVAL_TYPE%3D%221%22)"
        r = requests.get(url, headers=headers)
        # print(r.text)
        response = r.text.split('(')[1].split(')')[0]
        response = json.loads(response)
        if response:
            if response.get('result'):
                response = response.get('result').get('data')
                response_list += response
    foreign_capital_pool = []
    for i in response_list:
        code = i.get('SECURITY_CODE')
        name = i.get('SECURITY_NAME')
        price = i.get('CLOSE_PRICE')
        share_rate = i.get('FREE_SHARES_RATIO')
        hold_count = i.get('HOLD_SHARES') * 10000
        share_capital = int(hold_count / share_rate * 100)
        tmp = {
            'code': code,
            'name': name,
            'price': price,
            'share_capital': share_capital
        }
        foreign_capital_pool.append(tmp)
    return foreign_capital_pool


def get_foreign_capital_history_holding(exchange, holding_date=date.today()):
    month = holding_date.month
    day = holding_date.day
    logging.warning(
        f"爬取外资持股数据...\texchange:{exchange}\tholding_date:{holding_date}")
    base_url = f"https://www.hkexnews.hk/sdw/search/mutualmarket_c.aspx?t={exchange}"
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(base_url)
    driver.find_element_by_id("txtShareholdingDate").click()
    driver.find_element_by_xpath(
        '//*[@id="date-picker"]/div[1]/b[1]/ul/li[1]/button').click()
    driver.find_element_by_xpath(
        f'//*[@id="date-picker"]/div[1]/b[2]/ul/li[{month}]/button').click()
    driver.find_element_by_xpath(
        f'//*[@id="date-picker"]/div[1]/b[3]/ul/li[{day}]/button').click()
    driver.find_element_by_id("btnSearch").click()
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser').select(
        'div[class="mobile-list-body"]')
    data = [i.text for i in soup]
    driver.close()
    fc_data = []
    for code, name, count in zip(range(0, len(data), 4), range(
            1, len(data), 4), range(2, len(data), 4)):
        tmp = {
            'code': data[code], 'name': cc.convert(
                data[name]), 'holdingCount': int(
                data[count].replace(
                    ',', ''))}
        fc_data.append(tmp)
    for i in whole_pool:
        for j in fc_data:
            if i['name'] == j['name']:
                j['code'] = i['code']
    return fc_data


def FC_history_Query(holding_date):
    # 外资历史持股数据查询
    exchanges = ['sh', 'sz']
    fc_total = []
    logging.warning(f"外资持仓记录查询")
    for i in exchanges:
        data = get_foreign_capital_history_holding(
            exchange=i, holding_date=holding_date)
        fc_total += data
    return fc_total


def foreign_capital_add_weight(start_date=date.today()-timedelta(days=30), end_date=date.today()):
    # 外资最近一个月加仓或新进的个股
    history_data = FC_history_Query(start_date)
    new_data = FC_history_Query(end_date)
    result = []
    logging.warning(f"查询外资加仓或新进的个股")
    for i in new_data:
        for j in history_data:
            if i['code'] == j['code']:
                if i['holdingCount'] > j['holdingCount']:
                    i['addCount'] = i['holdingCount'] - j['holdingCount']
                    result.append(i)
    history_codes = [i['code'] for i in history_data]
    for i in new_data:
        if i['code'] not in history_codes:
            i['addCount'] = i['holdingCount']
            result.append(i)
    for i in result:
        i['code'] = i['code'].split('.')[0]
    return result


def foreign_capital_filter():
    data = query_share_capital()
    new_data = foreign_capital_add_weight()
    result = []
    for i in new_data:
        for j in data:
            if i['code'] == j['code']:
                i['add_rate'] = round(
                    i['addCount'] / j['share_capital'] * 100, 2)
                i['add_value'] = int(i['addCount'] * j['price'] / 10000)
                if i['add_rate'] >= 1 or i['add_value'] >= 10000:
                    # if i['add_value'] >= 5000:
                    result.append({'code': i['code'], 'name': i['name']})
                    # result.append(i)
    logging.warning(f"外资增持: {result}")
    return result


def get_recent_trade_date(day=date.today()):
    # 返回最近一个交易日
    if day.weekday() in (0, 1, 2, 3, 4):
        return day
    else:
        return get_recent_trade_date(day-timedelta(days=1))


def latest_week_foreign_capital_add_weight():
    # 从最近一周外资增仓或新进的个股(增持金额大于5千万)中挑选出高RPS, 股价接近一年新高的标的
    from security import get_price
    from RPS.quantitative_screening import get_RPS_stock_pool
    new_date = get_recent_trade_date()
    history_date = new_date - timedelta(days=7)
    history_data = FC_history_Query(history_date)
    new_data = FC_history_Query(new_date)
    result = []
    for i in new_data:
        for j in history_data:
            if i['code'] == j['code']:
                if i['holdingCount'] > j['holdingCount']:
                    i['addCount'] = i['holdingCount'] - j['holdingCount']
                    result.append(i)
    history_codes = [i['code'] for i in history_data]
    for i in new_data:
        if i['code'] not in history_codes:
            i['addCount'] = i['holdingCount']
            result.append(i)
    for i in result:
        i['code'] = i['code'].split('.')[0]
    rps_pool = get_RPS_stock_pool()
    rps_codes = [i[0] for i in rps_pool]
    pool = []
    for i in result:
        if i['code'] in rps_codes:
            pool.append(i)
    new_pool = []
    for i in pool:
        current_price, momentum = get_price(i['code'])
        i['addAmount'] = round(i['addCount'] * current_price / 100000000, 2)
        del i['holdingCount']
        del i['addCount']
        if i['addAmount'] >= 0.5 and momentum > 0.9:
            new_pool.append(i)
    sorted_pool = sorted(new_pool, key=lambda x: x['addAmount'], reverse=True)
    logging.warning(f"最近一周外资增持股池: {pool}")
    return sorted_pool


def foreign_capital_continuous_increase():
    # 近五个交易日外资持续增持
    day1 = get_recent_trade_date()-timedelta(days=1)
    day2 = get_recent_trade_date(day1-timedelta(days=1))
    day3 = get_recent_trade_date(day2-timedelta(days=1))
    day4 = get_recent_trade_date(day3-timedelta(days=1))
    day5 = get_recent_trade_date(day4-timedelta(days=1))
    day6 = get_recent_trade_date(day5-timedelta(days=1))
    data = foreign_capital_add_weight(start_date=day2, end_date=day1)
    print(f"{day2}-->{day1}\t{data}")
    data1 = foreign_capital_add_weight(start_date=day3, end_date=day2)
    print(f"{day3}-->{day2}\t{data1}")
    data2 = foreign_capital_add_weight(start_date=day4, end_date=day3)
    print(f"{day4}-->{day3}\t{data2}")
    data3 = foreign_capital_add_weight(start_date=day5, end_date=day4)
    print(f"{day5}-->{day4}\t{data3}")
    data4 = foreign_capital_add_weight(start_date=day6, end_date=day5)
    print(f"{day6}-->{day5}\t{data4}")
    add_dict = {}
    for i in data + data1 + data2 + data3 + data4:
        if i['code'] not in add_dict.keys():
            add_dict[i['code']] = {'code': i['code'], 'name': i['name'], 'addCount': i['addCount'], 'addTimes': 0}
        else:
            add_dict[i['code']]['addCount'] += i['addCount']
    add_list = [i['code'] for i in data] + [i['code'] for i in data1] + [i['code'] for i in data2] + [i['code'] for i in data3] + [i['code'] for i in data4]
    add_set = set(add_list)
    for i in add_set:
        # print(f"{i}--> {add_list.count(i)}")
        add_dict[i]['addTimes'] = add_list.count(i)
        # if add_dict[i]['addTimes'] >= 3:
        #     print(add_dict[i])
    print(add_dict)


# foreign_capital_continuous_increase()

