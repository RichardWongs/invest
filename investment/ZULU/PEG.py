# encoding: utf-8
import logging
import os
import time
import pickle
import requests
import json
from datetime import date, timedelta
from RPS.foreign_capital_increase import foreign_capital_filter
from monitor import get_industry_by_code
from security import get_stock_kline_with_volume
from RPS.quantitative_screening import get_RPS_stock_pool
from ZULU import share_pool


def get_research_report(code):
    # 获取个股研报数据
    time.sleep(0.5)
    beginTime = date.today() - timedelta(days=180)
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
        return response if response else None
    return None


def save_research_report2local():
    # 从东方财富网下载个股机构研报,并以二进制文件保存到本地,建议每周更新一次即可
    target = {}
    pool = continuous_growth_filter()
    for i in pool:
        data = get_research_report(i['code'])
        if data:
            print(data)
            target[i['code']] = data
    with open("research_report.bin", 'wb') as f:
        f.write(pickle.dumps(target))


def read_research_report_from_local():
    os.chdir("../ZULU")
    with open("research_report.bin", 'rb') as f:
        f = f.read()
        content = pickle.loads(f)
        return content


def read_binary_file_from_local(filename):
    os.chdir("../ZULU")
    with open(filename, 'rb') as f:
        f = f.read()
        content = pickle.loads(f)
        return content


def get_predict_eps(code, research_report: dict):
    # 根据研报预测计算今明两年的归母净利润
    if share_pool.get(str(code)):
        total_share = share_pool.get(str(code)).get('total_share')
    else:
        logging.error(f"{code}不在股票池中,请确认参数是否正确")
        return 0, 0
    if str(code) not in research_report.keys():
        # logging.warning(f"未查询到 {code} 机构研报,请更新研报数据!")
        return 0, 0
    else:
        data = research_report[str(code)]
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


def get_annual_report_by_year(year):
    # 从年度报告中筛选出归母净利润大于0的数据
    os.chdir("../ZULU")
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
            if pool_2020[k]['PARENT_NETPROFIT'] > pool_2019[k]['PARENT_NETPROFIT'] > pool_2018[k]['PARENT_NETPROFIT'] > pool_2017[k]['PARENT_NETPROFIT'] > 0:
                eps_pool.append({'code': k,
                                 'name': pool_2020[k]['SECURITY_NAME_ABBR'],
                                 'eps_2017': pool_2017[k]['PARENT_NETPROFIT'],
                                 'eps_2018': pool_2018[k]['PARENT_NETPROFIT'],
                                 'eps_2019': pool_2019[k]['PARENT_NETPROFIT'],
                                 'eps_2020': pool_2020[k]['PARENT_NETPROFIT']})
            # else:
            #     logging.warning(f"{k} 不符合年报净利润连续三年增长的标准")
    return eps_pool


def continuous_growth_four_year_filter_process():
    # 收益连续四年增长股票池
    target_pool = []
    pool = continuous_growth_filter()
    logging.warning(f"过去三年归母净利润每年都在增长的个股数量:{len(pool)}\t{pool}")
    research_report = read_research_report_from_local()
    logging.warning(f"公开研报覆盖个股:{len(research_report)}")
    for i in pool:
        eps2021, eps2022 = get_predict_eps(i['code'], research_report)
        i['eps_2021'] = eps2021
        i['eps_2022'] = eps2022
    for i in pool:
        if i['eps_2021'] > i['eps_2020']:
            target_pool.append(i)
    logging.warning(f"机构研报预测业绩增长的个股数量:{len(target_pool)}\t{target_pool}")
    return target_pool


def index_applies():
    indexes = ['000300']  # , '000905', '399006', '000688'
    applies_250, applies_60, applies_20 = 0, 0, 0
    for index in indexes:
        data250 = get_stock_kline_with_volume(index, is_index=True, limit=250)
        pre, current = data250[0]['close'], data250[-1]['close']
        if applies_250 < current/pre:
            applies_250 = current/pre
        data60 = data250[-60:]
        pre, current = data60[0]['close'], data60[-1]['close']
        if applies_60 < current/pre:
            applies_60 = current/pre
        data20 = data250[-22:]
        pre, current = data20[0]['close'], data20[-1]['close']
        if applies_20 < current/pre:
            applies_20 = current/pre
    return {'index_250': applies_250, 'index_60': applies_60, 'index_20': applies_60}


def relative_intensity(obj: dict, indexApplies=None):
    # 相对强度
    if not indexApplies:
        indexApplies = index_applies()
    data250 = get_stock_kline_with_volume(obj['code'], limit=250)
    pre, current = data250[0]['close'], data250[-1]['close']
    obj['intensity_250'] = round((current/pre/indexApplies['index_250'] - 1), 2)
    data60 = data250[-60:]
    pre, current = data60[0]['close'], data60[-1]['close']
    obj['intensity_60'] = round((current/pre/indexApplies['index_60'] - 1), 2)
    data20 = data250[-22:]
    pre, current = data20[0]['close'], data20[-1]['close']
    obj['intensity_20'] = round((current/pre/indexApplies['index_20'] - 1), 2)
    obj['total_intensity'] = round(obj['intensity_20'] + obj['intensity_60'] + obj['intensity_250'], 2)
    if obj['intensity_250'] > 0 and obj['intensity_20'] > 0:
        obj['strong'] = True
    else:
        obj['strong'] = False
    return obj


