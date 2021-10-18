
def AMA(price, N=10, NF=2, NS=30):
    direction = [0 for _ in range(len(price))]
    for i in range(len(price)):
        if i >= N:
            direction[i] = price[i] - price[i-N]
    volatility = [0 for _ in range(len(price))]
    delt = [0 for _ in range(len(price))]
    for i in range(1, len(price)):
        delt[i] = abs(price[i] - price[i-1])
    for i in range(N-1, len(price)):
        sum = 0
        for j in range(N):
            sum = sum + delt[i-N+1+j]
        volatility[i] = sum

    fasttest = 2/(NF + 1)
    slowtest = 2/(NS + 1)

    ER = [0 for _ in range(len(price))]
    smooth = [0 for _ in range(len(price))]
    c = [0 for _ in range(len(price))]

    for i in range(N, len(price)):
        ER[i] = abs(direction[i]/volatility[i])
        smooth[i] = ER[i] * (fasttest - slowtest) + slowtest
        c[i] = smooth[i] * smooth[i]

    ama = [0 for _ in range(len(price))]
    ama[N-1] = price[N-1]
    for i in range(N, len(price)):
        ama[i] = ama[i-1] + c[i] * (price[i] - ama[i-1])
    return ama


"""
计算价格效率
DIRECTION = CLOSE - REF(CLOSE, 10)
VOLATILITY = SUM(ABS(CLOSE - REF(CLOSE, 1)), 10)
ER = ABS(DIRECTION/VOLATILITY)
计算平滑系数
FASTSC = 2/(2+1)
SLOWSC = 2/(30+1)
SSC = ER * (FASTSC - SLOWSC) + SLOWSC
CQ = SSC * SSC
计算AMA1, AMA2 的值
AMA1 = EMA(DMA(CLOSE, ))
"""


def KAMA(kline, N=10, NF=2, NS=30):
    direction = [0 for _ in range(len(kline))]
    for i in range(len(kline)):
        if i >= N:
            direction[i] = kline[i]['close'] - kline[i-N]['close']
    volatility = [0 for _ in range(len(kline))]
    delt = [0 for _ in range(len(kline))]
    for i in range(1, len(kline)):
        delt[i] = abs(kline[i]['close'] - kline[i-1]['close'])
    for i in range(N-1, len(kline)):
        sum = 0
        for j in range(N):
            sum = sum + delt[i-N+1+j]
        volatility[i] = sum

    fasttest = 2/(NF + 1)
    slowtest = 2/(NS + 1)

    ER = [0 for _ in range(len(kline))]
    smooth = [0 for _ in range(len(kline))]
    c = [0 for _ in range(len(kline))]

    for i in range(N, len(kline)):
        ER[i] = abs(direction[i]/volatility[i])
        smooth[i] = ER[i] * (fasttest - slowtest) + slowtest
        c[i] = smooth[i] * smooth[i]

    ama = [0 for _ in range(len(kline))]
    ama[N-1] = kline[N-1]['close']
    for i in range(N, len(kline)):
        ama[i] = ama[i-1] + c[i] * (kline[i]['close'] - ama[i-1])
        kline[i]['KAMA'] = round(ama[i], 2)
    return kline[N:]


