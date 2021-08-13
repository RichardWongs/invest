# encoding:utf-8
import requests,json,time
from Stock.mapping import StockObject
from datetime import datetime,date,timedelta
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()


# MYSQL_HOST = "172.16.1.162"
# PORT = 3306
# USERNAME = 'root'
# PASSWORD = '123456'
#
# class Stock(Base):
#     __tablename__ = "stocks"
#
#     STOCK_CODE = Column(Integer,primary_key=True, nullable=False)
#     STOCK_NAME = Column(String(20),nullable=False)
#     CURRENT_PRICE = Column(Float, default=None)
#     DAY_20_APPLIES = Column(Float,default=0)
#     DAY_50_APPLIES = Column(Float, default=None)
#     DAY_120_APPLIES = Column(Float, default=None)
#     DAY_250_APPLIES = Column(Float, default=None)
#     DAY_250_HIGHEST_PRICE = Column(Float, default=None)
#     IS_NEW = Column(Integer,default=None)
#     UPDATE_TIME = Column(Date(), default=None)
#     INDUSTRY = Column(String(50), default=None)
#
# class DB(object):
#     def __init__(self):
#         self.engine = create_engine(f'mysql+pymysql://{USERNAME}:{PASSWORD}@{MYSQL_HOST}:{PORT}/stock')
#         self.DBSession = sessionmaker(bind=self.engine)
#         self.session = self.DBSession()
#
#     def addDB(self, code, name, applies=float(0), is_new=0):
#         data = Stock(STOCK_CODE=code,
#                      STOCK_NAME=name,
#                      DAY_20_APPLIES=applies,
#                      IS_NEW=is_new,
#                      UPDATE_TIME=datetime.now())
#         self.session.add(data)
#         self.session.commit()
#         self.session.close()
#
#     def updateDB(self, stock):
#         try:
#             if stock.code and stock.name:
#                 self.session.query(Stock).filter(Stock.STOCK_CODE==stock.code).update(
#                     {'STOCK_NAME': stock.name,
#                      'CURRENT_PRICE': stock.current_price,
#                      'DAY_20_APPLIES': stock.day_20_applies,
#                      'DAY_50_APPLIES': stock.day_50_applies,
#                      'DAY_120_APPLIES': stock.day_120_applies,
#                      'DAY_250_APPLIES': stock.day_250_applies,
#                      'DAY_250_HIGHEST_PRICE': stock.day_250_highest_price,
#                      'IS_NEW': stock.is_new,
#                      'UPDATE_TIME': stock.update_time}
#                 )
#                 self.session.commit()
#                 self.session.close()
#         except Exception() as e:
#             print(e)
#
#     def selectDB(self, code):
#         stock = self.session.query(Stock).filter(Stock.code==code).first()
#         self.session.close()
#         return stock
#
# class StockObject(object):
#     def __init__(self):
#         self.code = None
#         self.name = None
#         self.current_price = None
#         self.day_20_applies = None
#         self.day_50_applies = None
#         self.day_120_applies = None
#         self.day_250_applies = None
#         self.day_250_highest_price = None
#         self.is_new = 0
#         self.industry = None
#         self.update_time = datetime.now()


def get_all_stock():
    url = f"https://api.doctorxiong.club/v1/stock/all"
    responose = requests.get(url).json()
    data = [i[0].replace('sh','').replace('sz','') for i in responose['data']]
    data = [i for i in data if i[0] in ('6', '0', '3')]
    return data

def get_stock_detail():
    url = f"https://api.doctorxiong.club/v1/stock"
    params = {
        'code': '600000'
    }
    response = requests.get(url, params=params).json()
    print(response)

def get_stock_rank():
    url = f"https://api.doctorxiong.club/v1/stock/rank"
    body = {
        'node': 'a',
        'sort': 'priceChange'
    }
    response = requests.post(url, json=body).json()
    print(response)


