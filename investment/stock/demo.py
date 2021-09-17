# from scipy import stats
import math
import numpy as np
import matplotlib.pyplot as plt
"""
利用 Python 实现线性回归模型
"""


class LinerRegressionModel(object):
    def __init__(self, data):
        self.data = data
        self.x = data[:, 0]
        self.y = data[:, 1]

    def log(self, a, b):
        print("计算出的线性回归函数为:\ny = {:.5f}x + {:.5f}".format(a, b))

    def plt(self, a, b):
        plt.plot(self.x, self.y, 'o', label='data', markersize=10)
        plt.plot(self.x, a * self.x + b, 'r', label='line')
        plt.legend()
        plt.show()

    def least_square_method(self):
        """
        最小二乘法的实现
        """
        def calc_ab(x, y):
            sum_x, sum_y, sum_xy, sum_xx = 0, 0, 0, 0
            n = len(x)
            for i in range(0, n):
                sum_x += x[i]
                sum_y += y[i]
                sum_xy += x[i] * y[i]
                sum_xx += x[i]**2
            a = (sum_xy - (1 / n) * (sum_x * sum_y)) / \
                (sum_xx - (1 / n) * sum_x**2)
            b = sum_y / n - a * sum_x / n
            return a, b
        a, b = calc_ab(self.x, self.y)
        self.log(a, b)
        self.plt(a, b)


def run(data):
    data = np.array([[1, 2.5], [2, 3.3], [2.5, 3.8],
                     [3, 4.5], [4, 5.7], [5, 6]])
    model = LinerRegressionModel(data)
    model.least_square_method()
# ===================================================================================

testX = [
    174.5,
    171.2,
    172.9,
    161.6,
    123.6,
    112.1,
    107.1,
    98.6,
    98.7,
    97.5,
    95.8,
    93.5,
    91.1,
    85.2,
    75.6,
    72.7,
    68.6,
    69.1,
    63.8,
    60.1,
    65.2,
    71,
    75.8,
    77.8]
testY = [
    88.3,
    87.1,
    88.7,
    85.8,
    89.4,
    88,
    83.7,
    73.2,
    71.6,
    71,
    71.2,
    70.5,
    69.2,
    65.1,
    54.8,
    56.7,
    62,
    68.2,
    71.1,
    76.1,
    79.8,
    80.9,
    83.7,
    85.8]


def computeCorrelation(X, Y):
    xBar = np.mean(X)
    yBar = np.mean(Y)
    SSR = 0
    varX = 0
    varY = 0
    for i in range(0, len(X)):
        diffXXBar = X[i] - xBar
        diffYYBar = Y[i] - yBar
        SSR += (diffXXBar * diffYYBar)
        varX += diffXXBar**2
        varY += diffYYBar**2

    SST = math.sqrt(varX * varY)
    print("使用math库：r：", SSR / SST, "r-squared：", (SSR / SST)**2)
    return


# computeCorrelation(testX, testY)
#
# x = np.array(testX)
# y = np.array(testY)
# # 拟合 y = ax + b
# poly = np.polyfit(x, y, deg=1)
# print("使用numpy库：a：" + str(poly[0]) + "，b：" + str(poly[1]))


def rsquared(x, y):
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    # a、b、r
    print(
        "使用scipy库：a：",
        slope,
        "b：",
        intercept,
        "r：",
        r_value,
        "r-squared：",
        r_value**2)


rsquared(testX, testY)

# ========================================================================================

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

START_DATE = '20100101'
END_DATE = '20201231'
TS_CODE = '600085.SH'
DATE_INTERAL = 'W'

L_START_DATE = '20150101'
L_END_DATE = '20201231'


def get_data(ts_code):
    data = ts.pro_bar(ts_code=ts_code, adj='hfq', start_date=START_DATE, end_date=END_DATE,freq=DATE_INTERAL)
    data_close = data[['trade_date', 'close']].iloc[::-1,:]
    data_close.index = range(1,len(data)+1)
    return data_close


def show_close(data):
    fig = plt.figure(figsize=(20, 4), dpi=80)
    plt.plot(data.trade_date, data.close, label='原始走势', color='green')
    plt.xlabel('时间', fontsize=15)
    plt.ylabel('股价', fontsize=15)
    plt.legend(fontsize=15)
    plt.grid()
    plt.xticks(rotation=90, fontsize=15)
    plt.yticks(fontsize=15)
    plt.gca().xaxis.set_major_locator(MultipleLocator(30))




