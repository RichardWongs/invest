from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import date,datetime
import requests,json
import time
import logging
import colorama
from colorama import Fore,Back,Style
colorama.init()
logging.basicConfig(level=logging.INFO)


def TRI(high, low, close):
    return round(max(high, close) - min(low, close), 3)


def get_stock_kline_60_minutes(code):
    if str(code)[0] in ('0','1','3'):
        secid = f'0.{code}'
    else:
        secid = f'1.{code}'
    url = f"http://65.push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        'cb': "jQuery112403682476595453782_1625125440575",
        'secid': secid,
        'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
        'fields1': 'f1,f2,f3,f4,f5,f6',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
        'klt': 60,
        'fqt': 0,
        'end': '20500101',
        'lmt': 120,
        '_': f'{int(time.time())*1000}'
    }
    try:
        r = requests.get(url, params=params).text
        r = r.split('(')[1].split(')')[0]
        r = json.loads(r)
        r = r['data']['klines']
        data = []
        for i in range(len(r)):
            tmp = {}
            current_data = r[i].split(',')
            tmp['day'] = current_data[0]
            tmp['close'] = float(current_data[2])
            tmp['high'] = float(current_data[3])
            tmp['low'] = float(current_data[4])
            if i > 0:
                tmp['last_close'] = float(r[i - 1].split(',')[2])
                tmp['TRi'] = TRI(tmp['high'], tmp['low'], tmp['last_close'])
            data.append(tmp)
        data = data[1:]
    except Exception() as e:
        print(e)
    return data if data else None


def get_stock_kline_day(code):
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
        'lmt': 120,
        '_': f'{int(time.time())*1000}'
    }
    try:
        r = requests.get(url, params=params).text
        # print(r)
        r = r.split('(')[1].split(')')[0]
        r = json.loads(r)
        r = r['data']['klines']
        data = []
        for i in range(len(r)):
            tmp = {}
            current_data = r[i].split(',')
            tmp['day'] = current_data[0]
            tmp['close'] = float(current_data[2])
            tmp['high'] = float(current_data[3])
            tmp['low'] = float(current_data[4])
            if i > 0:
                tmp['last_close'] = float(r[i - 1].split(',')[2])
                tmp['TRi'] = TRI(tmp['high'], tmp['low'], tmp['last_close'])
            data.append(tmp)
        data = data[1:]
    except Exception() as e:
        print(e)
    return data if data else None


def turtleTransaction(code, model=1, period=1):
    TotalAmountAccount = 10000 # 账户总金额
    assert model in (1,2)
    day, sign_out_day = 0, 0
    if model == 1:
        day, sign_out_day = 20, 10
    if model == 2:
        day, sign_out_day = 60, 20
    can_lost_money = 1/100*TotalAmountAccount
    if period == 1:
        data = get_stock_kline_60_minutes(code)
    if period == 2:
        data = get_stock_kline_day(code)
    # print(data,'\n', len(data), '\n')
    prices = []
    for i in data[-(day+1):-1]:
        prices.append(i['close'])
        prices.append(i['high'])
        prices.append(i['low'])
    highest_price = max(prices)
    current_price = data[-1]['close']
    ATR = round(sum([i['TRi'] for i in data[-(day+1):-1]]) / len(data[-(day+1):-1]), 3)
    in_price1 = highest_price + 0.001
    in_price2 = round(in_price1 + 0.5 * ATR, 3)
    in_price3 = round(in_price2 + 0.5 * ATR, 3)
    in_price4 = round(in_price3 + 0.5 * ATR, 3)
    stop_loss_price1 = round(in_price1 - 2 * ATR, 3)
    stop_loss_price2 = round(in_price2 - 2 * ATR, 3)
    stop_loss_price3 = round(in_price3 - 2 * ATR, 3)
    stop_loss_price4 = round(in_price4 - 2 * ATR, 3)
    input_amount = round(can_lost_money/(in_price1-stop_loss_price1)*in_price1)  # 本次交易可投入仓位总金额
    sign_out_price = min([i['low'] for i in data[-sign_out_day:]])
    print(f"区间最高价: {highest_price}, 当前价格: {current_price}, ATR: {ATR}")
    print(f"入市价: {in_price1}, {in_price2}, {in_price3}, {in_price4}")
    print(f"止损价: {stop_loss_price1}, {stop_loss_price2}, {stop_loss_price3}, {stop_loss_price4}")
    print(f"止盈退出价: {sign_out_price}")
    print(f"本次交易可投入金额: {input_amount}, 单次建仓投入金额: {input_amount/4}")
    trigger = current_price>highest_price
    trigger = Back.GREEN+ str(trigger) +Style.RESET_ALL if trigger else Back.RED+ str(trigger) +Style.RESET_ALL
    print(f"是否触发建仓条件? {trigger}")


