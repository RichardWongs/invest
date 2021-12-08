import csv

import pandas as pd
file = "daily_data.csv"
with open(file, "rt") as f:
    reader = csv.reader(f)
    count = 0
    for i in reader:
        print(i)
        count += 1
        if count > 10:
            break
    # column = [row[2] for row in reader]
    # trade_date = [row[1] for row in reader]
    # print(column[0])
    # print(column[1:])






