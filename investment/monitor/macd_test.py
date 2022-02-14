from monitor import *


def simulation_week_macd(code):
    # 资料来源: 强势股投资日记 https://mp.weixin.qq.com/s/hskxWqXBoLDdc1ao57Ygaw
    simulation_date = date.today() + timedelta(days=7)
    kline = get_stock_kline_with_indicators(code, period=102)
    kline.append({'day': str(simulation_date), 'close': kline[-1]['close']})
    kline = MACD(kline)
    print(kline[-1])


simulation_week_macd(300760)
