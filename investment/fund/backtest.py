import requests,json,time
# 股债轮动策略 来源: 微信公众号 闲画财经

class MyAccount(object):
    position = 0  # 0 空仓 1 创业板 2 上证50

def TRI(high, low, close):
    return round(max(high, close) - min(low, close), 3)

def get_stock_kline_day(code, limit):
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
    days = 21
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
            tmp['TRi'] = TRI(tmp['high'], tmp['low'], tmp['last_close'])
        if i> days:
            last_month_close = float(r[i-days].split(',')[2])
            # print(r[i-days-1].split(','))
            # print(tmp)
            # print()
            tmp['applies'] = round((tmp['close']-last_month_close)/last_month_close*100, 2)
            # print(tmp['day'],tmp['close'],r[i-days].split(',')[0], last_month_close)
        data.append(tmp)
    data = data[1:]
    return data

def BackTest():
    funds = [
        {'name': '创成长', 'code': 159967},
        {'name': '质量ETF', 'code': 510050},
        # {'name': '质量ETF', 'code': 515910},
        # {"name": "恒生科技30ETF", "code": 513010}
    ]
    limit = 200
    fund_detail = []
    for i in funds:
        fund_detail.append(get_stock_kline_day(i['code'], limit))
    cyb,sz50 = fund_detail[0], fund_detail[1]
    for i in range(len(cyb)):
        if 'applies' in cyb[i].keys() and 'applies' in sz50[i].keys():
            if cyb[i]['applies'] <0 and sz50[i]['applies'] <0:
                # 判断是否最近的跌幅较大影响到月度收益,如果是,则空仓
                # 清空持仓是因为所持有的标的近期表现不佳导致最近22个交易日累计总涨幅为负,而不是因为一个月前表现较好的涨幅的交易日被调出
                if MyAccount.position == 1:
                    if cyb[i]['day_applies'] < cyb[i-22]['day_applies'] and cyb[i]['day_applies'] <0:
                        print(f"{cyb[i]['day']}  空仓")
                        MyAccount.position = 0
                elif MyAccount.position == 2:
                    if sz50[i]['day_applies'] < sz50[i-22]['day_applies'] and sz50[i]['day_applies'] <0:
                        print(f"{cyb[i]['day']}  空仓")
                        MyAccount.position = 0
                else:
                    pass
            elif cyb[i]['applies'] > sz50[i]['applies']:
                if MyAccount.position != 1:
                    MyAccount.position = 1
                    print(f"{cyb[i]['day']}  {i['name']}  当日涨跌幅  {cyb[i]['day_applies']}  最近一个月涨跌幅  {cyb[i]['applies']}")
            elif cyb[i]['applies'] < sz50[i]['applies']:
                if MyAccount.position != 2:
                    MyAccount.position = 2
                    print(f"{sz50[i]['day']}  {i['name']}  当日涨跌幅  {sz50[i]['day_applies']}  最近一个月涨跌幅  {sz50[i]['applies']}")
            else:
                continue


BackTest()

