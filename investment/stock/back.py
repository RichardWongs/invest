from datetime import datetime

import backtrader as bt
import pandas as pd
import matplotlib.pyplot as plt
import datetime as dt
import numpy as np

class TestStrategy(bt.Strategy):
    def log(self):
        dt = dt or self.datas[0].datetime.date(0)


if __name__ == "__main__":
    cerebro = bt.Cerebro()
    df = pd.read_csv("")
    df['Datetime'] = pd.to_datetime(df["Date"])
    df.set_index("Datetime", inplace=True)
    data = bt.feeds.YahooFinanceCSVData(dataname=df, fromdate=datetime(2020, 1, 1), todate=datetime(2021, 12, 1))
    cerebro.adddata(data)
    cerebro.broker.setcash(100000.0)
