import json
import time
import requests
from datetime import date, datetime, timedelta

# 外资白马股策略
class ForeignCapitalStrategy:
    pass


def get_trade_date(N, include_today=False):
    # 获取最近N个交易日
    trade_day = []
    for i in range(N * 2):
        day = date.today()-timedelta(days=i)
        if day.weekday()+1 in (1, 2, 3, 4, 5):
            trade_day.append(day)
    return trade_day[:N] if include_today else trade_day[1:N+1]


def foreignCapitalHolding():
    # 外资持股清单(持股市值超过5000万)
    url = "http://dcfm.eastmoney.com/em_mutisvcexpandinterface/api/js/get"
    timestamp = int(time.time()*1000)
    params = {
        'callback': f'jQuery1123013917823929726048_{timestamp}',
        'st': 'ShareSZ_Chg_One',
        'sr': -1,
        'ps': 2000,
        'p': 1,
        'type': 'HSGT20_GGTJ_SUM',
        'token': '894050c76af8597a853f5b408b759f5d',
        'filter': f"(DateType='1')(HdDate='{date.today()-timedelta(days=2)}')"
    }
    r = requests.get(url, params=params)
    response = r.text.split('(')[1].split(')')[0]
    response = json.loads(response)
    response = sorted(response, key=lambda x: x['ShareSZ'], reverse=True)
    foreignCapital_pool = []
    for i in response:
        code = i.get('SCode')
        name = i.get('SName')
        holding_market_value = round(i.get('ShareSZ')/100000000, 2)
        float_accounted = round(i.get('LTZB')*100, 2)
        if holding_market_value > 0.5:
            tmp = {'code': code, 'name': name, 'holding_market_value': holding_market_value, 'float_accounted': float_accounted}
            foreignCapital_pool.append(tmp)
            # print(f"{code}\t{name}\t持股市值:{holding_market_value}(亿)\t流通占比:{float_accounted}%")
    return foreignCapital_pool


def HGT(day=date.today()):
    url = f"http://dcfm.eastmoney.com/em_mutisvcexpandinterface/api/js/get"
    time_stamp = int(datetime.today().timestamp()*1000)
    params = {
        'callback': f'jQuery112307201576248685275_{time_stamp}',
        'st': 'DetailDate,Rank',
        'sr': 1,
        'ps': 10,
        'p': 1,
        'type': 'HSGTCJB',
        'sty': 'HGT',
        'token': '70f12f2f4f091e459a279469fe49eca5',
        'filter': f"(MarketType=1)(DetailDate=^{day}^)"
    }
    r = requests.get(url, params=params)
    response = r.text.split('(')[1].split(')')[0]
    response = json.loads(response)
    if len(response) > 0:
        data = []
        for i in response:
            if i['HGTJME'] > 0:
                tmp = {'code': i['Code'], 'name': i['Name'], 'close': i['Close'], 'buying': i['HGTJME'], 'day': i['DetailDate']}
                data.append(tmp)
        sorted_data = sorted(data, key=lambda x: x['buying'], reverse=True)
        return sorted_data


def SGT(day=date.today()):
    url = f"http://dcfm.eastmoney.com/em_mutisvcexpandinterface/api/js/get"
    time_stamp = int(datetime.today().timestamp()*1000)
    params = {
        'callback': f'jQuery112307201576248685275_{time_stamp}',
        'st': 'DetailDate,Rank',
        'sr': 1,
        'ps': 10,
        'p': 1,
        'type': 'HSGTCJB',
        'sty': 'SGT',
        'token': '70f12f2f4f091e459a279469fe49eca5',
        'filter': f"(MarketType=3)(DetailDate=^{day}^)"
    }
    r = requests.get(url, params=params)
    response = r.text.split('(')[1].split(')')[0]
    response = json.loads(response)
    if len(response) > 0:
        data = []
        for i in response:
            if i['SGTJME'] > 0:
                tmp = {'code': i['Code'], 'name': i['Name'], 'close': i['Close'], 'buying': i['SGTJME'], 'day': i['DetailDate']}
                data.append(tmp)
        sorted_data = sorted(data, key=lambda x: x['buying'], reverse=True)
        return sorted_data


def run(N):
    days = get_trade_date(N)
    sh = []
    sz = []
    for i in days:
        h = HGT(i)
        s = SGT(i)
        time.sleep(2)
        sh.append(h)
        sz.append(s)
    print(sh)
    print(sz)


if __name__ == '__main__':
    run(2)



