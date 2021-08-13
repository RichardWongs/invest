from datetime import date, timedelta
import requests,json
import time
from bs4 import BeautifulSoup
import re
import math
import numpy as np


def get_style_index(index_code, begin_time = date.today()-timedelta(days=180)):
    # 国证指数K线数据
    url = f"http://hq.cnindex.com.cn/market/market/getIndexDailyDataWithDataFormat"
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
    data = list(reversed(data))
    result = []
    for i in data:
        tmp = {}
        tmp['day'] = i[0]
        tmp['close'] = i[5]
        tmp['applies'] = i[6]
        result.append(tmp)
    return result


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
    return new_data

def get_hour_k_line_info(code):
    # 60分钟K线数据
    timestamp = int(time.time()*1000)
    url = f"https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_sz{code}_60_{timestamp}=/CN_MarketDataService.getKLineData"
    params = {
        "symbol": f"sz{code}",
        "scale": 60,
        "ma": "no",
        "datalen": 180
    }
    response = requests.get(url, params=params)
    content = response.text.split("=(")[1].split(");")[0]
    content = json.loads(content)
    for i in range(len(content)):
        del content[i]["volume"]
        del content[i]["open"]
        del content[i]["high"]
        del content[i]["low"]
        if i>0:
            content[i]["applies"] = round(float(content[i]["close"])-float(content[i-1]["close"]), 3)
    del content[0]
    return content

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
        if i > 0:
            tmp['applies'] = round(float(records[i][1])-float(records[i-1][1]), 4)
        record_data.append(tmp)
    del record_data[0]
    return record_data
    



if __name__ == '__main__':
    data = get_fund(code=159949)
    new_data = RSI_BY_DICT(data)
    for i in new_data:
        if "RSI" in i.keys():
            print(i)

    # data = get_style_index(399296)
    # new_data = RSI_BY_DICT(data)
    # for i in new_data:
    #     print(i)
