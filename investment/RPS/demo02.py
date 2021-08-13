# encoding: utf-8
import pandas as pd
from datetime import date, timedelta
import tushare as ts
pro = ts.pro_api("b625f0b90069039346d199aa3c0d5bc53fd47212437337b45ba87487")


def get_close(code):
    # 按照日期范围获取股票交易日期,收盘价
    start = int(str(date.today() - timedelta(days=365)).replace('-', ''))
    end = int(str(date.today()).replace('-', ''))
    df = pro.daily(ts_code=code, start_date=start, end_date=end, fields='trade_date,close')
    # 将交易日期设置为索引值
    df.index = pd.to_datetime(df.trade_date)
    df = df.sort_index()
    closes = []
    [closes.append(i[1]) for i in df.values]
    close = closes[-1]
    highest = max(closes[:-1])
    momentum = round(close / highest, 3)
    interval_yield = round((closes[-1] - closes[0]) / closes[0] * 100, 2)
    return {'code': code, 'interval_yield': interval_yield, 'momentum': momentum}


