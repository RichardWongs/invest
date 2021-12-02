# encoding: utf-8
import logging
import os
import time
import pickle
import requests
import json
from datetime import date, timedelta
from RPS.foreign_capital_increase import foreign_capital_filter
from security import get_stock_kline_with_volume
from RPS.quantitative_screening import get_RPS_stock_pool
from ZULU import share_pool


def get_research_report(code):
    # 获取个股研报数据
    time.sleep(0.5)
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
        logging.warning(f"未查询到 {code} 机构研报,请更新研报数据!")
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
            else:
                logging.warning(f"{k} 不符合年报净利润连续三年增长的标准")
    return eps_pool


def continuous_growth_four_year_filter_process():
    # 收益连续四年增长股票池
    target_pool = []
    pool = continuous_growth_filter()
    research_report = read_research_report_from_local()
    for i in pool:
        eps2021, eps2022 = get_predict_eps(i['code'], research_report)
        i['eps_2021'] = eps2021
        i['eps_2022'] = eps2022
    for i in pool:
        if i['eps_2021'] > i['eps_2020']:
            target_pool.append(i)
    return target_pool


def index_applies():
    indexes = ['000300'] # , '000905', '399006', '000688'
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
    intensity_250 = round((current/pre/indexApplies['index_250'] - 1), 2)
    data60 = data250[-60:]
    pre, current = data60[0]['close'], data60[-1]['close']
    intensity_60 = round((current/pre/indexApplies['index_60'] - 1), 2)
    data20 = data250[-22:]
    pre, current = data20[0]['close'], data20[-1]['close']
    intensity_20 = round((current/pre/indexApplies['index_20'] - 1), 2)
    # intensity = {'intensity_250': intensity_250, 'intensity_60': intensity_60, 'intensity_20': intensity_20}
    obj['intensity_20'] = intensity_20
    obj['intensity_60'] = intensity_60
    obj['intensity_250'] = intensity_250
    obj['total_intensity'] = round(intensity_20 + intensity_60 + intensity_250, 2)
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
    logging.warning(f"\n{obj.get('name')}\t{obj.get('code')}\n未来12个月的预测利润: {round(predict_the_coming_year_eps/100000000, 2)}亿\n预测未来一年的市盈率: {predict_pe}\n过去12个月的预测利润: {round(past_year/100000000, 2)}亿\npeg: {peg}\t净利润增速: {growth_rate_earnings_per_share}%")
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
    target = []
    low_peg_pool = []
    rps_pool = get_RPS_stock_pool_zulu()
    rps_pool = [i[0] for i in rps_pool]
    logging.warning(f"高RPS股票池: {rps_pool}")
    for i in pool:
        i['pe'], i['peg'], i['growth'] = calculate_peg_V2(i)
        del i['eps_2017']
        del i['eps_2018']
        del i['eps_2019']
        del i['eps_2020']
        del i['eps_2021']
        del i['eps_2022']
        if 0 < i['peg'] < 1.0 and i['code'] in rps_pool:
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


