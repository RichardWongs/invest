import time
import requests
import json
from datetime import date, timedelta


def get_research_report(code):
    beginTime = date.today() - timedelta(days=30)
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


def calculate_peg(code, close_price, this_year_eps, last_year_eps):
    thisYearWeight = 6  # 今年剩下的月数
    nextYearWeight = 6  # 未来12个月中明年所占的月数
    avg_predictThisYearEps, avg_predictNextYearEps = get_predict_eps(code)
    predict_the_coming_year_eps = round(avg_predictThisYearEps*nextYearWeight/12 + avg_predictNextYearEps*thisYearWeight/12, 2)
    print(f"预测未来一年的收益: {predict_the_coming_year_eps}")
    predict_pe = round(close_price/predict_the_coming_year_eps, 2)
    print(f"预测未来一年的市盈率: {predict_pe}")
    past_year = round(this_year_eps*nextYearWeight/12 + last_year_eps*this_year_eps/12, 2)
    print(f"过去一年的收益: {past_year}")
    growth_rate_earnings_per_share = round((predict_the_coming_year_eps - past_year)/past_year * 100, 2)
    peg = round(predict_pe/growth_rate_earnings_per_share, 2)
    print(f"peg: {peg}")


get_predict_eps(601636)
print("预测未来一年的收益", round(1.86 * 6/12 + 2.05 * 6/12, 2))  # 预测未来一年的收益
print("预测未来一年的市盈率", round(28.17/1.96, 2))  # 预测未来一年的市盈率
print("过去一年的收益", round(0.82 * 6/12 + 0.46 * 6/12, 2))  # 过去一年的收益
# print("未来每股收益增长率", round((1.96 - 0.64)/0.64 * 100, 2))  # 未来每股收益增长率
# print(round(14.37/206.25, 2))
print('\n\n')
calculate_peg(601636, 28.17, 0.82, 0.46)

