# encoding: utf-8
import logging
import time
import pickle
import requests
import json
from datetime import date, timedelta
from security import get_stock_kline_with_volume
from ZULU import share_pool


def get_research_report(code):
    # 获取个股研报数据
    # time.sleep(2)
    beginTime = date.today() - timedelta(days=60)
    endTime = date.today()
    timestamp = int(time.time()*1000)
    url = f"http://reportapi.eastmoney.com/report/list?cb=datatable4737182&pageNo=1&pageSize=50&code={code}&industryCode=*&industry=*&rating=*&ratingchange=*&beginTime={beginTime}&endTime={endTime}&fields=&qType=0&_={timestamp}"
    response = requests.get(url)
    # print(response.text)
    response = response.text.replace('datatable4737182', '')
    response = response[1:-1]
    response = json.loads(response)
    if 'data' in response.keys():
        response = response.get('data')
        return response
    return None


def get_predict_eps(code):
    # 根据研报预测计算今明两年的归母净利润
    if share_pool.get(str(code)):
        total_share = share_pool.get(str(code)).get('total_share')
    else:
        logging.error(f"{code}不在股票池中,请确认参数是否正确")
        return 0, 0
    data = get_research_report(code)
    predictThisYearEps = []
    predictNextYearEps = []
    if data and len(data) > 3:
        for i in data:
            if i['predictThisYearEps'] and i['predictNextYearEps']:
                predictThisYearEps.append(float(i['predictThisYearEps']))
                predictNextYearEps.append(float(i['predictNextYearEps']))
        if len(predictThisYearEps) > 0 and len(predictNextYearEps) > 0:
            avg_predictThisYearEps = round(sum(predictThisYearEps)/len(predictThisYearEps), 2)
            avg_predictNextYearEps = round(sum(predictNextYearEps)/len(predictNextYearEps), 2)
            # print(f"{code}\n今年收益预测:{avg_predictThisYearEps}元\n明年收益预测:{avg_predictNextYearEps}元")
            return avg_predictThisYearEps * total_share, avg_predictNextYearEps * total_share
        else:
            return 0, 0
    else:
        return 0, 0


def select_stock_last_year_eps(code):
    # 查询个股上一年度的归母净利润
    years = ['2019', '2020']
    eps = {'2019': None, '2020': None}
    for year in years:
        target_file = f"annual_report_{year}.bin"
        with open(target_file, 'rb') as f:
            file = f.read()
            content = pickle.loads(file)
        for i in content:
            if i.get('SECURITY_CODE') == str(code):
                eps[year] = i.get('PARENT_NETPROFIT')
    return eps


def get_annual_report_by_year(year):
    # 从年度报告中筛选出归母净利润大于0的数据
    file = f"annual_report_{year}.bin"
    pool = {}
    with open(file, 'rb') as f:
        f = f.read()
        content = pickle.loads(f)
    for i in content:
        if i.get('PARENT_NETPROFIT') and i.get('PARENT_NETPROFIT') > 0:
            pool[i.get('SECURITY_CODE')] = i
    return pool


def continuous_growth_filter(code=None):
    # 筛选出过去三年归母净利润每年都在增长的个股
    pool_2017 = get_annual_report_by_year(2017)
    pool_2018 = get_annual_report_by_year(2018)
    pool_2019 = get_annual_report_by_year(2019)
    pool_2020 = get_annual_report_by_year(2020)
    eps_pool = []
    for k in pool_2017:
        if k in pool_2018.keys() and k in pool_2019.keys() and k in pool_2020.keys():
            if code and str(code) == k:
                if str(code) not in pool_2017.keys():
                    logging.warning(f"2017年报中未发现{code}")
                elif str(code) not in pool_2018.keys():
                    logging.warning(f"2018年报中未发现{code}")
                elif str(code) not in pool_2018.keys():
                    logging.warning(f"2019年报中未发现{code}")
                elif str(code) not in pool_2018.keys():
                    logging.warning(f"2020年报中未发现{code}")
            if pool_2020[k]['PARENT_NETPROFIT'] > pool_2019[k]['PARENT_NETPROFIT'] > pool_2018[k]['PARENT_NETPROFIT'] > pool_2017[k]['PARENT_NETPROFIT']:
                eps_pool.append({'code': k,
                                 'name': pool_2020[k]['SECURITY_NAME_ABBR'],
                                 'eps_2017': pool_2017[k]['PARENT_NETPROFIT'],
                                 'eps_2018': pool_2018[k]['PARENT_NETPROFIT'],
                                 'eps_2019': pool_2019[k]['PARENT_NETPROFIT'],
                                 'eps_2020': pool_2020[k]['PARENT_NETPROFIT']})
    return eps_pool


def continuous_growth_four_year_filter_process():
    # 收益连续四年增长股票池
    target_pool = []
    pool = continuous_growth_filter()
    for i in pool:
        eps2021, eps2022 = get_predict_eps(i['code'])
        i['eps_2021'] = eps2021
        i['eps_2022'] = eps2022
    for i in pool:
        if i['eps_2021'] > i['eps_2020']:
            target_pool.append(i)
    return target_pool


