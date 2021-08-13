from datetime import date, timedelta,datetime
import requests,json
import time
from bs4 import BeautifulSoup
import re
import math
import numpy as np
from apscheduler.schedulers.blocking import BlockingScheduler
import logging
logging.basicConfig(level=logging.INFO)


def get_style_index(index_code):
    # 国证指数K线数据
    url = f"http://hq.cnindex.com.cn/market/market/getIndexDailyDataWithDataFormat"
    begin_time = date.today() - timedelta(days=365)
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
    return list(reversed(data))

def RSI_DAY(data):
    rsi_day = 14
    up = [i if i > 0 else 0 for i in [i[6] for i in data[:14]]]
    down = [i * -1 if i < 0 else 0 for i in [i[6] for i in data[:14]]]
    smooth_up_14 = sum(up) / len(up)
    smooth_down_14 = sum(down) / len(down)
    new_data = []
    for i in range(len(data)):
        tmp_list = {}
        tmp_list["date"] = data[i][0]
        up_column = data[i][6] if data[i][6] > 0 else 0
        tmp_list["up_column"] = up_column
        down_column = data[i][6] * -1 if data[i][6] < 0 else 0
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

def RSI_BY_DICT(data):
    assert data, "data 不能为空"
    rsi_day = 14
    up = [i if i > 0 else 0 for i in [i["applies"] for i in data[:14]]]
    down = [i * -1 if i < 0 else 0 for i in [i["applies"] for i in data[:14]]]
    smooth_up_14 = sum(up) / len(up)
    smooth_down_14 = sum(down) / len(down)
    new_data = []
    for i in range(len(data)):
        tmp_list = {}
        tmp_list["date"] = data[i]["day"]
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
    return new_data[-1]['RSI']

