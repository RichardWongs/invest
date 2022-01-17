import os
import time
import logging
import pandas as pd
from 动量模型 import readMarketDataFromLocal
from RPS.RPS_DATA import cal_ret, all_RPS, fill_in_data_V2


def run():
    start = int(time.time())
    filename = "daily_data.csv"
    if filename in os.listdir(os.curdir):
        os.remove(filename)
    data = readMarketDataFromLocal()
    dataframe = pd.DataFrame()
    for i in data:
        df = pd.DataFrame(i['kline'], columns=['day', 'close'], index=[i['day'] for i in i['kline']])
        df.index = pd.to_datetime(df.day)
        df = df.sort_index()
        dataframe[i['code']] = df.close
    dataframe.index_col = 0
    dataframe.to_csv(filename, encoding='utf-8')
    time.sleep(1)
    data = pd.read_csv(filename, encoding='utf-8', index_col='day')
    data.index = pd.to_datetime(data.index, format='%Y%m%d', errors='ignore')
    for rps_day in [20, 50, 120, 250]:
        ret = cal_ret(data, w=rps_day)
        rps = all_RPS(ret)
        new_rps = {}
        for k, v in rps.items():
            tmp = {}
            for i in range(len(v)):
                tmp[v.index[i]] = {'code': v.index[i], 'RPS': round(v.values[i][-1], 2)}
            new_rps[k] = tmp
        fill_in_data_V2(new_rps, filename=f'RPS_{rps_day}_V2.csv')
    end = int(time.time())
    minutes = int((end - start) / 60)
    seconds = (end - start) % 60
    logging.warning(f"RPS总耗时: {minutes}分{seconds}秒")


if __name__ == "__main__":
    run()

