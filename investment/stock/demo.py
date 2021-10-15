price = [364.0, 359.0, 355.69, 362.36, 371.5, 349.0, 348.6, 367.03, 379.99, 388.17, 384.0, 367.28, 368.21, 366.6, 361.5, 351.1, 359.0, 373.18, 369.1, 375.05, 377.74, 375.57, 387.96, 395.53, 385.42, 384.0, 409.6, 434.1, 425.34, 424.5, 414.78, 432.21, 407.5, 409.59, 409.37, 434.63, 451.98, 445.0, 420.18, 434.51, 450.0, 452.8, 450.23, 468.45, 467.3, 476.23, 493.9, 508.51, 534.8, 529.5, 519.59, 519.27, 515.23, 542.5, 559.16, 545.88, 565.79, 563.01, 551.37, 568.0, 531.0, 523.5, 528.04, 555.78, 557.08, 547.01, 539.78, 495.0, 525.05, 556.8, 550.4, 552.0, 531.0, 569.0, 557.0, 543.88, 516.0, 510.5, 517.25, 502.0, 502.05, 477.0, 480.0, 495.0, 503.0, 494.11, 521.9, 523.0, 530.24, 521.0, 507.5, 505.24, 494.87, 488.71, 493.5, 486.5, 516.1, 514.01, 503.0, 507.2, 502.1, 502.8, 529.9, 525.35, 498.0, 503.0, 493.31, 492.99, 499.98, 513.5, 500.43, 502.51, 525.73, 534.0, 521.0, 505.0, 522.26, 532.3, 565.02]


def zeros(length):
    result = []
    for i in range(length):
        result.append(0)
    return result


def AMA(price, N=10, NF=2, NS=30):
    direction = zeros(len(price))
    for i in range(len(price)):
        if i >= N:
            direction[i] = price[i] - price[i-N]
    volatility = zeros(len(price))
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

    ER = zeros(len(price))
    smooth = zeros(len(price))
    c = zeros(len(price))

    for i in range(N, len(price)):
        ER[i] = abs(direction[i]/volatility[i])
        smooth[i] = ER[i] * (fasttest - slowtest) + slowtest
        c[i] = smooth[i] * smooth[i]

    ama = zeros(len(price))
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