def index_applies():
    indexs = ['000300']  # , '000905', '399006', '000688'
    applies_250 = applies_60 = applies_20 = 0
    for index in indexs:
        data250 = get_stock_kline_with_volume(index, is_index=True, limit=250)
        pre, current = data250[0]['close'], data250[-1]['close']
        if applies_250 < current/pre:
            applies_250 = current/pre
        data60 = data250[-60:]
        pre, current = data60[0]['close'], data60[-1]['close']
        if applies_60 < current/pre:
            applies_60 = current/pre
        data20 = data250[-20:]
        pre, current = data20[0]['close'], data20[-1]['close']
        if applies_20 < current/pre:
            applies_20 = current/pre
    return {'index_250': applies_250, 'index_60': applies_60, 'index_20': applies_60}


def relative_intensity(code, index_applies):
    # 相对强度
    data250 = get_stock_kline_with_volume(code, limit=250)
    pre, current = data250[0]['close'], data250[-1]['close']
    intensity_250 = round((current/pre/index_applies['index_250'] - 1)*100, 2)
    data60 = data250[-60:]
    pre, current = data60[0]['close'], data60[-1]['close']
    intensity_60 = round((current/pre/index_applies['index_60'] - 1)*100, 2)
    data20 = data250[-20:]
    pre, current = data20[0]['close'], data20[-1]['close']
    intensity_20 = round((current/pre/index_applies['index_20'] - 1)*100, 2)
    intensity = {'intensity_250': intensity_250, 'intensity_60': intensity_60, 'intensity_20': intensity_20}
    print(intensity)
    return intensity


def calculate_peg_V2(obj: dict):
    thisYearWeight = 4  # 今年剩下的月数
    nextYearWeight = 12 - thisYearWeight  # 未来12个月中明年所占的月数
    code = obj.get('code')
    total_share = share_pool.get(str(code)).get('total_share')
    close_price = get_stock_kline_with_volume(code, limit=5)[-1]['close']
    avg_predictThisYearEps = obj.get('eps_2021')
    avg_predictNextYearEps = obj.get('eps_2022')
    if avg_predictThisYearEps == 0 or avg_predictNextYearEps == 0:
        logging.warning(f"{obj.get('name')}({code})未获取到机构预测业绩或机构数量较少,本次不参与计算")
        return 0, 0
    last_year_eps = obj.get('eps_2019')
    predict_the_coming_year_eps = round(avg_predictThisYearEps*nextYearWeight/12 + avg_predictNextYearEps*thisYearWeight/12, 2)
    print(f"{obj.get('name')}\t{obj.get('code')}")
    print(f"预测未来一年的预测利润: {round(predict_the_coming_year_eps/100000000, 2)}亿")
    predict_pe = round(close_price * total_share/predict_the_coming_year_eps, 2)
    print(f"预测未来一年的市盈率: {predict_pe}")
    past_year = round(avg_predictThisYearEps*nextYearWeight/12 + last_year_eps*thisYearWeight/12, 2)
    print(f"过去12个月的预测利润: {round(past_year/100000000, 2)}亿")
    growth_rate_earnings_per_share = round((predict_the_coming_year_eps - past_year)/past_year * 100, 2)
    peg = round(predict_pe/growth_rate_earnings_per_share, 2)
    print(f"peg: {peg}\t净利润增速: {growth_rate_earnings_per_share}%")
    return peg, growth_rate_earnings_per_share


def run():
    pool = continuous_growth_four_year_filter_process()
    benchmark = index_applies()
    target = []
    for i in pool:
        intensity = relative_intensity(i['code'], index_applies=benchmark)
        if intensity['intensity_250'] > intensity['intensity_20'] > 0 or intensity['intensity_250'] > intensity['intensity_60'] > 0:
            i['intensity_250'] = intensity['intensity_250']
            i['intensity_60'] = intensity['intensity_60']
            i['intensity_20'] = intensity['intensity_20']
            i['total_intensity'] = intensity['intensity_250'] + intensity['intensity_60'] + intensity['intensity_20']
            i['peg'], i['growth'] = calculate_peg_V2(i)
            target.append(i)
    target = sorted(target, key=lambda x: x['peg'], reverse=False)
    print(target, '\n', len(target))
    return target


def run_simple(code):
    data = continuous_growth_filter(code)
    for i in data:
        if i['code'] == str(code):
            eps2021, eps2022 = get_predict_eps(i['code'])
            i['eps_2021'] = eps2021
            i['eps_2022'] = eps2022
            peg, growth = calculate_peg_V2(i)
            i['peg'] = peg
            i['growth'] = growth
            print(i)
            break
    else:
        logging.warning(f"{code} 不符合归母净利润四年连续增长的标准或未收录到个股年报数据,请核实.")


run_simple('002539')

