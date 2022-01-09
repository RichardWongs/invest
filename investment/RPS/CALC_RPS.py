import os
import pandas as pd
from 动量模型 import readMarketDataFromLocal

filename = "daily_data.csv"
if filename in os.listdir(os.curdir):
    os.remove(filename)
data = readMarketDataFromLocal()
dataframe = pd.DataFrame()
count = 0
for i in data:
    if count > 100:
        break
    df = pd.DataFrame(i['kline'], columns=['trade_date', 'close'], index=[i['day'] for i in i['kline']])
    dataframe[i['code']] = df.close
    count += 1
dataframe.index_col = 0
dataframe.to_csv(filename, encoding='utf-8')

