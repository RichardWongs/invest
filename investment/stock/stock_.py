# encoding:utf-8
import requests,json,time
from _datetime import datetime,date
from sqlalchemy import Column, String, Integer, create_engine, Date, Float
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
import tushare as ts
ts.set_token('b625f0b90069039346d199aa3c0d5bc53fd47212437337b45ba87487')


MYSQL_HOST = "172.16.1.162"
PORT = 3306
USERNAME = 'root'
PASSWORD = '123456'

class Stock(Base):
    __tablename__ = "stocks"

    STOCK_CODE = Column(Integer,primary_key=True, nullable=False)
    STOCK_NAME = Column(String(20),nullable=False)
    DAY_20_APPLIES = Column(Float,default=0)
    IS_NEW = Column(Integer,default=None)
    UPDATE_TIME = Column(Date(), default=None)

class FundHolding(Base):
    __tablename__ = "fund_holding"

    CODE = Column(String(10),primary_key=True, nullable=False)
    NAME = Column(String(50), default=None)
    FUND_HOLDING_COUNT = Column(Float, default=None)
    FUND_HOLDING_RATIO = Column(Float, default=None)
    UPDATE_TIME = Column(Date, default=None)



class DB(object):
    def __init__(self):
        self.engine = create_engine(f'mysql+pymysql://{USERNAME}:{PASSWORD}@{MYSQL_HOST}:{PORT}/stock')
        self.DBSession = sessionmaker(bind=self.engine)
        self.session = self.DBSession()

    def addStock(self, code, name, applies=float(0), is_new=1):
        data = Stock(STOCK_CODE=code,
                     STOCK_NAME=name,
                     DAY_20_APPLIES=applies,
                     IS_NEW=is_new,
                     UPDATE_TIME=datetime.now())
        self.session.add(data)
        self.session.commit()
        self.session.close()


    def updateFundHolding(self, obj:FundHolding):
        if self.session.query(FundHolding).filter(FundHolding.CODE==obj.CODE).first():
            self.session.query(FundHolding).filter(FundHolding.CODE==obj.CODE).update(
                        {FundHolding.NAME: obj.NAME,
                         FundHolding.FUND_HOLDING_COUNT: obj.FUND_HOLDING_COUNT,
                         FundHolding.FUND_HOLDING_RATIO: obj.FUND_HOLDING_RATIO,
                         FundHolding.UPDATE_TIME: obj.UPDATE_TIME})
        else:
            data = FundHolding(CODE=obj.CODE,
                               NAME=obj.NAME,
                               FUND_HOLDING_COUNT=obj.FUND_HOLDING_COUNT,
                               FUND_HOLDING_RATIO=obj.FUND_HOLDING_RATIO,
                               UPDATE_TIME=obj.UPDATE_TIME)
            self.session.add(data)
        self.session.commit()
        self.session.close()



def get_all_stock():
    url = f"https://api.doctorxiong.club/v1/stock/all"
    responose = requests.get(url).json()
    return responose['data']

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
        'lmt': 200,
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
            data.append(tmp)
        return data[1:]
    except Exception() as e:
        print(e)
        return None

def get_20_day_applies(code):
    time.sleep(1)
    data = get_stock_kline_day(code)
    if data and len(data) > 20:
        tmp = {}
        day_20_applies = round((data[-1]['close']-data[-20]['last_close'])/data[-20]['last_close']*100, 2)
        tmp['code'] = code
        tmp['day_20_applies'] = day_20_applies
        if len(data) <= 180:
            tmp['is_new'] = 1
        else:
            tmp['is_new'] = 0
        return tmp

def get_fund_holdings():
    db = DB()
    data = ts.fund_holdings(2021, 2)
    for i in data.values:
        s = FundHolding()
        s.CODE = i[7]
        s.NAME = i[3]
        s.UPDATE_TIME = i[5]
        s.FUND_HOLDING_COUNT = float(i[1])*10000
        s.FUND_HOLDING_RATIO = float(i[6])
        db.updateFundHolding(s)
        del s

