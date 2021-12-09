import csv

import pandas as pd
file = "daily_data.csv"
# with open(file, "rt") as f:
#     reader = csv.reader(f)
#     trade_date = [row[0] for row in reader]
#     print(trade_date)
#     count = 0
#     for i in reader:
#         print(i)
#         count += 1
#         if count > 10:
#             break
    # column = [row[2] for row in reader]
    # trade_date = [row[0] for row in reader]
    # print(column[0])
    # print(column[1:])
pool = []
df = pd.read_csv(file, encoding="utf-8")
# print(df.columns)
for i in df.columns[1:]:
    pool.append({'code': i, 'kline': []})
# print(df.values)
index = 0
# for i in df.values:
#     print(i)
print(pool)
for i in df.values[:1]:
    print(i)
    for j in i[1:]:
        pass
