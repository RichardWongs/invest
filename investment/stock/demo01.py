import tushare as ts
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, FormatStrFormatter
import matplotlib
import datetime
from sklearn import linear_model
# token = 'b625f0b90069039346d199aa3c0d5bc53fd47212437337b45ba87487'
# ts.set_token(token)
pro = ts.pro_api("b625f0b90069039346d199aa3c0d5bc53fd47212437337b45ba87487")
matplotlib.rcParams['font.family'] = 'SimHei'


def get_data(ts_code):
    data = ts.pro_bar(ts_code=ts_code, adj='hfq', start_date=START_DATE, end_date=END_DATE,freq=DATE_INTERAL)
    data_close = data[['trade_date', 'close']].iloc[::-1,:]
    data_close.index = range(1,len(data)+1)
    print(data_close)
    return data_close


START_DATE = '20100101'  # 获取数据起始日期
END_DATE = '20201231'
TS_CODE = '600085.SH'
DATE_INTERAL = 'W'    # 周线

L_START_DATE = '20150101'    # 需要拟合趋势起始日期
L_END_DATE = '20201231'

shares = ['002820.SZ', '600186.SH', '600866.SH', '002910.SZ', '000590.SZ',
          '000650.SZ', '000989.SZ', '002566.SZ', '002644.SZ', '002728.SZ',
          '002693.SZ', '002900.SZ', '002907.SZ', '600062.SH', '600227.SH',]




def main_point(shares):
    for share in shares[:5]:
        data_close = get_data(share)
        regr_data = reg_p(data_close,L_START_DATE,L_END_DATE,point)
        show_regr_data(data_close,regr_data,share)


def reg_l(data_close,s_date,e_date):
    l_data = data_close.loc[(data_close.trade_date>=s_date)&(data_close.trade_date<=e_date)]
    y = l_data.close
    x = np.array(l_data.index).reshape(-1,1)
    regr = linear_model.LinearRegression()
    regr.fit(x,y)
    return regr,l_data


def reg_p(data_close,s_date,e_date,point):
    l_data = data_close.loc[(data_close.trade_date>=s_date)&(data_close.trade_date<=e_date)]
    l_index = l_data.index
    index = list(map(int,np.linspace(l_index[0],l_index[-1],point, endpoint=True)))
    index = [np.int64(i) for i in index]
    regs = []
    for i in range(0,point-1):
        x = l_data.loc[(l_data.index>=index[i])&(l_data.index<=index[i+1])]
        xx = np.array(x.index).reshape(-1,1)
        y = x.close
        regr = linear_model.LinearRegression()
        regr.fit(xx,y)
        y1 = [ i*regr.coef_ + regr.intercept_ for i in x.index ]
        regs.append((x.index,y1,regr.coef_))

    return regs


def show_l(data, l_data, regr, title):
    fig = plt.figure(figsize=(25, 4), dpi=80)
    l_index = l_data.index
    l_y = [y*regr.coef_ + regr.intercept_ for y in l_index]
    plt.title(title)
    if regr.coef_ >= 0:
        colr = 'red'
    else:
        colr = 'green'
    plt.plot(l_index, l_y, label='趋势 {} '.format(np.round(regr.coef_, 6)*100), color=colr)
    plt.xlabel('时间', fontsize=15)
    plt.ylabel('股价', fontsize=15)
    plt.plot(data.trade_date, data.close, label='股价变化', color='gray')
    plt.legend(fontsize=15)
    plt.xticks(rotation=90, fontsize=15)
    plt.yticks(fontsize=15)
    plt.gca().xaxis.set_major_locator(MultipleLocator(30))
    plt.show()


def show_regr_data(data_close, regr_data, share):
    fig = plt.figure(figsize=(25, 4), dpi=80)
    plt.title(share)
    for data in regr_data:
        if data[2] >= 0:
            colr = 'red'
        else:
            colr = 'green'
        plt.plot(data[0], data[1], label='趋势 {} '.format(np.round(data[2], 4)*100), color=colr)
    plt.xlabel('时间', fontsize=15)
    plt.ylabel('股价', fontsize=15)
    plt.plot(data_close.trade_date, data_close.close, label='股价变化', color='gray')
    plt.legend(fontsize=15)
    plt.xticks(rotation=90,fontsize=15)
    plt.yticks(fontsize=15)
    plt.gca().xaxis.set_major_locator(MultipleLocator(30))
    plt.show()


def main(shares):
    # shares 股票代码列表
    for share in shares:
        data_close = get_data(share)
        regr, l_data = reg_l(data_close, L_START_DATE, L_END_DATE)
        show_l(data_close,l_data,regr,share)


START_DATE = '20200101'
END_DATE = '20210101'
TS_CODE = '600085.SH'
DATE_INTERAL = 'W'

L_START_DATE = '20150101'
L_END_DATE = '20201231'

point = 6

# shares = ['002820.SZ', '600186.SH', '600866.SH', '002910.SZ', '000590.SZ', '000650.SZ', '000989.SZ', '002566.SZ', '002644.SZ', '002728.SZ', '002693.SZ', '002900.SZ', '002907.SZ', '600062.SH', '600227.SH',]
shares = ['300760.SZ']
main(shares)
# main_point(shares)

