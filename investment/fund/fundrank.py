# encoding: utf-8
# 基金业绩排名
import json
import requests
from datetime import date, timedelta
from fundresults import get_fund_yield, get_fund_year_yield


def get_fund_rank(sort):
    url = f"https://api.doctorxiong.club/v1/fund/rank"
    headers = {
        'Content-Type': 'application/json'
    }
    body = {
        'sort': sort,
        'fundType': ['gp', 'hh'],
        'pageIndex': 1,
        'pageSize': 500
    }
    response = requests.post(url, json=body).json()
    return response['data']['rank']


def get_all_funds():
    url = f"https://api.doctorxiong.club/v1/fund/all"
    response = requests.get(url).json()
    print(len(response['data']))


def get_fund_detail(code, start_date, end_date):
    url = "https://api.doctorxiong.club/v1/fund/detail"
    params = {
        'code': code,
        'startDate': start_date,
        'endDate': end_date
    }
    response = requests.get(url, params=params).json()
    response = response['data']
    print(json.dumps(response, indent=4, ensure_ascii=False))


def get_fund_detail_list(fund_list: list, start_date=date.today()-timedelta(days=1), end_date=date.today()):
    # 批量获取基金详情
    code = ",".join([i['code'] for i in fund_list])
    url = "https://api.doctorxiong.club/v1/fund/detail/list"
    params = {
        'code': code,
        'startDate': start_date,
        'endDate': end_date
    }
    response = requests.get(url, params=params).json()
    response = response['data']
    result = [{'code': i['code'], 'name': i['name'], 'fundScale': i['fundScale']} for i in response]
    for i in fund_list:
        for j in result:
            if i['code'] == j['code']:
                i['fundScale'] = j['fundScale']
    return fund_list


def fund_ranking_summary():
    # 基金业绩排行汇总
    # data_3m = get_fund_rank('3y')
    # data_6m = get_fund_rank('6y')
    data_1y = get_fund_rank('1n')
    data_2y = get_fund_rank('2n')
    data_3y = get_fund_rank('3n')
    data_5y = get_fund_rank('5n')
    # t1 = data_6m  # [i for i in data_6m if i in data_3m]
    t2 = [i for i in data_2y if i in data_1y]
    t3 = [i for i in data_5y if i in data_3y]
    target = [i for i in t2 if i in t3]
    # target = [i for i in t1 if i in [i for i in t3 if i in t2]]
    for i in target:
        del i['netWorthDate']
        del i['netWorth']
        del i['dayGrowth']
        del i['fundType']
        del i['expectWorthDate']
        del i['expectWorth']
        del i['expectGrowth']
        del i['lastWeekGrowth']
        del i['lastMonthGrowth']
        del i['lastThreeMonthsGrowth']
        del i['lastSixMonthsGrowth']
    print(f"target: {target}")
    years = (2016, 2017, 2018, 2019, 2020, 2021)
    data = []
    for fund in target:
        tmp = {'code': fund['code'], 'name': fund['name']}
        for y in years:
            tmp[y] = get_fund_yield(code=tmp['code'], year=y)
        tmp['3y'] = get_fund_year_yield(tmp['code'], 3)
        tmp['5y'] = get_fund_year_yield(tmp['code'], 5)
        data.append(tmp), print(tmp)
    return data


# print(fund_ranking_summary())


