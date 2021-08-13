# 导入需要的模块
import requests
from datetime import date,datetime, time,timedelta
from bs4 import BeautifulSoup
import re
import math
import time
import numpy as np


def get_html(code, start_date, end_date, page=1, per=20):
    url = 'http://fund.eastmoney.com/f10/F10DataApi.aspx?type=lsjz&code={0}&page={1}&sdate={2}&edate={3}&per={4}'.format(
        code, page, start_date, end_date, per)
    rsp = requests.get(url)
    html = rsp.text
    return html
 
 
def get_fund(code, start_date=str(date.today()-timedelta(180)), end_date=str(date.today()), page=1, per=20):
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
    record_data = []
    for i in range(len(records)):
        tmp = {}
        tmp['day'] = records[i][0]
        tmp['close'] = records[i][1]
        tmp['applies_rate'] = str(records[i][3]).replace("%", "")
        if i > 0:
            tmp['applies'] = round(float(records[i][1])-float(records[i-1][1]), 4)
        record_data.append(tmp)
    del record_data[0]
    return record_data


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


def output_six_style_index_info():
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

def RSI_BY_DICT(data):
    rsi_day = 14
    up = [i if i > 0 else 0 for i in [i["applies"] for i in data[:14]]]
    down = [i * -1 if i < 0 else 0 for i in [i["applies"] for i in data[:14]]]
    smooth_up_14 = sum(up) / len(up)
    smooth_down_14 = sum(down) / len(down)
    new_data = []
    for i in range(len(data)):
        tmp_list = {}
        tmp_list["day"] = data[i]["day"]
        up_column = data[i]["applies"] if data[i]["applies"] > 0 else 0
        tmp_list["up_column"] = up_column
        down_column = data[i]["applies"] * -1 if data[i]["applies"] < 0 else 0
        tmp_list["down_column"] = down_column
        if i == 13:
            smooth_up = smooth_up_14
            smooth_down = smooth_down_14
        elif i > 13:
            smooth_up = (new_data[i - 1]["smooth_up"] * (rsi_day - 1) + up_column) / rsi_day
            smooth_down = (new_data[i - 1]["smooth_down"] * (rsi_day - 1) + down_column) / rsi_day
        else:
            smooth_up = smooth_down = None
        tmp_list["smooth_up"] = smooth_up
        tmp_list["smooth_down"] = smooth_down
        relative_intensity = smooth_up / smooth_down if (smooth_up is not None or smooth_down is not None) else None
        tmp_list["relative_intensity"] = relative_intensity
        if relative_intensity:
            tmp_list["RSI"] = round(100 - (100 / (1 + relative_intensity)), 2)
        new_data.append(tmp_list)
    # for i in new_data:
    #     print(i)
    return new_data[-1]['RSI']



def etf_fund_applies():
    # 查询主流行业ETF最近一个月的涨跌幅
    funds = [
        {"name": "创成长","code": 159967},
        {"name": "质量ETF","code": 515910},
        {"name": "建信中证红利潜力指数","code": "007671"},
        {"name": "光伏ETF", "code": 515790},
        {"name": "医疗ETF","code": 159828},
        {"name": "生物医药ETF","code": 161726},
        {"name": "有色金属ETF","code": 512400},
        {"name": "家电ETF","code": 159996},
        {"name": "新能车ETF", "code": 515700},
        {"name": "白酒基金", "code": 161725},
        {"name": "酒ETF", "code": 512690},
        {"name": "农业ETF","code": 159825},
        {"name": "钢铁ETF", "code": 515210},
        {"name": "煤炭ETF","code": 515220},
        {"name": "银行ETF","code": 512800},
        {"name": "证券ETF","code": 159841},
        {"name": "房地产ETF","code": 512200},
        {"name": "恒生互联ETF","code": 513330},
        {"name": "5G ETF", "code": 515050},
        {"name": "军工ETF","code": 512660},
        {"name": "芯片ETF", "code": 159995},
        {"name": "化工ETF", "code": 159870},
        {"name": "游戏ETF", "code": 159869},
    ]
    ETF_list = []
    for fund in funds:
        applies = get_fund(fund.get("code"))
        print(applies)
        rsi_value = RSI_BY_DICT(applies)
        applies_month = applies[-22:]
        applies_week = applies[-5:]
        fund_month_applies = round(sum([float(i['applies_rate']) for i in applies_month]), 2)
        fund_week_applies = round(sum([float(i['applies_rate']) for i in applies_week]), 2)
        tmp = {}
        tmp['name'] = fund.get('name')
        tmp['code'] = fund.get('code')
        tmp['month_applies'] = fund_month_applies
        tmp['week_applies'] = fund_week_applies
        tmp['RSI'] = rsi_value
        ETF_list.append(tmp)
    return sorted(ETF_list, key=lambda x:x['week_applies'], reverse=True)


if __name__ == '__main__':
    data = etf_fund_applies()
    for i in data:
        print(i)