def get_hour_k_line_info(code):
    timestamp = int(time.time()*1000)
    if str(code).startswith('1'):
        code = f"sz{code}"
    else:
        code = f"sh{code}"
    url = f"https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_{code}_60_{timestamp}=/CN_MarketDataService.getKLineData"
    params = {
        "symbol": code,
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
            # content[i]["applies"] = round((float(content[i]["close"])-float(content[i-1]["close"]))/float(content[i-1]["close"]), 3)
            content[i]["applies"] = round((float(content[i]["close"])-float(content[i-1]["close"])), 3)
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
    # print(records)
    record_data = []
    for i in range(len(records)):
        tmp = {}
        tmp['day'] = records[i][0]
        tmp['close'] = records[i][1]
        if i > 0:
            tmp['applies'] = round(float(records[i][1])-float(records[i-1][1]), 4)
            tmp['applies_rate'] = round((float(records[i][1])-float(records[i-1][1]))/float(records[i-1][1])*100, 2)
        record_data.append(tmp)
    del record_data[0]
    return record_data


def get_fund_month_results(code, year=date.today().year, month=date.today().month):
    if month in (1,3,5,7,8,10,12):
        end_day = 31
    elif month in (4,6,9,11):
        end_day = 30
    else:
        end_day = 29 if year % 4 == 0 else 28
    start_date = datetime(year, month, 1).strftime("%Y-%m-%d")
    end_date = datetime(year, month, end_day).strftime("%Y-%m-%d")
    data = get_fund(code, start_date, end_date)
    print(data)
    # print(sum([x['applies_rate'] for x in data]))
    return sum([x['applies_rate'] for x in data])


def get_all_fund_list():
    url = "http://fund.eastmoney.com/js/fundcode_search.js"
    response = requests.get(url)
    response = response.text.split("=")[1].replace(';', '')
    response = json.loads(response)
    funds = []
    for i in response:
        if i[3] in ('混合型', '股票型'):
            tmp = {}
            tmp['code'] = i[0]
            tmp['name'] = i[2]
            funds.append(tmp)
    return funds

def fund_rank():
    # 基金业绩排行榜
    page = 1
    fund_type = 1
    # fund_type: 0 全部  1 股票型  2 债券型  3 混合型  4 指数型  6 QDII  7 LOF
    sort = 13
    # sort: 6 近一周 7 近一月 8 近三月 9 近六月 10 近一年 11 近两年 12 近三年 13 今年来 14 成立以来
    timestamp = int(time.time())*1000
    url = f"http://fund.jrj.com.cn/json/netrank/open?type={fund_type}&mana=0&limit=300&page={page}&sort={sort}&order=1&vname=fundranklist&_={timestamp}"
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.106 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    response.encoding = "utf-8"
    resp = response.text.split('var fundranklist=')[1]
    resp = json.loads(resp)
    for i in resp['list']:
        print(i['fundSName'], i['fundCode'])

def send_dingtalk_message(message):
    url = "https://oapi.dingtalk.com/robot/send"
    headers = {'Content-Type': 'application/json'}
    params = {
        'access_token': 'fa4cee8e6c94d8bef582caf47f22b326cf32d617d867ec7bbe611cc50b0729f8'
    }
    body = {
        'msgtype': 'text',
        'text': {'content': message}
    }
    response = requests.post(url, headers=headers, params=params, data=json.dumps(body)).json()
    print(json.dumps(response, indent=4, ensure_ascii=False))


def etf_fund_applies():
    # 查询主流行业ETF最近一个月/一周的涨跌幅
    funds = [
        {"name": "光伏ETF", "code": 515790},
        {"name": "医疗ETF","code": 510050},
        {"name": "生物医药ETF","code": 161726},
        {"name": "有色金属ETF","code": 512400},
        {"name": "家电ETF","code": 159996},
        {"name": "新能车ETF", "code": 515700},
        {"name": "酒LOF", "code": 160632},
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
        rsi_value = RSI_BY_DICT(applies)
        applies_month = applies[-22:]
        applies_week = applies[-5:]
        fund_month_applies = round(sum([float(i['applies_rate']) for i in applies_month]) * 100, 4)
        fund_week_applies = round(sum([float(i['applies_rate']) for i in applies_week]) * 100, 4)
        tmp = {}
        tmp['name'] = fund.get('name')
        tmp['code'] = fund.get('code')
        tmp['month_applies'] = fund_month_applies
        tmp['week_applies'] = fund_week_applies
        tmp['RSI'] = rsi_value
        ETF_list.append(tmp)
    data = sorted(ETF_list, key=lambda x:x['week_applies'], reverse=True)
    message = f"{date.today()}\n"
    for i in data:
        # print(f"{i['name']} 周涨幅: {i['week_applies']} RSI: {i['RSI']}")
        message += f"{i['name']}    5日涨幅: {i['week_applies']}    RSI: {i['RSI']}\n"
    send_dingtalk_message(message)
    # print('\n')
    # return data


def run():
    funds = [
        {'code': 159967, 'name': '创成长'},
        {'code': 515910, 'name': '质量ETF'},
        {'code': 161725, 'name': '白酒基金'},
        {'code': 588000, 'name': '科创50ETF'},
        {"code": 515700, "name": "新能车ETF"},
        {"code": 515790, "name": "光伏ETF"},
    ]
    open_time = datetime.strptime(str(datetime.now().date())+"09:30:00", '%Y-%m-%d%H:%M:%S')
    close_time = datetime.strptime(str(datetime.now().date())+"15:00:00", '%Y-%m-%d%H:%M:%S')
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if now >= open_time and now <= close_time:
        pass
    message = f"{now}\n"
    for i in funds:
        day_rsi  = RSI_BY_DICT(get_fund(i['code']))
        hour_rsi = RSI_BY_DICT(get_hour_k_line_info(i['code']))
        if day_rsi >= 70 or day_rsi <= 45 or hour_rsi < 30 or hour_rsi > 70:
            # print(f"{i['name']}: 日RSI {day_rsi}   60分钟RSI {hour_rsi}")
            message += f"{i['name']}: 日RSI  {day_rsi}   60分钟RSI  {hour_rsi}\n"
    if message.split(f'{now}\n')[1]:
        send_dingtalk_message(message)
    # print('\n')


if __name__ == '__main__':
    # sched = BlockingScheduler()
    # sched.add_job(run, "interval", minutes=5)
    # sched.add_job(etf_fund_applies, "cron", hour="09", minute="20")
    # sched.start()
    # etf_fund_applies()
    # run()
    get_fund_month_results(159967)
