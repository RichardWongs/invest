import mplfinance as mpf
import pandas as pd
from datetime import datetime
from monitor import get_stock_kline_with_indicators


def market_chart(code, name="UNKNOWN"):
    data = get_stock_kline_with_indicators(code, period=101, limit=250)
    for i in data:
        i['day'] = datetime.strptime(i['day'], "%Y-%m-%d").date()
        del i['applies']
        del i['VOL']
        del i['last_close']
        del i['TRI']
        if '10th_largest' in i.keys():
            del i['10th_largest']
        if '10th_minimum' in i.keys():
            del i['10th_minimum']
        if 'avg_volume' in i.keys():
            del i['avg_volume']
        if 'volume_ratio' in i.keys():
            del i['volume_ratio']
    df = pd.DataFrame(data)
    df["datetime"] = pd.to_datetime(df["day"])
    df.set_index("datetime", inplace=True)
    mpf.plot(df,
             type="candle",
             title=code,
             ylabel="price($)",
             style="binance",
             volume=True,
             ylabel_lower="volume(shares)",
             figratio=(12, 6),
             mav=(50, 150, 200),
             show_nontrading=False,
             savefig=f"{name}.png")