def turtle_run():
    funds = [
        {'code': 159967, 'name': '创成长'},
        {'code': 515910, 'name': '质量ETF'},
        {'code': 588000, 'name': '科创50ETF'},
        {'code': 512690, 'name': '酒ETF'},
        {'code': 159885, 'name': '低碳ETF'},
        {"code": 516390, "name": "新能源汽车ETF"},
        {"code": 515790, "name": "光伏ETF"},
        {"code": 512170, "name": "医疗ETF"},
        {"code": 159995, "name": "芯片ETF"},
        {"code": 513010, "name": "恒生科技30ETF"},
        {"code": 513060, "name": "恒生医疗ETF"},
    ]
    for i in funds:
        print(f"{i['name']}")
        turtleTransaction(code=i['code'], model=1, period=2)
        # model(1,2):海龟交易系统的系统1与系统2, period(1,2):获取交易品种的60分钟价格或日价格走势
        print()


def EarlETF_turtle(fund):
    data = get_stock_kline_60_minutes(fund['code'])
    hour_close = data[-1]['close']
    hour_10_average = round(sum([i['close'] for i in data[-10:]])/len(data[-10:]),3)
    hour_100_average = round(sum([i['close'] for i in data[-100:]])/len(data[-100:]),3)
    hour_50 = []
    for i in data[-51:-1]:
        hour_50.append(i['high'])
        hour_50.append(i['low'])
    hour_50_high = max(hour_50)
    hour_50_low = min(hour_50)
    hour_25 = []
    for i in data[-26:-1]:
        hour_25.append(i['low'])
    hour_25_low = min(hour_25)
    if hour_10_average > hour_100_average:
        if hour_close > hour_50_high:
            print(fund['name'])
            print(Fore.LIGHTRED_EX +'达到买入条件'+ Style.RESET_ALL)
            print(f"当前收盘价:{hour_close}\n10小时平均:{hour_10_average}\n100小时平均:{hour_100_average}")
            print(f"50小时最高:{hour_50_high}\n25小时最低:{hour_25_low}\n50小时最低:{hour_50_low}\n\n")
        # else:
        #     print(fund['name'])
        #     print(f"买入价格: {round(hour_50_high+0.001,3)}\n\n")
    elif hour_50_low < hour_close < hour_25_low:
        print(fund['name'])
        print(Fore.LIGHTGREEN_EX +'减仓一半'+ Style.RESET_ALL)
        print(f"当前收盘价:{hour_close}\n10小时平均:{hour_10_average}\n100小时平均:{hour_100_average}")
        print(f"50小时最高:{hour_50_high}\n25小时最低:{hour_25_low}\n50小时最低:{hour_50_low}\n\n")
    elif hour_close < hour_50_low:
        print(fund['name'])
        print(Fore.LIGHTGREEN_EX +'清仓'+ Style.RESET_ALL)
        print(f"当前收盘价:{hour_close}\n10小时平均:{hour_10_average}\n100小时平均:{hour_100_average}")
        print(f"50小时最高:{hour_50_high}\n25小时最低:{hour_25_low}\n50小时最低:{hour_50_low}\n\n")
    else:
        # print(Fore.LIGHTBLUE_EX +"保持现状"+ Style.RESET_ALL)
        pass

def get_trade_time():
    from datetime import datetime, timedelta
    timed = []
    ten_prev = datetime.strptime(str(datetime.now().date()) + "10:30", '%Y-%m-%d%H:%M')
    ten_next = ten_prev + timedelta(minutes=1)
    eleven_prev = datetime.strptime(str(datetime.now().date()) + "11:30", '%Y-%m-%d%H:%M')
    eleven_next = ten_prev + timedelta(minutes=1)
    two_prev = datetime.strptime(str(datetime.now().date()) + "14:00", '%Y-%m-%d%H:%M')
    two_next = two_prev + timedelta(minutes=1)
    three_prev = datetime.strptime(str(datetime.now().date()) + "14:55", '%Y-%m-%d%H:%M')
    three_next = three_prev + timedelta(minutes=1)
    timed.append((ten_prev, ten_next))
    timed.append((eleven_prev, eleven_next))
    timed.append((two_prev, two_next))
    timed.append((three_prev, three_next))
    if date.today().weekday() in (0,1,2,3,4):
        now = datetime.now()
        for i in timed:
            if i[0] <= now <= i[1]:
                return True
    return False

def Earl_Run():
    funds = [
        {'code': 159967, 'name': '创成长'},
        {'code': 515910, 'name': '质量ETF'},
        {'code': 159721, 'name': '深创100'},
        {"code": 516390, "name": "新能源汽车ETF"},
        {"code": 515790, "name": "光伏ETF"},
        {"code": 516820, "name": "医疗创新ETF"},
        {"code": 513010, "name": "恒生科技30ETF"},
        {"code": 513330, "name": "恒生医疗ETF"},
        {'code': 506001, 'name': '万家科创板'}
    ]
    for i in funds:
        EarlETF_turtle(i)
        # time.sleep(2)


if __name__ == "__main__":
    # sched = BlockingScheduler()
    # sched.add_job(turtle_run, "interval", minutes=30)
    # sched.add_job(Earl_Run, "interval", minutes=30)
    # sched.start()
    Earl_Run()
