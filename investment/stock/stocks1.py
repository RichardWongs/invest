from _datetime import datetime
from sqlalchemy import Column, String, Integer, create_engine, ForeignKey, Date,Float
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
MYSQL_HOST = "172.16.1.162"
PORT = 3306
USERNAME = 'root'
PASSWORD = '123456'


class Stock(Base):
    __tablename__ = "stock"

    STOCK_CODE = Column(Integer,primary_key=True, nullable=False)
    STOCK_NAME = Column(String(20),nullable=False)
    DAY_20_APPLIES = Column(Float,default=0)
    IS_NEW = Column(Integer,default=None)
    UPDATE_TIME = Column(Date(), default=None)

class DB(object):
    def __init__(self):
        self.engine = create_engine(f'mysql+pymysql://{USERNAME}:{PASSWORD}@{MYSQL_HOST}:{PORT}/stock')
        self.DBSession = sessionmaker(bind=self.engine)
        self.session = self.DBSession()

    def updateDB(self, code, name, applies=float(0), is_new=1):
        data = Stock(STOCK_CODE=code,
                     STOCK_NAME=name,
                     DAY_20_APPLIES=applies,
                     IS_NEW=is_new,
                     UPDATE_TIME=datetime.now())
        self.session.add(data)
        self.session.commit()
        self.session.close()


db = DB()
db.updateDB(600000, '浦发银行', -2.31, 0)
