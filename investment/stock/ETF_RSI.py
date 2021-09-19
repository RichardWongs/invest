from datetime import date, timedelta,datetime
import requests,json
import time
from bs4 import BeautifulSoup
import re
import math
import numpy as np
from apscheduler.schedulers.blocking import BlockingScheduler
import logging
import colorama
from colorama import Fore,Back,Style
colorama.init()
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


def get_current_price(code):
    code = f'sz{code}' if str(code).startswith('1') else f'sh{code}'
    url = f"https://hq.sinajs.cn/?list={code}"
    r = requests.get(url)
    content = r.text.split('"')[1]
    content = content.split(',')
    tmp = {}
    tmp['last_close'] = float(content[2])
    tmp['close'] = float(content[3])
    tmp['day'] = content[-3]
    tmp['applies'] = round(tmp['close'] - tmp['last_close'], 4)
    tmp['applies_rate'] = round((tmp['close']-tmp['last_close']) / tmp['last_close'] * 100, 2)
    return tmp


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
            tmp['last_close'] = float(records[i-1][1])
            tmp['applies'] = round(float(records[i][1])-float(records[i-1][1]), 4)
            tmp['applies_rate'] = round((float(records[i][1])-float(records[i-1][1]))/float(records[i-1][1])*100, 2)
        record_data.append(tmp)
    del record_data[0]
    record_data.append(get_current_price(code))
    return record_data


def get_fund_month_results(code, year, month):
    if month in (1,3,5,7,8,10,12):
        end_day = 31
    elif month in (4,6,9,11):
        end_day = 30
    else:
        end_day = 29 if year % 4 == 0 else 28
    start_date = datetime(year, month, 1).strftime("%Y-%m-%d")
    end_date = datetime(year, month, end_day).strftime("%Y-%m-%d")
    data = get_fund(code, start_date, end_date)
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
    # print(json.dumps(response, indent=4, ensure_ascii=False))


def phase_applies(data):
    # 阶段涨跌幅
    phase_open = data[0]['last_close']
    phase_close = data[-1]['close']
    return round((phase_close-phase_open)/phase_open*100, 2)


def etf_fund_applies():
    # 观察标的最近5个交易日的涨跌幅
    # 查询主流行业ETF最近一个月/一周的涨跌幅
    funds = [
        {"name": "光伏ETF", "code": 515790},
        {"name": "酒ETF", "code": 512690},
        {"name": "医疗ETF","code": 512170},
        {"name": "生物医药ETF","code": 512290},
        {"name": "有色金属ETF","code": 512400},
        {"name": "家电ETF","code": 159996},
        {"name": "新能源车ETF", "code": 515030},
        {"name": "农业ETF","code": 159825},
        {"name": "钢铁ETF", "code": 515210},
        {"name": "煤炭ETF","code": 515220},
        {"name": "银行ETF","code": 512800},
        {"name": "证券ETF","code": 512880},
        {"name": "房地产ETF","code": 512200},
        {"name": "恒生互联ETF","code": 513330},
        {"name": "5G ETF", "code": 159994},
        {"name": "军工ETF","code": 512660},
        {"name": "芯片ETF", "code": 512760},
        {"name": "游戏ETF", "code": 516010},
    ]
    ETF_list = []
    for fund in funds:
        applies = get_stock_kline_day(fund.get("code"), limit=180)
        rsi_value = RSI_BY_DICT(applies)
        applies_month = applies[-22:]
        applies_week = applies[-5:]
        tmp = {}
        tmp['name'] = fund.get('name')
        tmp['code'] = fund.get('code')
        tmp['month_applies'] = phase_applies(applies_month)
        tmp['week_applies'] = phase_applies(applies_week)
        tmp['RSI'] = rsi_value
        ETF_list.append(tmp)
    data = sorted(ETF_list, key=lambda x:x['week_applies'], reverse=True)
    message = f"{date.today()}\n"
    print(f"\n{date.today()}")
    for i in data:
        week_applies = Fore.LIGHTRED_EX +str(i['week_applies'])+ Style.RESET_ALL if i['week_applies']>0 else Fore.LIGHTGREEN_EX+str(i['week_applies'])+ Style.RESET_ALL
        month_applies = Fore.LIGHTRED_EX +str(i['month_applies'])+ Style.RESET_ALL if i['month_applies']>0 else Fore.LIGHTGREEN_EX+str(i['month_applies'])+ Style.RESET_ALL
        print(f"{i['name']} 周涨幅: {week_applies} 月涨幅: {month_applies} RSI: {i['RSI']}")
        message += f"{i['name']}    5日涨幅: {i['week_applies']}    月涨幅: {i['month_applies']}    RSI: {i['RSI']}\n"
    send_dingtalk_message(message)
    print('\n')
    # return data