# from ZULU import get_quarter_report, get_earnings_forecast
# save_research_report2local()
# get_quarter_report()
# get_earnings_forecast()
p = [{'code': '600919', 'name': '江苏银行', 'pe': 3.86, 'peg': 0.18, 'growth': 21.21}, {'code': '601166', 'name': '兴业银行', 'pe': 4.14, 'peg': 0.25, 'growth': 16.35}, {'code': '601677', 'name': '明泰铝业', 'pe': 9.79, 'peg': 0.27, 'growth': 36.2}, {'code': '601225', 'name': '陕西煤业', 'pe': 5.21, 'peg': 0.28, 'growth': 18.86}, {'code': '601838', 'name': '成都银行', 'pe': 4.85, 'peg': 0.29, 'growth': 16.74}, {'code': '601009', 'name': '南京银行', 'pe': 5.09, 'peg': 0.29, 'growth': 17.49}, {'code': '002154', 'name': '报喜鸟', 'pe': 10.07, 'peg': 0.31, 'growth': 31.99}, {'code': '000157', 'name': '中联重科', 'pe': 6.74, 'peg': 0.32, 'growth': 20.81}, {'code': '002918', 'name': '蒙娜丽莎', 'pe': 11.7, 'peg': 0.34, 'growth': 34.64}, {'code': '601668', 'name': '中国建筑', 'pe': 3.6, 'peg': 0.36, 'growth': 10.14}, {'code': '000001', 'name': '平安银行', 'pe': 7.9, 'peg': 0.36, 'growth': 21.73}, {'code': '601658', 'name': '邮储银行', 'pe': 5.49, 'peg': 0.37, 'growth': 14.68}, {'code': '600926', 'name': '杭州银行', 'pe': 8.02, 'peg': 0.38, 'growth': 20.9}, {'code': '601390', 'name': '中国中铁', 'pe': 4.34, 'peg': 0.38, 'growth': 11.35}, {'code': '600882', 'name': '妙可蓝多', 'pe': 50.68, 'peg': 0.39, 'growth': 129.81}, {'code': '601229', 'name': '上海银行', 'pe': 4.12, 'peg': 0.39, 'growth': 10.5}, {'code': '000425', 'name': '徐工机械', 'pe': 6.89, 'peg': 0.41, 'growth': 16.72}, {'code': '603916', 'name': '苏博特', 'pe': 11.78, 'peg': 0.41, 'growth': 28.74}, {'code': '603180', 'name': '金牌厨柜', 'pe': 11.81, 'peg': 0.41, 'growth': 29.11}, {'code': '002839', 'name': '张家港行', 'pe': 7.38, 'peg': 0.44, 'growth': 16.74}, {'code': '002833', 'name': '弘亚数控', 'pe': 12.87, 'peg': 0.44, 'growth': 29.26}, {'code': '300587', 'name': '天铁股份', 'pe': 24.92, 'peg': 0.44, 'growth': 56.08}, {'code': '603801', 'name': '志邦家居', 'pe': 10.76, 'peg': 0.44, 'growth': 24.24}, {'code': '601128', 'name': '常熟银行', 'pe': 7.54, 'peg': 0.45, 'growth': 16.8}, {'code': '300260', 'name': '新莱应材', 'pe': 33.8, 'peg': 0.45, 'growth': 75.13}, {'code': '002831', 'name': '裕同科技', 'pe': 17.36, 'peg': 0.45, 'growth': 38.23}, {'code': '002539', 'name': '云图控股', 'pe': 10.39, 'peg': 0.46, 'growth': 22.52}, {'code': '601169', 'name': '北京银行', 'pe': 3.84, 'peg': 0.47, 'growth': 8.16}, {'code': '002867', 'name': '周大生', 'pe': 11.55, 'peg': 0.48, 'growth': 24.07}, {'code': '000026', 'name': '飞亚达', 'pe': 9.63, 'peg': 0.48, 'growth': 20.11}, {'code': '600346', 'name': '恒力石化', 'pe': 7.82, 'peg': 0.49, 'growth': 16.12}, {'code': '002142', 'name': '宁波银行', 'pe': 10.18, 'peg': 0.49, 'growth': 20.84}, {'code': '601636', 'name': '旗滨集团', 'pe': 8.47, 'peg': 0.49, 'growth': 17.38}, {'code': '688793', 'name': '倍轻松', 'pe': 31.72, 'peg': 0.5, 'growth': 63.61}, {'code': '688599', 'name': '天合光能', 'pe': 41.33, 'peg': 0.5, 'growth': 82.37}, {'code': '603279', 'name': '景津环保', 'pe': 18.23, 'peg': 0.5, 'growth': 36.78}, {'code': '600556', 'name': '天下秀', 'pe': 31.52, 'peg': 0.51, 'growth': 61.59}, {'code': '600323', 'name': '瀚蓝环境', 'pe': 11.22, 'peg': 0.52, 'growth': 21.46}, {'code': '603588', 'name': '高能环境', 'pe': 15.42, 'peg': 0.54, 'growth': 28.73}, {'code': '600036', 'name': '招商银行', 'pe': 9.49, 'peg': 0.55, 'growth': 17.25}, {'code': '603129', 'name': '春风动力', 'pe': 31.91, 'peg': 0.56, 'growth': 56.97}, {'code': '002572', 'name': '索菲亚', 'pe': 9.67, 'peg': 0.57, 'growth': 17.04}, {'code': '002832', 'name': '比音勒芬', 'pe': 16.48, 'peg': 0.58, 'growth': 28.41}, {'code': '002541', 'name': '鸿路钢构', 'pe': 17.39, 'peg': 0.58, 'growth': 30.09}, {'code': '603688', 'name': '石英股份', 'pe': 48.2, 'peg': 0.59, 'growth': 81.38}, {'code': '300601', 'name': '康泰生物', 'pe': 39.58, 'peg': 0.6, 'growth': 66.42}, {'code': '600048', 'name': '保利地产', 'pe': 5.23, 'peg': 0.6, 'growth': 8.74}, {'code': '600438', 'name': '通威股份', 'pe': 19.46, 'peg': 0.61, 'growth': 31.76}, {'code': '603613', 'name': '国联股份', 'pe': 43.37, 'peg': 0.63, 'growth': 68.73}, {'code': '600989', 'name': '宝丰能源', 'pe': 14.75, 'peg': 0.63, 'growth': 23.59}, {'code': '000977', 'name': '浪潮信息', 'pe': 18.47, 'peg': 0.63, 'growth': 29.46}, {'code': '002271', 'name': '东方雨虹', 'pe': 18.95, 'peg': 0.63, 'growth': 30.24}, {'code': '300482', 'name': '万孚生物', 'pe': 16.87, 'peg': 0.65, 'growth': 25.87}, {'code': '002677', 'name': '浙江美大', 'pe': 12.73, 'peg': 0.65, 'growth': 19.62}, {'code': '300755', 'name': '华致酒行', 'pe': 21.51, 'peg': 0.66, 'growth': 32.81}, {'code': '002129', 'name': '中环股份', 'pe': 25.86, 'peg': 0.66, 'growth': 38.98}, {'code': '002727', 'name': '一心堂', 'pe': 16.18, 'peg': 0.66, 'growth': 24.48}, {'code': '002960', 'name': '青鸟消防', 'pe': 23.0, 'peg': 0.67, 'growth': 34.21}, {'code': '300031', 'name': '宝通科技', 'pe': 15.94, 'peg': 0.67, 'growth': 23.65}, {'code': '601939', 'name': '建设银行', 'pe': 4.66, 'peg': 0.67, 'growth': 6.92}, {'code': '603043', 'name': '广州酒家', 'pe': 17.79, 'peg': 0.69, 'growth': 25.73}, {'code': '603587', 'name': '地素时尚', 'pe': 10.49, 'peg': 0.69, 'growth': 15.24}, {'code': '300982', 'name': '苏文电能', 'pe': 24.49, 'peg': 0.7, 'growth': 34.82}, {'code': '000661', 'name': '长春高新', 'pe': 21.4, 'peg': 0.7, 'growth': 30.6}, {'code': '688308', 'name': '欧科亿', 'pe': 24.08, 'peg': 0.71, 'growth': 33.84}, {'code': '002508', 'name': '老板电器', 'pe': 13.04, 'peg': 0.71, 'growth': 18.48}, {'code': '002645', 'name': '华宏科技', 'pe': 22.43, 'peg': 0.72, 'growth': 31.02}, {'code': '601888', 'name': '中国中免', 'pe': 26.71, 'peg': 0.73, 'growth': 36.77}, {'code': '002706', 'name': '良信股份', 'pe': 31.7, 'peg': 0.73, 'growth': 43.69}, {'code': '300451', 'name': '创业慧康', 'pe': 25.39, 'peg': 0.74, 'growth': 34.53}, {'code': '002812', 'name': '恩捷股份', 'pe': 53.84, 'peg': 0.76, 'growth': 71.04}, {'code': '002293', 'name': '罗莱生活', 'pe': 13.34, 'peg': 0.76, 'growth': 17.55}, {'code': '300450', 'name': '先导智能', 'pe': 50.24, 'peg': 0.77, 'growth': 65.05}, {'code': '600031', 'name': '三一重工', 'pe': 10.46, 'peg': 0.78, 'growth': 13.46}, {'code': '300037', 'name': '新宙邦', 'pe': 29.29, 'peg': 0.78, 'growth': 37.65}, {'code': '603444', 'name': '吉比特', 'pe': 14.11, 'peg': 0.79, 'growth': 17.87}, {'code': '600612', 'name': '老凤祥', 'pe': 11.71, 'peg': 0.81, 'growth': 14.5}, {'code': '002080', 'name': '中材科技', 'pe': 15.1, 'peg': 0.82, 'growth': 18.49}, {'code': '688169', 'name': '石头科技', 'pe': 24.3, 'peg': 0.83, 'growth': 29.38}, {'code': '002402', 'name': '和而泰', 'pe': 31.02, 'peg': 0.84, 'growth': 37.03}, {'code': '300911', 'name': '亿田智能', 'pe': 27.1, 'peg': 0.85, 'growth': 31.86}, {'code': '300724', 'name': '捷佳伟创', 'pe': 35.11, 'peg': 0.85, 'growth': 41.11}, {'code': '300207', 'name': '欣旺达', 'pe': 45.03, 'peg': 0.86, 'growth': 52.18}, {'code': '688580', 'name': '伟思医疗', 'pe': 30.06, 'peg': 0.87, 'growth': 34.74}, {'code': '300792', 'name': '壹网壹创', 'pe': 24.68, 'peg': 0.87, 'growth': 28.22}, {'code': '601995', 'name': '中金公司', 'pe': 19.8, 'peg': 0.88, 'growth': 22.6}, {'code': '600690', 'name': '海尔智家', 'pe': 17.43, 'peg': 0.88, 'growth': 19.83}, {'code': '601799', 'name': '星宇股份', 'pe': 36.72, 'peg': 0.88, 'growth': 41.59}, {'code': '002318', 'name': '久立特材', 'pe': 15.72, 'peg': 0.88, 'growth': 17.95}, {'code': '300785', 'name': '值得买', 'pe': 26.15, 'peg': 0.89, 'growth': 29.23}, {'code': '603659', 'name': '璞泰来', 'pe': 49.88, 'peg': 0.89, 'growth': 55.75}, {'code': '600702', 'name': '舍得酒业', 'pe': 42.77, 'peg': 0.9, 'growth': 47.77}, {'code': '300623', 'name': '捷捷微电', 'pe': 33.7, 'peg': 0.91, 'growth': 36.99}, {'code': '002353', 'name': '杰瑞股份', 'pe': 17.71, 'peg': 0.92, 'growth': 19.29}, {'code': '603883', 'name': '老百姓', 'pe': 20.64, 'peg': 0.94, 'growth': 21.98}, {'code': '300628', 'name': '亿联网络', 'pe': 31.23, 'peg': 0.94, 'growth': 33.19}, {'code': '603939', 'name': '益丰药房', 'pe': 26.66, 'peg': 0.94, 'growth': 28.43}, {'code': '002946', 'name': '新乳业', 'pe': 28.33, 'peg': 0.96, 'growth': 29.39}, {'code': '688059', 'name': '华锐精密', 'pe': 35.97, 'peg': 0.97, 'growth': 36.95}, {'code': '003006', 'name': '百亚股份', 'pe': 26.46, 'peg': 0.97, 'growth': 27.39}, {'code': '002049', 'name': '紫光国微', 'pe': 52.26, 'peg': 0.97, 'growth': 53.68}, {'code': '002007', 'name': '华兰生物', 'pe': 21.95, 'peg': 0.98, 'growth': 22.33}, {'code': '603019', 'name': '中科曙光', 'pe': 29.3, 'peg': 0.98, 'growth': 29.85}, {'code': '603707', 'name': '健友股份', 'pe': 33.78, 'peg': 0.99, 'growth': 34.01}, {'code': '688798', 'name': '艾为电子', 'pe': 82.08, 'peg': 1.0, 'growth': 82.33}, {'code': '603833', 'name': '欧派家居', 'pe': 21.83, 'peg': 1.0, 'growth': 21.89}, {'code': '688626', 'name': '翔宇医疗', 'pe': 29.78, 'peg': 1.02, 'growth': 29.22}, {'code': '300866', 'name': '安克创新', 'pe': 31.5, 'peg': 1.02, 'growth': 30.74}, {'code': '002372', 'name': '伟星新材', 'pe': 19.41, 'peg': 1.02, 'growth': 19.08}, {'code': '300316', 'name': '晶盛机电', 'pe': 40.77, 'peg': 1.03, 'growth': 39.67}, {'code': '300122', 'name': '智飞生物', 'pe': 32.68, 'peg': 1.03, 'growth': 31.72}, {'code': '688598', 'name': '金博股份', 'pe': 45.36, 'peg': 1.05, 'growth': 43.32}, {'code': '000333', 'name': '美的集团', 'pe': 14.29, 'peg': 1.05, 'growth': 13.55}, {'code': '002465', 'name': '海格通信', 'pe': 26.77, 'peg': 1.05, 'growth': 25.54}, {'code': '603986', 'name': '兆易创新', 'pe': 37.24, 'peg': 1.06, 'growth': 35.13}, {'code': '002415', 'name': '海康威视', 'pe': 21.87, 'peg': 1.06, 'growth': 20.71}, {'code': '002139', 'name': '拓邦股份', 'pe': 28.23, 'peg': 1.06, 'growth': 26.7}, {'code': '300638', 'name': '广和通', 'pe': 41.21, 'peg': 1.06, 'growth': 38.93}, {'code': '688066', 'name': '航天宏图', 'pe': 45.22, 'peg': 1.07, 'growth': 42.36}, {'code': '300059', 'name': '东方财富', 'pe': 34.97, 'peg': 1.07, 'growth': 32.71}, {'code': '688508', 'name': '芯朋微', 'pe': 60.94, 'peg': 1.09, 'growth': 55.74}, {'code': '600223', 'name': '鲁商发展', 'pe': 16.35, 'peg': 1.09, 'growth': 15.01}, {'code': '000739', 'name': '普洛药业', 'pe': 33.87, 'peg': 1.1, 'growth': 30.81}, {'code': '300662', 'name': '科锐国际', 'pe': 35.25, 'peg': 1.11, 'growth': 31.74}, {'code': '300014', 'name': '亿纬锂能', 'pe': 59.85, 'peg': 1.13, 'growth': 52.74}, {'code': '300979', 'name': '华利集团', 'pe': 30.68, 'peg': 1.15, 'growth': 26.68}, {'code': '300413', 'name': '芒果超媒', 'pe': 27.22, 'peg': 1.15, 'growth': 23.66}, {'code': '600529', 'name': '山东药玻', 'pe': 31.43, 'peg': 1.15, 'growth': 27.29}, {'code': '603198', 'name': '迎驾贡酒', 'pe': 31.54, 'peg': 1.16, 'growth': 27.24}, {'code': '300223', 'name': '北京君正', 'pe': 57.11, 'peg': 1.16, 'growth': 49.14}, {'code': '000799', 'name': '酒鬼酒', 'pe': 56.54, 'peg': 1.16, 'growth': 48.6}, {'code': '601728', 'name': '中国电信', 'pe': 13.48, 'peg': 1.18, 'growth': 11.46}, {'code': '300327', 'name': '中颖电子', 'pe': 45.21, 'peg': 1.18, 'growth': 38.32}, {'code': '600887', 'name': '伊利股份', 'pe': 22.09, 'peg': 1.18, 'growth': 18.78}, {'code': '002409', 'name': '雅克科技', 'pe': 44.94, 'peg': 1.19, 'growth': 37.85}, {'code': '688200', 'name': '华峰测控', 'pe': 53.43, 'peg': 1.2, 'growth': 44.51}, {'code': '605305', 'name': '中际联合', 'pe': 37.5, 'peg': 1.21, 'growth': 30.99}, {'code': '603599', 'name': '广信股份', 'pe': 12.72, 'peg': 1.21, 'growth': 10.55}, {'code': '603369', 'name': '今世缘', 'pe': 29.13, 'peg': 1.23, 'growth': 23.63}, {'code': '002242', 'name': '九阳股份', 'pe': 15.56, 'peg': 1.24, 'growth': 12.52}, {'code': '688601', 'name': '力芯微', 'pe': 53.77, 'peg': 1.25, 'growth': 42.88}, {'code': '688076', 'name': '诺泰生物', 'pe': 49.05, 'peg': 1.25, 'growth': 39.18}, {'code': '603899', 'name': '晨光文具', 'pe': 27.55, 'peg': 1.26, 'growth': 21.83}, {'code': '600845', 'name': '宝信软件', 'pe': 40.55, 'peg': 1.27, 'growth': 31.81}, {'code': '000938', 'name': '紫光股份', 'pe': 27.44, 'peg': 1.28, 'growth': 21.36}, {'code': '603501', 'name': '韦尔股份', 'pe': 42.8, 'peg': 1.28, 'growth': 33.34}, {'code': '603345', 'name': '安井食品', 'pe': 42.72, 'peg': 1.29, 'growth': 32.99}, {'code': '688016', 'name': '心脉医疗', 'pe': 45.45, 'peg': 1.31, 'growth': 34.62}, {'code': '601965', 'name': '中国汽研', 'pe': 24.48, 'peg': 1.31, 'growth': 18.69}, {'code': '605089', 'name': '味知香', 'pe': 41.35, 'peg': 1.32, 'growth': 31.36}, {'code': '002837', 'name': '英维克', 'pe': 45.14, 'peg': 1.33, 'growth': 33.93}, {'code': '603719', 'name': '良品铺子', 'pe': 31.76, 'peg': 1.35, 'growth': 23.59}, {'code': '300012', 'name': '华测检测', 'pe': 42.62, 'peg': 1.35, 'growth': 31.52}, {'code': '300653', 'name': '正海生物', 'pe': 38.96, 'peg': 1.35, 'growth': 28.83}, {'code': '002557', 'name': '洽洽食品', 'pe': 25.27, 'peg': 1.36, 'growth': 18.53}, {'code': '300383', 'name': '光环新网', 'pe': 20.64, 'peg': 1.36, 'growth': 15.22}, {'code': '600809', 'name': '山西汾酒', 'pe': 50.68, 'peg': 1.38, 'growth': 36.71}, {'code': '603919', 'name': '金徽酒', 'pe': 34.38, 'peg': 1.38, 'growth': 24.88}, {'code': '002050', 'name': '三花智控', 'pe': 37.42, 'peg': 1.39, 'growth': 26.98}, {'code': '002436', 'name': '兴森科技', 'pe': 30.01, 'peg': 1.39, 'growth': 21.59}, {'code': '688100', 'name': '威胜信息', 'pe': 36.5, 'peg': 1.43, 'growth': 25.59}, {'code': '002821', 'name': '凯莱英', 'pe': 79.75, 'peg': 1.43, 'growth': 55.6}, {'code': '000568', 'name': '泸州老窖', 'pe': 36.72, 'peg': 1.44, 'growth': 25.54}, {'code': '600298', 'name': '安琪酵母', 'pe': 27.61, 'peg': 1.44, 'growth': 19.19}, {'code': '603195', 'name': '公牛集团', 'pe': 26.83, 'peg': 1.45, 'growth': 18.46}, {'code': '688516', 'name': '奥特维', 'pe': 59.28, 'peg': 1.47, 'growth': 40.41}, {'code': '300595', 'name': '欧普康视', 'pe': 54.24, 'peg': 1.49, 'growth': 36.31}, {'code': '002230', 'name': '科大讯飞', 'pe': 50.79, 'peg': 1.5, 'growth': 33.83}, {'code': '600600', 'name': '青岛啤酒', 'pe': 38.2, 'peg': 1.51, 'growth': 25.33}, {'code': '300896', 'name': '爱美客', 'pe': 83.01, 'peg': 1.52, 'growth': 54.69}, {'code': '688789', 'name': '宏华数科', 'pe': 69.13, 'peg': 1.53, 'growth': 45.22}, {'code': '300474', 'name': '景嘉微', 'pe': 93.47, 'peg': 1.56, 'growth': 59.9}, {'code': '601100', 'name': '恒立液压', 'pe': 31.23, 'peg': 1.6, 'growth': 19.57}, {'code': '300685', 'name': '艾德生物', 'pe': 54.29, 'peg': 1.6, 'growth': 33.96}, {'code': '688301', 'name': '奕瑞科技', 'pe': 66.69, 'peg': 1.61, 'growth': 41.55}, {'code': '000858', 'name': '五粮液', 'pe': 30.84, 'peg': 1.63, 'growth': 18.9}, {'code': '603456', 'name': '九洲药业', 'pe': 57.95, 'peg': 1.63, 'growth': 35.55}, {'code': '688621', 'name': '阳光诺和', 'pe': 66.14, 'peg': 1.67, 'growth': 39.55}, {'code': '300776', 'name': '帝尔激光', 'pe': 40.14, 'peg': 1.67, 'growth': 24.01}, {'code': '600050', 'name': '中国联通', 'pe': 17.08, 'peg': 1.69, 'growth': 10.13}, {'code': '300363', 'name': '博腾股份', 'pe': 78.28, 'peg': 1.7, 'growth': 45.97}, {'code': '688363', 'name': '华熙生物', 'pe': 68.47, 'peg': 1.74, 'growth': 39.25}, {'code': '688686', 'name': '奥普特', 'pe': 62.05, 'peg': 1.8, 'growth': 34.45}, {'code': '600760', 'name': '中航沈飞', 'pe': 55.87, 'peg': 1.81, 'growth': 30.89}, {'code': '688083', 'name': '中望软件', 'pe': 86.01, 'peg': 1.84, 'growth': 46.84}, {'code': '688131', 'name': '皓元医药', 'pe': 79.81, 'peg': 1.85, 'growth': 43.21}, {'code': '300760', 'name': '迈瑞医疗', 'pe': 42.36, 'peg': 1.89, 'growth': 22.4}, {'code': '300957', 'name': '贝泰妮', 'pe': 74.24, 'peg': 1.91, 'growth': 38.84}, {'code': '300496', 'name': '中科创达', 'pe': 74.8, 'peg': 1.92, 'growth': 39.01}, {'code': '600763', 'name': '通策医疗', 'pe': 64.18, 'peg': 1.93, 'growth': 33.29}, {'code': '300661', 'name': '圣邦股份', 'pe': 86.04, 'peg': 1.96, 'growth': 43.82}, {'code': '688356', 'name': '键凯科技', 'pe': 96.19, 'peg': 2.0, 'growth': 48.08}, {'code': '002461', 'name': '珠江啤酒', 'pe': 27.15, 'peg': 2.0, 'growth': 13.57}, {'code': '300759', 'name': '康龙化成', 'pe': 71.01, 'peg': 2.03, 'growth': 34.97}, {'code': '300751', 'name': '迈为股份', 'pe': 87.43, 'peg': 2.04, 'growth': 42.87}, {'code': '688777', 'name': '中控技术', 'pe': 58.01, 'peg': 2.08, 'growth': 27.88}, {'code': '603605', 'name': '珀莱雅', 'pe': 54.48, 'peg': 2.19, 'growth': 24.88}, {'code': '688111', 'name': '金山办公', 'pe': 75.95, 'peg': 2.22, 'growth': 34.28}, {'code': '300015', 'name': '爱尔眼科', 'pe': 71.69, 'peg': 2.26, 'growth': 31.72}, {'code': '300973', 'name': '立高食品', 'pe': 63.87, 'peg': 2.3, 'growth': 27.79}, {'code': '688690', 'name': '纳微科技', 'pe': 153.16, 'peg': 2.32, 'growth': 66.15}, {'code': '300347', 'name': '泰格医药', 'pe': 45.76, 'peg': 2.34, 'growth': 19.57}, {'code': '600519', 'name': '贵州茅台', 'pe': 40.26, 'peg': 2.56, 'growth': 15.74}, {'code': '603127', 'name': '昭衍新药', 'pe': 83.68, 'peg': 2.63, 'growth': 31.78}, {'code': '603288', 'name': '海天味业', 'pe': 57.18, 'peg': 2.83, 'growth': 20.24}, {'code': '600893', 'name': '航发动力', 'pe': 92.09, 'peg': 3.21, 'growth': 28.68}, {'code': '600436', 'name': '片仔癀', 'pe': 92.4, 'peg': 3.4, 'growth': 27.17}, {'code': '002371', 'name': '北方华创', 'pe': 154.65, 'peg': 4.04, 'growth': 38.28}, {'code': '603290', 'name': '斯达半导', 'pe': 158.53, 'peg': 4.05, 'growth': 39.14}, {'code': '688012', 'name': '中微公司', 'pe': 122.47, 'peg': 5.38, 'growth': 22.76}, {'code': '300253', 'name': '卫宁健康', 'pe': 39.21, 'peg': 6.55, 'growth': 5.99}, {'code': '603606', 'name': '东方电缆', 'pe': 26.72, 'peg': 17.58, 'growth': 1.52}]
for i in p:
    print(f"{i['code']}.SH" if i['code'].startswith('6') else f"{i['code']}.SZ", i['name'], i['peg'])