# 先引入后面可能用到的library
import time
from datetime import date, timedelta
import numpy as np
import pandas as pd
import tushare as ts


# %matplotlib inline
# 正常显示画图时出现的中文和负号
# from pylab import mpl
# pro = ts.pro_api("b625f0b90069039346d199aa3c0d5bc53fd47212437337b45ba87487")
# mpl.rcParams['font.sans-serif'] = ['SimHei']
# mpl.rcParams['axes.unicode_minus'] = False
# begin_date = int(str(date.today() - timedelta(weeks=52)).replace('-', ''))
# today = int(str(date.today()).replace('-', ''))


# def get_stock_list():
#     df = pro.stock_basic(exchange='', list_status='L',
#                          fields='ts_code,symbol,name,list_date')  # fields='ts_code,symbol,name,area,industry,list_date'
#     # 排除掉新股次新股
#     df = df[df['list_date'].apply(int).values < begin_date]
#     # 获取当前所有非新股次新股代码和名称
#     codes = df.ts_code.values
#     names = df.name.values
#     stock_list = []
#     for code, name in zip(codes, names):
#         tmp = {'code': code, 'name': name}
#         stock_list.append(tmp)
#     return stock_list


# 构建一个字典方便调用
# code_name = dict(zip(names, codes))


# print(code_name)


# 使用 tushare 获取上述股票周价格数据并转换为周收益率
# 设定默认起始日期为2018年1月5日，结束日期为2019年3月19日
# 日期可以根据需要自己改动


# def get_data(code, start=begin_date, end=today):
#     df = pro.daily(ts_code=code, start_date=start, end_date=end, fields='trade_date,close')
#     # 将交易日期设置为索引值
#     df.index = pd.to_datetime(df.trade_date)
#     df = df.sort_index()
#     return df.close


# 构建一个空的dataframe用来装数据
# data = pd.DataFrame()
# for name, code in code_name.items():
#     data[name] = get_data(code)
# print(data)
# data.to_csv('daily_data.csv', encoding='utf-8')


# data = pd.read_csv('stock_data.csv', encoding='gbk', index_col='trade_date')
# data.index = (pd.to_datetime(data.index)).strftime('%Y%m%d')


# 计算收益率
# def cal_ret(df, w=5):
#     df = df / df.shift(w) - 1
#     return df.iloc[w:, :].fillna(0)


# ret120 = cal_ret(data, w=50)
# print(ret120)


# 计算RPS
# def get_RPS(ser):
#     df = pd.DataFrame(ser.sort_values(ascending=False))
#     df['n'] = range(1, len(df) + 1)
#     df['rps'] = (1 - df['n'] / len(df)) * 100
#     return df


# 计算每个交易日所有股票滚动w日的RPS
# def all_RPS(data):
#     dates = (data.index).strftime('%Y%m%d')
#     RPS = {}
#     for i in range(len(data)):
#         RPS[dates[i]] = pd.DataFrame(get_RPS(data.iloc[i]).values, columns=['收益率', '排名', 'RPS'],
#                                      index=get_RPS(data.iloc[i]).index)
#     return RPS


# rps120 = all_RPS(ret120)
# print(rps120)


# 获取所有股票在某个期间的RPS值
# def all_data(rps, ret):
#     df = pd.DataFrame(np.NaN, columns=ret.columns, index=ret.index)
#     for date in ret.index:
#         date = date.strftime('%Y%m%d')
#         d = rps[date]
#         for c in d.index:
#             df.loc[date, c] = d.loc[c, 'RPS']
#     return df


# 构建一个以前面收益率为基础的空表
# df_new = pd.DataFrame(np.NaN, columns=ret120.columns, index=ret120.index)
# for date in df_new.index:
#     date = date.strftime('%Y%m%d')
#     d = rps120[date]
#     for c in d.index:
#         df_new.loc[date, c] = d.loc[c, 'RPS']
# print(df_new)
# df_new = df_new[df_new.index == "2021-07-30"]
# print(df_new, type(df_new))


# def plot_rps(stock):
#     plt.subplot(211)
#     data[stock][120:].plot(figsize=(16,16),color='r')
#     plt.title(stock+'股价走势',fontsize=15)
#     plt.yticks(fontsize=12)
#     plt.xticks([])
#     ax = plt.gca()
#     ax.spines['right'].set_color('none')
#     ax.spines['top'].set_color('none')
#     plt.subplot(212)
#     df_new[stock].plot(figsize=(16,8),color='b')
#     plt.title(stock+'RPS相对强度',fontsize=15)
#     my_ticks = pd.date_range('2018-06-9','2019-3-31',freq='m')
#     plt.xticks(my_ticks,fontsize=12)
#     plt.yticks(fontsize=12)
#     ax = plt.gca()
#     ax.spines['right'].set_color('none')
#     ax.spines['top'].set_color('none')
#     plt.show()
# print(rps120)

# dates = ['20210728', '20210729', '20210730']
# df_rps = pd.DataFrame()
# for date in dates:
#     df_rps[date] = rps120[date].index[:50]
#     print(df_rps)