def get_stock_kline_day(code, limit=30):
    if str(code)[0] in ('0','1','3'):
        secid = f'0.{code}'
    else:
        secid = f'1.{code}'
    url = f"http://67.push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        'cb': "jQuery11240671737283431526_1624931273440",
        'secid': secid,
        'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
        'fields1': 'f1,f2,f3,f4,f5,f6',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
        'klt': 101,
        'fqt': 0,
        'end': '20500101',
        'lmt': limit,
        '_': f'{int(time.time())*1000}'
    }
    r = requests.get(url, params=params).text
    r = r.split('(')[1].split(')')[0]
    r = json.loads(r)
    r = r['data']['klines']
    data = []
    days = 22
    for i in range(len(r)):
        tmp = {}
        current_data = r[i].split(',')
        tmp['day'] = current_data[0]
        tmp['code'] = code
        tmp['close'] = float(current_data[2])
        tmp['high'] = float(current_data[3])
        tmp['low'] = float(current_data[4])
        tmp['day_applies'] = float(current_data[8])
        if i > 0:
            tmp['last_close'] = float(r[i - 1].split(',')[2])
            tmp['applies'] = round(tmp['close']-tmp['last_close'], 3)
        if i>= 5:
            last_week_applies = float(r[i-5].split(',')[2])
            tmp['week_applies'] = round((tmp['close']-last_week_applies)/last_week_applies*100, 2)
        if i>= days:
            last_month_close = float(r[i-days].split(',')[2])
            tmp['month_applies'] = round((tmp['close']-last_month_close)/last_month_close*100, 2)
        data.append(tmp)
    data = data[1:]
    return data


def ETF_ROTATION():
    # 观察标的最近一个月的涨跌幅
    funds = [
        {'code': 159967, 'name': '创成长'},
        {'code': 515910, 'name': '质量ETF'},
        {'code': 159721, 'name': '深创100'},
        {"code": 516390, "name": "新能源汽车ETF"},
        {"code": 515790, "name": "光伏ETF"},
        {"code": 516820, "name": "医疗创新ETF"},
        {"code": 513010, "name": "恒生科技30ETF"},
        {"code": 513060, "name": "恒生医疗ETF"}
    ]
    message = ""
    print()
    for i in funds:
        data = get_stock_kline_day(i['code'])[-1]
        del data['close']
        del data['high']
        del data['low']
        del data['last_close']
        if 'month_applies' in data.keys():
            if data['month_applies'] <0:
                print(Fore.LIGHTGREEN_EX + f"{i['name']}  {data}" + Style.RESET_ALL)
            else:
                print(Fore.LIGHTRED_EX + f"{i['name']}  {data}" + Style.RESET_ALL)
        elif data['day_applies'] >0:
            print(Fore.LIGHTRED_EX + f"{i['name']}  {data}" + Style.RESET_ALL)
        else:
            print(Fore.LIGHTGREEN_EX + f"{i['name']}  {data}" + Style.RESET_ALL)
        message += f"{i['name']}  {data}\n"
    send_dingtalk_message(message)


def rsi_run():
    # 观察RSI指标运行情况
    funds = [
        {'code': 159967, 'name': '创成长'},
        {'code': 515910, 'name': '质量ETF'},
        {'code': 160632, 'name': '酒LOF'},
        {"code": 516390, "name": "新能源汽车ETF"},
        {"code": 515790, "name": "光伏ETF"},
        {"code": 512170, "name": "医疗ETF"},
        {"code": 513010, "name": "恒生科技30ETF"},
        {"code": 513060, "name": "恒生医疗ETF"},
    ]
    open_time = datetime.strptime(str(datetime.now().date())+"09:30:00", '%Y-%m-%d%H:%M:%S')
    close_time = datetime.strptime(str(datetime.now().date())+"15:00:00", '%Y-%m-%d%H:%M:%S')
    now = datetime.now()#.strftime("%Y-%m-%d %H:%M:%S")
    if now.weekday() in (0,1,2,3,4) and now >= open_time and now <= close_time:
        message = f"{now}\n"
        print(f'{now.strftime("%Y-%m-%d %H:%M:%S")}')
        for i in funds:
            day_rsi  = RSI_BY_DICT(get_fund(i['code']))
            hour_rsi = RSI_BY_DICT(get_hour_k_line_info(i['code']))
            print(f"{i['name']}: 日RSI {day_rsi}   60分钟RSI {hour_rsi}")
            if day_rsi >= 65 or day_rsi <= 45 or hour_rsi < 30 or hour_rsi > 70:
                message += f"{i['name']}: 日RSI  {day_rsi}   60分钟RSI  {hour_rsi}\n"
        if message.split(f'{now}\n')[1]:
            send_dingtalk_message(message)
        print('\n')


if __name__ == '__main__':
    # sched = BlockingScheduler()
    # sched.add_job(etf_fund_applies, "cron", day_of_week='0-4', hour="14", minute="30")
    # sched.add_job(ETF_ROTATION, 'cron', day_of_week='0-4', hour="14", minute="40")
    # sched.start()
    ETF_ROTATION()
    etf_fund_applies()