def calculate_peg_V2(obj: dict):
    thisYearWeight = 1  # 今年剩下的月数
    nextYearWeight = 12 - thisYearWeight  # 未来12个月中明年所占的月数
    code = obj.get('code')
    total_share = share_pool.get(str(code)).get('total_share')
    close_price = get_stock_kline_with_volume(code, limit=5)[-1]['close']
    avg_predictThisYearEps = obj.get('eps_2021')
    avg_predictNextYearEps = obj.get('eps_2022')
    if avg_predictThisYearEps == 0 or avg_predictNextYearEps == 0:
        logging.warning(f"{obj.get('name')}({code})未获取到机构预测业绩或机构数量较少,本次不参与计算")
        return 0, 0
    last_year_eps = obj.get('eps_2020')
    predict_the_coming_year_eps = round(avg_predictThisYearEps*thisYearWeight/12 + avg_predictNextYearEps*nextYearWeight/12, 2)
    # print(f"{obj.get('name')}\t{obj.get('code')}")
    # print(f"未来12个月的预测利润: {round(predict_the_coming_year_eps/100000000, 2)}亿")
    predict_pe = round(close_price * total_share/predict_the_coming_year_eps, 2)
    # print(f"预测未来一年的市盈率: {predict_pe}")
    past_year = round(avg_predictThisYearEps*nextYearWeight/12 + last_year_eps*thisYearWeight/12, 2)
    # print(f"过去12个月的预测利润: {round(past_year/100000000, 2)}亿")
    growth_rate_earnings_per_share = round((predict_the_coming_year_eps - past_year)/past_year * 100, 2)
    peg = round(predict_pe/growth_rate_earnings_per_share, 2)
    # print(f"peg: {peg}\t净利润增速: {growth_rate_earnings_per_share}%")
    # logging.warning(f"\n{obj.get('name')}\t{obj.get('code')}\n未来12个月的预测利润: {round(predict_the_coming_year_eps/100000000, 2)}亿\n预测未来一年的市盈率: {predict_pe}\n过去12个月的预测利润: {round(past_year/100000000, 2)}亿\npeg: {peg}\t净利润增速: {growth_rate_earnings_per_share}%")
    return predict_pe, peg, growth_rate_earnings_per_share


def quarter_forecast_filter(pool):
    # 根据季报和业绩预告做进一步过滤
    quarter_report = read_binary_file_from_local("quarter_report.bin")
    for i in pool[:]:
        if i['code'] in quarter_report.keys():
            if quarter_report[i['code']]['SJLTZ'] < 0:
                pool.remove(i)
    logging.warning(f"季报净利润增速为正的个股数量(包含未公布季报个股): {len(pool)}")
    earnings_forecast = read_binary_file_from_local("earnings_forecast.bin")
    for i in pool[:]:
        if i['code'] in earnings_forecast.keys():
            ADD_AMP_LOWER = earnings_forecast[i['code']]['ADD_AMP_LOWER']
            if ADD_AMP_LOWER and ADD_AMP_LOWER < 0:
                pool.remove(i)
        else:
            i['industry'] = get_industry_by_code(i['code'])
    logging.warning(f"业绩预告净利润增速为正的个股数量(包含未公布业绩预告个股): {len(pool)}")
    return pool


def get_RPS_stock_pool_zulu():
    # 根据RPS值进行第一步筛选
    import pandas as pd
    os.chdir("../RPS")
    files = ['RPS_20_V2.csv', 'RPS_250_V2.csv']
    long = [(i[0].split('.')[0], i[1]) for i in (pd.read_csv(files[1], encoding="utf-8")).values if i[-1] > 80]
    short = [(i[0].split('.')[0], i[1]) for i in (pd.read_csv(files[0], encoding="utf-8")).values if i[-1] > 80]
    pool = [i for i in long if i in short]
    logging.warning(f"高RPS股票池:\t{len(pool)}\t{pool}")
    return pool


def run():
    pool = continuous_growth_four_year_filter_process()
    logging.warning(f"符合归母净利润四年连续增长标准的个股数量: {len(pool)}")
    pool = quarter_forecast_filter(pool)
    rps_pool = []
    indexs = index_applies()
    target = []
    low_peg_pool = []
    for i in pool:
        i = relative_intensity(i, indexApplies=indexs)
        i['pe'], i['peg'], i['growth'] = calculate_peg_V2(i)
        del i['eps_2017']
        del i['eps_2018']
        del i['eps_2019']
        del i['eps_2020']
        del i['eps_2021']
        del i['eps_2022']
        if 0 < i['peg'] < 1.0 and i['strong']:
            low_peg_pool.append(i)
        if i['peg'] > 0:
            target.append(i)
    target = sorted(target, key=lambda x: x['peg'], reverse=False)
    low_peg_pool = sorted(low_peg_pool, key=lambda x: x['peg'], reverse=False)
    logging.warning(f"低PEG且高相对强度:{len(low_peg_pool)}\t{low_peg_pool}\n全部PEG股票池:{len(target)}\t{target}")
    return low_peg_pool, target


def run_simple(code, eps2021=None, eps2022=None):
    data = continuous_growth_filter(code)
    research_report = read_research_report_from_local()
    for i in data:
        if i['code'] == str(code):
            if not (eps2021 and eps2022):
                eps2021, eps2022 = get_predict_eps(i['code'], research_report)
            i['eps_2021'] = eps2021
            i['eps_2022'] = eps2022
            i['pe'], i['peg'], i['growth'] = calculate_peg_V2(i)
            index_applie = index_applies()
            i = relative_intensity(i, index_applie)
            print(i)
            break
    else:
        logging.warning(f"{code} 不符合归母净利润四年连续增长的标准或未收录到个股年报数据,请核实.")


def update_dataPackage():
    # 更新数据包
    from ZULU import get_quarter_report, get_earnings_forecast
    save_research_report2local()
    get_quarter_report()
    get_earnings_forecast()


save_research_report2local()
