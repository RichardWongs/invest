import requests,json
import time

def TRI(high, low, close):
    return round(max(high, close) - min(low, close), 3)


def get_ATR(data, day):
    assert isinstance(data, list) and len(data) > day+1
    return round(sum([i['TRi'] for i in data[-(day+1):-1]]) / len(data[-(day+1):-1]), 3)


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
    return data


def turtleTransaction(code, model):
    assert model in (1,2)
    day, sign_out_day = 0, 0
    if model == 1:
        day, sign_out_day = 20, 10
    if model == 2:
        day, sign_out_day = 60, 20
    data = get_stock_kline_day(code)
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
    sign_out_price = min([i['low'] for i in data[-sign_out_day:]])
    print(f"区间最高价: {highest_price}, 当前价格: {current_price}, ATR: {ATR}")
    print(f"入市价: {in_price1}, {in_price2}, {in_price3}, {in_price4}")
    print(f"止损价: {stop_loss_price1}, {stop_loss_price2}, {stop_loss_price3}, {stop_loss_price4}")
    print(f"止盈退出价: {sign_out_price}")



