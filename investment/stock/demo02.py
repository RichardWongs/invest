import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import array
import numpy as np
import math

def get_data(filename):
    data = pd.read_csv(filename)

    # 构造X列表和Y列表
    X_parameter = []
    Y_parameter = []
    for single_square, single_price_value in zip(data['square_feet'], data['price']):
        X_parameter.append([float(single_square)])
        Y_parameter.append(float(single_price_value))
    return X_parameter, Y_parameter

def linear_model_main(X_parameter, Y_parameter, predict_square_feet):
    # 构造回归对象
    regr = LinearRegression()
    regr.fit(X_parameter, Y_parameter)

    # 获取预测值
    predict_outcome = regr.predict(predict_square_feet)

    # 构造返回字典
    predictions = {}
    # 截距值
    predictions["截距值intercept"] = regr.intercept_
    # 回归系数(斜率值)
    predictions["回归系数(斜率值)coefficient"] = regr.coef_
    # 预测值
    predictions["预测值predict_value"] = predict_outcome
    print(f"截距值: {regr.intercept_}\t斜率值: {regr.coef_}")
    return predictions

def show_linear_line(X_parameter, Y_parameter):
    # 构造回归对象
    regr = LinearRegression()
    regr.fit(X_parameter, Y_parameter)

    # 绘出已知数据散点图
    plt.scatter(X_parameter, Y_parameter, color="blue")
    # 绘出预测直线
    plt.plot(X_parameter, regr.predict(X_parameter), color="red", linewidth=4)
    plt.show()

def main():
    # 读取数据
    X, Y = get_data("data.csv")
    # 获取预测值,在这里我们预测700平方英尺的房子房价
    predict_square_feet = [700]
    result = linear_model_main(X, Y, [predict_square_feet])
    for key, value in result.items():
        show_linear_line(X, Y)


def R2(X, Y):
    xBar = np.mean(X)
    yBar = np.mean(Y)
    SSR = 0
    varX = 0
    varY = 0
    for i in range(0, len(X)):
        diffXXBar = X[i] - xBar
        diffYYBar = Y[i] - yBar
        SSR += (diffXXBar * diffYYBar)
        varX += diffXXBar ** 2
        varY += diffYYBar ** 2
    SST = math.sqrt(varX * varY)
    return SSR / SST


def calc_linear(x, y):
    assert len(x) == len(y)
    x_ = sum(x)/len(x)
    y_ = sum(y)/len(y)
    print(f"x_:{x_}\ty_:{y_}")
    add_value = 0
    for i in range(len(x)):
        add_value += x[i] * y[i]
    take_value = x_ * y_
    print(f"add_value:{add_value}\ttake_value:{take_value}")
    x_sum_square = 0
    for i in range(len(x)):
        x_sum_square += x[i]*x[i]
    x_sqrt = sum(x)*sum(x)/len(x)*len(x)
    print(f"x_sum_square:{x_sum_square}\tx_sqrt:{x_sqrt}")
    b = (add_value-len(x)*take_value)/(x_sum_square-len(x)*x_sqrt)
    a = y_ - b * x_
    print(f"a:{a}\tb:{b}")



