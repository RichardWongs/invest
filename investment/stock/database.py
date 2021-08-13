import logging
from sqlalchemy import Column, String, Integer, create_engine, Date, Float
from sqlalchemy.orm import sessionmaker
from datetime import datetime,date,timedelta
from .table import Stock

MYSQL_HOST = "172.16.1.162"
PORT = 3306
USERNAME = 'root'
PASSWORD = '123456'

def mysql_connect(db):
    import pymysql
    conn = pymysql.connect(host=MYSQL_HOST,
                           user=USERNAME,
                           passwd=PASSWORD,
                           db=db,
                           port=PORT,
                           charset="utf8")
    cur = conn.cursor()
    yield cur
    logging.info('关闭游标')
    cur.close()
    logging.info('执行commit')
    conn.commit()
    logging.info('关闭MySQL连接')
    conn.close()

def set_data_from_mysql(db, statement):
    cur = mysql_connect(db)
    for i in cur:
        if isinstance(statement, str):
            i.execute(statement)
        elif isinstance(statement, list) or isinstance(statement, tuple):
            for j in statement:
                i.execute(j)
        else:
            print('The params statement must be str,list or tuple')


def query_data_from_mysql(db, statement):
    cur = mysql_connect(db)
    for i in cur:
        if isinstance(statement, str):
            i.execute(statement)
            data = i.fetchall()
            if data:
                if isinstance(data, tuple) and len(data) == 1:
                    return data[0]
                else:
                    return data
        else:
            logging.warning('The params statement must be str!')

class DB(object):
    def __init__(self):
        self.engine = create_engine(f'mysql+pymysql://{USERNAME}:{PASSWORD}@{MYSQL_HOST}:{PORT}/stock')
        self.DBSession = sessionmaker(bind=self.engine)
        self.session = self.DBSession()

    def addDB(self, code, name, applies=float(0), is_new=0):
        data = Stock(STOCK_CODE=code,
                     STOCK_NAME=name,
                     DAY_20_APPLIES=applies,
                     IS_NEW=is_new,
                     UPDATE_TIME=datetime.now())
        self.session.add(data)
        self.session.commit()
        self.session.close()

    def updateDB(self, stock):
        try:
            if stock.code and stock.name:
                self.session.query(Stock).filter(Stock.STOCK_CODE==stock.code).update(
                    {'STOCK_NAME': stock.name,
                     'CURRENT_PRICE': stock.current_price,
                     'DAY_20_APPLIES': stock.day_20_applies,
                     'DAY_50_APPLIES': stock.day_50_applies,
                     'DAY_120_APPLIES': stock.day_120_applies,
                     'DAY_250_APPLIES': stock.day_250_applies,
                     'DAY_250_HIGHEST_PRICE': stock.day_250_highest_price,
                     'IS_NEW': stock.is_new,
                     'UPDATE_TIME': stock.update_time}
                )
                self.session.commit()
                self.session.close()
        except Exception() as e:
            print(e)

    def selectDB(self, code):
        stock = self.session.query(Stock).filter(Stock.code==code).first()
        self.session.close()
        return stock