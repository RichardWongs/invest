import csv
import pandas as pd
from monitor import EMA


file = "daily_data.csv"
df = pd.read_csv(file, encoding="utf-8")
codes = df.columns[1:]
for i in range(len(codes)):
    closes = df.iloc[:, i+1].values
    tmp = {'code': codes[i], 'name': "", 'industry': "", 'close': closes[-1], 'ema': EMA(closes, 150)}
    print(codes[i], len(closes), EMA(closes, 150))
    break


