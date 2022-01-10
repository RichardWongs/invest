from monitor import *
import sys
from datetime import date,datetime


def market_chart(code=None, name=None):
    import mplfinance as mpf
    if code:
        name = get_name_by_code(code)
    elif name:
        code = get_code_by_name(name)
    else:
        logging.error("code 和 name 必须传一个")
        sys.exit()
    save_path = "../STOCK_CHANNEL"
    if str(code).startswith('1') or str(code).startswith('5'):
        save_path += "/ETF"
    else:
        # save_path += "/STOCK"
        save_path += "/beautiful"
    code = str(code).split('.')[0]
    data = get_stock_kline_with_indicators(code, period=101, limit=150)
    data = BooleanLine(data)
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
    mc = mpf.make_marketcolors(
        up="red",
        down="green",
        edge="i",
        wick="i",
        volume="in",
        inherit=True
    )
    s = mpf.make_mpf_style(
        # gridaxis="both",
        # gridstyle="-.",
        y_on_right=False,
        marketcolors=mc,
        rc={"font.family": "SimHei"}
    )
    add_plot = [
        mpf.make_addplot(df.get('BBU')),
        mpf.make_addplot(df.get('MID')),
        mpf.make_addplot(df.get('BBL'))
    ]
    mpf.plot(df,
             type="candle",
             title=f"{code}  {name}",
             ylabel="price($)",
             style=s,
             volume=True,
             ylabel_lower="volume(shares)",
             figratio=(12, 6),
             # figscale=8,
             mav=(50, 150, 200),
             addplot=add_plot,
             show_nontrading=True,
             # savefig=f"{save_path}/{name}.png"
             )
    logging.warning(f"{code}\t{name}")


market_chart("600519")
