from sqlalchemy import Column, String, Integer, create_engine, Date, Float
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()


class Stock(Base):
    __tablename__ = "stocks"

    STOCK_CODE = Column(Integer,primary_key=True, nullable=False)
    STOCK_NAME = Column(String(20),nullable=False)
    CURRENT_PRICE = Column(Float, default=None)
    DAY_20_APPLIES = Column(Float,default=0)
    DAY_50_APPLIES = Column(Float, default=None)
    DAY_120_APPLIES = Column(Float, default=None)
    DAY_250_APPLIES = Column(Float, default=None)
    DAY_250_HIGHEST_PRICE = Column(Float, default=None)
    IS_NEW = Column(Integer,default=None)
    UPDATE_TIME = Column(Date(), default=None)
    INDUSTRY = Column(String(50), default=None)

