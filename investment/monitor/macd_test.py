from monitor import *

kline = get_stock_kline_with_indicators(300015, period=102)
kline = MACD(kline)
for i in kline:
    print(i)