def get_stock_kline_day(stock, limit=300):
    # from .mapping import StockObject
    assert isinstance(stock, StockObject)
    if str(stock.code)[0] in ('0','1','3'):
        secid = f'0.{stock.code}'
    else:
        secid = f'1.{stock.code}'
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
    try:
        r = requests.get(url, params=params).text
        r = r.split('(')[1].split(')')[0]
        r = json.loads(r)
        r = r['data']
        if r and isinstance(r, dict):
            stock.name = r['name']
            r = r['klines']
            # print(r)
        else:
            return None
        data = []
        for i in range(len(r)):
            tmp = {}
            current_data = r[i].split(',')
            tmp['day'] = current_data[0]
            tmp['close'] = float(current_data[2])
            tmp['high'] = float(current_data[3])
            tmp['low'] = float(current_data[4])
            tmp['volume'] = float(current_data[6])
            if i > 0:
                tmp['last_close'] = float(r[i - 1].split(',')[2])
            data.append(tmp)
        return data[1:]
    except Exception() as e:
        print(e)
        return None

def get_20_day_applies(stock):
    from .mapping import StockObject
    assert isinstance(stock, StockObject)
    time.sleep(1)
    data = get_stock_kline_day(stock)
    if data and len(data) > 20:
        if datetime.strptime(data[-1]['day'], '%Y-%m-%d') < (datetime.today()-timedelta(days=3)):
            return None
        stock.current_price = data[-1]['close']
        day_20_applies = round((data[-1]['close']-data[-20]['last_close'])/data[-20]['last_close']*100, 2)
        stock.day_20_applies = day_20_applies
        if len(data) > 50:
            day_50_applies = round((data[-1]['close']-data[-50]['last_close'])/data[-50]['last_close']*100, 2)
            stock.day_50_applies = day_50_applies
        if len(data) > 120:
            day_120_applies = round((data[-1]['close'] - data[-120]['last_close']) / data[-120]['last_close'] * 100, 2)
            stock.day_120_applies = day_120_applies
        if len(data) > 250:
            day_250_applies = round((data[-1]['close'] - data[-250]['last_close']) / data[-250]['last_close'] * 100, 2)
            stock.day_250_applies = day_250_applies
            highest = data[-251]['high']
            for i in data[-251:-1]:
                if i['high'] > highest:
                    highest = i['high']
            stock.day_250_highest_price = highest
        if len(data) <= 180:
            stock.is_new = 1
        else:
            stock.is_new = 0
        # return stock

def run():
    from .mapping import StockObject
    from .database import DB
    stocks = get_all_stock()
    db = DB()
    for i in stocks:
        s = StockObject()
        s.code = i
        get_20_day_applies(s)
        if s:
            db.updateDB(s)
            print(s.code,s.name,s.current_price)
            del s
        else:
            print(i, "获取K线失败!")



def get_all_fund_list():
    url = "http://fund.eastmoney.com/js/fundcode_search.js"
    response = requests.get(url)
    response = response.text.split("=")[1].replace(';', '')
    response = json.loads(response)
    funds = []
    for i in response:
        tmp = {}
        tmp['code'] = i[0]
        tmp['name'] = i[2]
        tmp['type'] = i[3]
        funds.append(tmp)
    return funds


def read_txt():
    filename = r"D:\trade_funds.txt"
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
        contents = content.split('\n')
        data = []
        for i in contents:
            if i:
                tmp = {}
                tmp['code'], tmp['name'], tmp['type'] = i.split(' ')
                data.append(tmp)
        return data


def fund_volume():
    # 查询统计所有场内基金,过滤十日平均成交额低于一千万的场内基金
    funds = read_txt()  # get_all_fund_list()
    for i in funds:
        if (i['code'].startswith('1') or i['code'].startswith('5')) and i['type'] not in ('货币型', 'REITs'):
            s = StockObject()
            s.code = i['code']
            s.name = i['name']
            data = get_stock_kline_day(s, limit=30)
            if data:
                s.volume = f"{round(sum([i['volume'] for i in data[-10:]])/10/10000, 2)}万"
                if round(sum([i['volume'] for i in data[-10:]])/10/10000, 2) > 1000:
                    print(i['code'], i['name'], i['type'], s.volume)

