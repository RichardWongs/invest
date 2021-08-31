import time
import pickle
import requests
import json
from datetime import date, timedelta
from security import get_stock_kline_with_volume


def get_research_report(code):
    # 获取个股研报数据
    beginTime = date.today() - timedelta(days=60)
    endTime = date.today()
    timestamp = int(time.time()*1000)
    url = f"http://reportapi.eastmoney.com/report/list?cb=datatable4737182&pageNo=1&pageSize=50&code={code}&industryCode=*&industry=*&rating=*&ratingchange=*&beginTime={beginTime}&endTime={endTime}&fields=&qType=0&_={timestamp}"
    response = requests.get(url)
    response = response.text.split('(')[1].split(')')[0]
    response = json.loads(response)
    if 'data' in response.keys():
        response = response.get('data')
        return response
    return None


def get_predict_eps(code):
    data = get_research_report(code)
    predictThisYearEps = []
    predictNextYearEps = []
    for i in data:
        predictThisYearEps.append(float(i['predictThisYearEps']))
        predictNextYearEps.append(float(i['predictNextYearEps']))
    avg_predictThisYearEps = round(sum(predictThisYearEps)/len(predictThisYearEps), 2)
    avg_predictNextYearEps = round(sum(predictNextYearEps)/len(predictNextYearEps), 2)
    print(f"今年收益预测:{avg_predictThisYearEps}元\n明年收益预测:{avg_predictNextYearEps}元")
    return avg_predictThisYearEps, avg_predictNextYearEps


def select_stock_last_year_eps(code):
    # 查询个股上一年度的每股收益
    years = ['2019', '2020']
    eps = {'2019': None, '2020': None}
    for year in years:
        target_file = f"annual_report_{year}.bin"
        with open(target_file, 'rb') as f:
            file = f.read()
            content = pickle.loads(file)
        for i in content:
            if i.get('SECURITY_CODE') == str(code):
                eps[year] = i.get('BASIC_EPS')
                # eps[f"{year}_deduct"] = i.get('DEDUCT_BASIC_EPS')
    return eps


def calculate_peg(code):
    year = str(date.today().year - 1)
    history_eps = select_stock_last_year_eps(code)
    last_year_eps = history_eps.get(year)
    close_price = get_stock_kline_with_volume(code, limit=5)[-1]['close']
    thisYearWeight = 4  # 今年剩下的月数
    nextYearWeight = 12 - thisYearWeight  # 未来12个月中明年所占的月数
    avg_predictThisYearEps, avg_predictNextYearEps = get_predict_eps(code)
    predict_the_coming_year_eps = round(avg_predictThisYearEps*nextYearWeight/12 + avg_predictNextYearEps*thisYearWeight/12, 2)
    print(f"预测未来一年的收益: {predict_the_coming_year_eps}")
    predict_pe = round(close_price/predict_the_coming_year_eps, 2)
    print(f"预测未来一年的市盈率: {predict_pe}")
    past_year = round(avg_predictThisYearEps*nextYearWeight/12 + last_year_eps*thisYearWeight/12, 2)
    print(f"过去一年的收益: {past_year}")
    growth_rate_earnings_per_share = round((predict_the_coming_year_eps - past_year)/past_year * 100, 2)
    print(f"未来每股收益增长率: {growth_rate_earnings_per_share}%")
    peg = round(predict_pe/growth_rate_earnings_per_share, 2)
    print(f"peg: {peg}")


calculate_peg(601636)


