import numpy
from pandas import *
from math import *
from pandas._libs.window.aggregations import ewma


def PPSR(df):
    PP = Series((df['High'] + df['Low'] + df['Close']) / 3)
    R1 = Series(2 * PP - df['Low'])
    S1 = Series(2 * PP - df['High'])
    R2 = Series(PP + df['High'] - df['Low'])
    S2 = Series(PP - df['High'] + df['Low'])
    R3 = Series(df['High'] + 2 * (PP - df['Low']))
    S3 = Series(df['Low'] - 2 * (df['High'] - PP))
    psr = {'PP':PP, 'R1':R1, 'S1':S1, 'R2':R2, 'S2':S2, 'R3':R3, 'S3':S3}
    PSR = DataFrame(psr)
    df = df.join(PSR)
    return df


def TRIX(df, n):
    EX1 = ewma(df['Close'], span = n, min_periods = n - 1)
    EX2 = ewma(EX1, span = n, min_periods = n - 1)
    EX3 = ewma(EX2, span = n, min_periods = n - 1)
    i = 0
    ROC_l = [0]
    while i + 1 <= df.index[-1]:
        ROC = (EX3[i + 1] - EX3[i]) / EX3[i]
        ROC_l.append(ROC)
        i = i + 1
    Trix = Series(ROC_l, name = 'Trix_' + str(n))
    df = df.join(Trix)
    return df


def DONCH(df, n):
    i = 0
    DC_l = []
    while i < n - 1:
        DC_l.append(0)
        i = i + 1
    i = 0
    while i + n - 1 < df.index[-1]:
        DC = max(df['High'].ix[i:i + n - 1]) - min(df['Low'].ix[i:i + n - 1])
        DC_l.append(DC)
        i = i + 1
    DonCh = Series(DC_l, name = 'Donchian_' + str(n))
    DonCh = DonCh.shift(n - 1)
    df = df.join(DonCh)
    return df

