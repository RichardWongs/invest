# encoding: gbk
import sys
from datetime import datetime, date
import logging
import os
import time
import pandas as pd
import requests

import RPS.动量模型
from RPS.动量模型 import find_institutions_holding
from fund import get_fund_kline
from momentum.concept import get_industry_list, get_concept_kline_v2
from monitor import *


def get_etf_list():
    etf_list = [{"name": "创成长", "code": 159967},
                {"name": "质量ETF", "code": 515910},
                {"name": "A50ETF", "code": 159601},
                {"name": "上证50", "code": 510050},
                {"name": "沪深300ETF", "code": 510300},
                {"name": "中证500ETF", "code": 510500},
                {"name": "科创50", "code": 588000},
                {"name": "光伏ETF", "code": 515790},
                {"name": "医疗ETF", "code": 510050},
                {"name": "生物医药ETF", "code": 161726},
                {"name": "有色金属ETF", "code": 512400},
                {"name": "家电ETF", "code": 159996},
                {"name": "酒ETF", "code": 512690},
                {"name": "农业ETF", "code": 159825},
                {"name": "钢铁ETF", "code": 515210},
                {"name": "煤炭ETF", "code": 515220},
                {"name": "银行ETF", "code": 512800},
                {"name": "证券ETF", "code": 159841},
                {"name": "房地产ETF", "code": 512200},
                {"name": "恒生互联ETF", "code": 513330},
                {"name": "5G ETF", "code": 515050},
                {"name": "军工ETF", "code": 512660},
                {"name": "芯片ETF", "code": 159995},
                {"name": "化工ETF", "code": 159870},
                {'name': '深创100', 'code': 159721},
                {"name": "新能源汽车ETF", "code": 516390},
                {"name": "光伏ETF", "code": 515790},
                {"name": "医疗创新ETF", "code": 516820},
                {"name": "恒生科技30ETF", "code": 513010},
                {"name": "恒生医疗ETF", "code": 513060},
                {'name': "碳中和50ETF", "code": 516070}]
    return etf_list


def price_range_statistics(code, name="UNKNOWN"):
    kline = get_stock_kline_with_indicators(code, limit=120)
    N, M = 10, 50
    kline = EMA_V2(EMA_V2(kline, N), M)
    kline = Channel_Trade_System(kline, code=code, name=name)
    ttl = len(kline)
    mid_range = 0   # 两条均线之间
    under_range = 0  # 长均线与下通道线之间
    up_range = 0  # 短均线与上通道线之间
    for i in range(len(kline)):
        if kline[i][f'ema{N}'] > kline[i]['close'] >= kline[i][f'ema{M}'] or kline[i][f'ema{N}'] < kline[i]['close'] < kline[i][f'ema{M}']:
            mid_range += 1
        if kline[i][f'ema{N}'] < kline[i]['close'] < kline[i]['up_channel']:
            up_range += 1
        if kline[i]['down_channel'] < kline[i]['close'] < kline[i][f'ema{M}']:
            under_range += 1
    logging.warning(f"价格位于短均线与上通道线之间: {round(up_range/ttl*100, 2)}%\t价格位于长短均线之间: {round(mid_range/ttl*100, 2)}%"
                    f"\t价格位于长均线与下通道线之间: {round(under_range/ttl*100, 2)}%")


def select_convertible_bond():
    url = "https://www.jisilu.cn/data/cbnew/cb_list_new/?___jsl=LST___t=1635232720194"
    headers = {
        'Cookie': "kbzw__Session=hr6788crd3h7ss0560u1bdtam4; Hm_lvt_164fe01b1433a19b507595a43bf58262=1635233006,1635908529; kbz_newcookie=1; kbzw_r_uname=RichardWongs; kbzw__user_login=7Obd08_P1ebax9aXycvZydjp18_Q3sjnmrCW6c3q1e3Q6dvR1YyhmNjcqpqwzdrI25HZ2qzbkabF2NrWy97R2cbckqyopJmcndbd3dPGpJ2skq-Sq6qUs47FotLWoLbo5uDO4sKmrKGogZi43efZ2PDfl7DKgainoaickLjd56udtIzvmKqKl7jj6M3VuNnbwNLtm6yVrY-qrZOgrLi1wcWhieXV4seWqNza3ueKkKTc6-TW3puwl6SRpaupq5melqiZyMrfzenLpZaqrqGrlw..; Hm_lpvt_164fe01b1433a19b507595a43bf58262=1635908547"
    }
    body = {
        'is_search': 'N',
        'rp': 50,
        'page': 1
    }
    r = requests.post(url, headers=headers).json()
    logging.warning(str(r)[-30:])
    r = r['rows']
    for i in r:
        i = i['cell']
        del i['bond_py']
        del i['stock_py']
        del i['volatility_rate']
        del i['real_force_redeem_price']
        del i['redeem_dt']
        del i['adjusted']
        del i['convert_price_valid']
        del i['market_cd']
        del i['btype']
        del i['qflag2']
        del i['bond_value']
        del i['option_value']
        del i['fund_rt']
        del i['put_ytm_rt']
        del i['notes']
        del i['redeem_icon']
        print(i)


def draw_line_and_save2local(code, name="UNKNOWN", save_path=r"../STOCK_CHANNEL", period=101, limit=101):
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["SimHei"]  # 设置字体
    plt.rcParams["axes.unicode_minus"] = False  # 该语句解决图像中的“-”负号的乱码问题
    if str(code).startswith('1') or str(code).startswith('5'):
        save_path += "/ETF"
    else:
        save_path += "/STOCK"
    c = Channel(code, name, period=period, limit=limit)
    x = [i for i in range(len(c.kline))]
    close = [i['close'] for i in c.kline]
    ema50 = [i['ema50'] for i in c.kline]
    up_channel = [i['up_channel'] for i in c.kline]
    down_channel = [i['down_channel'] for i in c.kline]
    kama = [i['KAMA'] for i in c.kline]
    plt.rcParams['figure.figsize'] = (16, 8)
    plt.plot(x, close, color='black')
    plt.plot(x, ema50, color='pink')
    plt.plot(x, up_channel, color="red", linestyle='dashed')
    plt.plot(x, down_channel, color="green", linestyle='dashed')
    plt.plot(x, kama, color="red")
    plt.title(name)
    plt.savefig(f'{save_path}/{name}.png', dpi=180)
    # plt.show()
    plt.close()


def draw_line_by_simple(code, name="UNKNOWN", period=101, limit=120):
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["SimHei"]  # 设置字体
    plt.rcParams["axes.unicode_minus"] = False  # 该语句解决图像中的“-”负号的乱码问题
    c = Channel(code, name, period=period, limit=limit)
    c.kline = EMA_V2(EMA_V2(EMA_V2(c.kline, 10), 20), 50)
    x = [i for i in range(len(c.kline))]
    close = [i['close'] for i in c.kline]
    ma10 = [i['ema10'] for i in c.kline]
    ma20 = [i['ema20'] for i in c.kline]
    ma50 = [i['ema50'] for i in c.kline]
    up_channel = [i['up_channel'] for i in c.kline]
    down_channel = [i['down_channel'] for i in c.kline]
    kama = [i['KAMA'] for i in c.kline]
    plt.rcParams['figure.figsize'] = (16, 8)
    plt.plot(x, close, color='black')
    plt.plot(x, ma10, color='blue')
    plt.plot(x, ma20, color='purple')
    plt.plot(x, ma50, color='pink')
    plt.plot(x, up_channel, color="red", linestyle='dashed')
    plt.plot(x, down_channel, color="green", linestyle='dashed')
    plt.plot(x, kama, color="red")
    plt.title(name)
    plt.show()
    plt.close()


def draw_line_macd(code, name="UNKNOWN", period=101, limit=120):
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["SimHei"]  # 设置字体
    plt.rcParams["axes.unicode_minus"] = False  # 该语句解决图像中的“-”负号的乱码问题
    kline = get_stock_kline_with_indicators(code, period=period, limit=limit)
    kline = MACD(EMA_V2(EMA_V2(EMA_V2(kline, 10), 20), 50))
    x = [i for i in range(len(kline))]
    close = [i['close'] for i in kline]
    ma50 = [i['ema50'] for i in kline]
    dif = [i['DIF'] for i in kline]
    dea = [i['DEA'] for i in kline]
    macd = [i['MACD'] for i in kline]
    plt.rcParams['figure.figsize'] = (16, 8)
    plt.plot(x, close, color='black')
    plt.plot(x, ma50, color='pink')
    plt.plot(x, dif, color="red", linestyle='dashed')
    plt.plot(x, dea, color="green", linestyle='dashed')
    plt.bar(x, macd, color="red")
    plt.title(name)
    plt.show()
    plt.close()


def draw_line_by_ATR_Channel(code, name="UNKNOWN", period=101, limit=120):
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["SimHei"]  # 设置字体
    plt.rcParams["axes.unicode_minus"] = False  # 该语句解决图像中的“-”负号的乱码问题
    kline = get_stock_kline_with_indicators(code, period=period, limit=limit)
    kline = EMA_V2(kline, 50)
    kline = ATR_Channel_System(kline)
    x = [i for i in range(len(kline))]
    close = [i['close'] for i in kline]
    ma50 = [i['ema50'] for i in kline]
    ATR_plus_1 = [i['+1ATR'] for i in kline]
    ATR_plus_2 = [i['+2ATR'] for i in kline]
    ATR_plus_3 = [i['+3ATR'] for i in kline]
    ATR_minus_1 = [i['-1ATR'] for i in kline]
    ATR_minus_2 = [i['-2ATR'] for i in kline]
    ATR_minus_3 = [i['-3ATR'] for i in kline]
    plt.rcParams['figure.figsize'] = (16, 8)
    plt.plot(x, close, color='black')
    plt.plot(x, ma50, color='pink')
    plt.plot(x, ATR_plus_1, color="gray", linestyle='dashed')
    plt.plot(x, ATR_plus_2, color="gray", linestyle='dashed')
    plt.plot(x, ATR_plus_3, color="gray", linestyle='dashed')
    plt.plot(x, ATR_minus_1, color="gray", linestyle='dashed')
    plt.plot(x, ATR_minus_2, color="gray", linestyle='dashed')
    plt.plot(x, ATR_minus_3, color="gray", linestyle='dashed')
    plt.title(name)
    plt.show()
    plt.close()


def draw_boolean(code):
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["SimHei"]  # 设置字体
    plt.rcParams["axes.unicode_minus"] = False  # 该语句解决图像中的“-”负号的乱码问题
    kline = get_stock_kline_with_indicators(code)
    kline = BooleanLine(kline)
    x = [i for i in range(len(kline))]
    close = [i['close'] for i in kline]
    BBU_minus = [i['BBU_minus'] for i in kline]
    BBL_minus = [i['BBL_minus'] for i in kline]
    BBU = [i['BBU'] for i in kline]
    BBL = [i['BBL'] for i in kline]
    plt.rcParams['figure.figsize'] = (16, 8)
    plt.plot(x, close)
    plt.plot(x, BBU_minus, linestyle='dashed')
    plt.plot(x, BBL_minus, linestyle='dashed')
    plt.plot(x, BBU, linestyle='dashed')
    plt.plot(x, BBL, linestyle='dashed')
    plt.title(code)
    plt.show()
    plt.close()


def draw(code, name="UNKNOWN", period=101, limit=120):
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["SimHei"]  # 设置字体
    plt.rcParams["axes.unicode_minus"] = False  # 该语句解决图像中的“-”负号的乱码问题
    rows, columns = 1, 2

    save_path = "../STOCK_CHANNEL"
    if str(code).startswith('1') or str(code).startswith('5'):
        save_path += "/ETF"
    else:
        save_path += "/STOCK"

    data = get_stock_kline_with_indicators(code, period=period, limit=limit)
    data = EMA_V2(EMA_V2(EMA_V2(EMA_V2(data, 10), 20), 50), 26)
    data = ATR_Channel_System(data)
    data = KAMA(data)
    c = Channel(code=code, name=name, period=period, limit=limit)
    ucc, dcc = c.find_channel_coefficients()
    for i in data:
        i['up_channel'] = i['ema26'] * (1+ucc)
        i['down_channel'] = i['ema26'] * (1-dcc)
    x = [i for i in range(len(data))]
    close = [i['close'] for i in data]
    ma10 = [i['ema10'] for i in data]
    ma50 = [i['ema50'] for i in data]
    kama = [i['KAMA'] for i in data]

    up_channel = [i['up_channel'] for i in data]
    down_channel = [i['down_channel'] for i in data]
    plt.rcParams['figure.figsize'] = (16, 8)
    plt.subplot(rows, columns, 1)
    plt.plot(x, close)
    plt.plot(x, ma10)
    plt.plot(x, ma50)
    plt.plot(x, up_channel, color="red", linestyle='dashed')
    plt.plot(x, down_channel, color="green", linestyle='dashed')
    plt.title("Channel")

    ATR_plus_1 = [i['+1ATR'] for i in data]
    ATR_plus_2 = [i['+2ATR'] for i in data]
    ATR_plus_3 = [i['+3ATR'] for i in data]
    ATR_minus_1 = [i['-1ATR'] for i in data]
    ATR_minus_2 = [i['-2ATR'] for i in data]
    ATR_minus_3 = [i['-3ATR'] for i in data]

    plt.subplot(rows, columns, 2)
    plt.plot(x, close)
    plt.plot(x, ma10)
    plt.plot(x, ma50)
    plt.plot(x, ATR_plus_1, color="gray", linestyle='dashed')
    plt.plot(x, ATR_plus_2, color="gray", linestyle='dashed')
    plt.plot(x, ATR_plus_3, color="gray", linestyle='dashed')
    plt.plot(x, ATR_minus_1, color="gray", linestyle='dashed')
    plt.plot(x, ATR_minus_2, color="gray", linestyle='dashed')
    plt.plot(x, ATR_minus_3, color="gray", linestyle='dashed')
    plt.title("ATR Channel")

    # plt.subplot(rows, columns, 2)
    # bool_data = BooleanLine(data)
    # x = x[:-20]
    # kama = kama[-len(x):]
    # plt.plot(x, [i['close'] for i in bool_data])
    # plt.plot(x, [i['BBL'] for i in bool_data], color="gray", linestyle='dashed')
    # plt.plot(x, [i['BBU'] for i in bool_data], color="gray", linestyle='dashed')
    # plt.plot(x, kama)
    # plt.title("Boolean Channel")

    plt.suptitle(name)
    plt.savefig(f"{save_path}/{code if name == 'UNKNOWN' else name}.png")
    # plt.show()
    plt.close()


def market_chart(code=None, name=None):
    import mplfinance as mpf
    if code:
        if not name:
            name = get_name_by_code(code)
    elif name:
        if not code:
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
    data = get_stock_kline_with_indicators(code, period=101, limit=400)
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
    mpf.plot(df,
             type="candle",
             title=f"{code}  {name}",
             ylabel="price($)",
             style=s,
             volume=True,
             ylabel_lower="volume(shares)",
             figratio=(12, 6),
             figscale=8,
             mav=(50, 150, 200),
             show_nontrading=True,
             # savefig=f"{save_path}/{name}.png"
             )
    logging.warning(f"{code}\t{name}")


def market_chart_boolean(code=None, name=None):
    import mplfinance as mpf
    if code:
        if not name:
            name = get_name_by_code(code)
    elif name:
        if not code:
            code = get_code_by_name(name)
    else:
        logging.error("code 和 name 必须传一个")
        sys.exit()
    save_path = "../STOCK_CHANNEL"
    if str(code).startswith('1') or str(code).startswith('5'):
        save_path += "/ETF"
    elif str(code)[0] in ('0', '3', '6'):
        save_path += "/STOCK"
    else:
        save_path += "/INDUSTRY"
    code = str(code).split('.')[0]
    if str(code)[0] in ('0', '3', '6', '1', '5', '4', '8'):
        data = get_stock_kline_with_indicators(code, period=101, limit=120)
    else:
        data = get_concept_kline_v2(code, limit=120)
    data = BooleanLine(data)
    for i in data:
        i['day'] = datetime.strptime(i['day'], "%Y-%m-%d").date()
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
             figscale=8,
             # mav=(50, 150, 200),
             addplot=add_plot,
             # show_nontrading=True,
             savefig=f"{save_path}/{name}.png"
             )
    logging.warning(f"{code}\t{name}")


def draw_channel_by_kline(code=None, name=None):
    import mplfinance as mpf
    if code:
        if not name:
            name = get_name_by_code(code)
    elif name:
        if not code:
            code = get_code_by_name(name)
    else:
        logging.error("code 和 name 必须传一个")
        sys.exit()
    save_path = "../STOCK_CHANNEL"
    if str(code)[0] in ('1', '5'):
        save_path += "/ETF"
    elif str(code)[0] in ('0', '3', '6'):
        save_path += "/STOCK"
        # save_path += "/beautiful"
    else:
        save_path += "/INDUSTRY"
    code = str(code).split('.')[0]
    data = Channel(code=code, name=name).kline
    if len(data) > 100:
        data = data[-100:]
    for i in range(len(data)):
        data[i]['day'] = date.today()+timedelta(days=i)
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
        y_on_right=False,
        marketcolors=mc,
        rc={"font.family": "SimHei"}
    )
    add_plot = [
        mpf.make_addplot(df.get('up_channel')),
        mpf.make_addplot(df.get('down_channel')),
        # mpf.make_addplot(df.get('KAMA')),
    ]
    mpf.plot(df,
             type="candle",
             title=f"{code}  {name}",
             ylabel="price($)",
             style=s,
             volume=True,
             ylabel_lower="volume(shares)",
             figratio=(12, 6),
             figscale=4,
             mav=(20,),
             addplot=add_plot,
             show_nontrading=True,
             # savefig=f"{save_path}/{name.replace('*', '')}.png"
             )
    # logging.warning(f"{code}\t{name}")


def draw_channel_by_kline_V2(kline: list, name=None):
    import mplfinance as mpf
    save_path = "../STOCK_CHANNEL"
    if len(kline) > 100:
        kline = kline[-100:]
    for i in range(len(kline)):
        kline[i]['day'] = date.today()+timedelta(days=i)
    df = pd.DataFrame(kline)
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
        y_on_right=False,
        marketcolors=mc,
        rc={"font.family": "SimHei"}
    )
    add_plot = [
        mpf.make_addplot(df.get('up_channel')),
        mpf.make_addplot(df.get('down_channel'))
    ]
    mpf.plot(df,
             type="candle",
             title=f"{name}",
             ylabel="price($)",
             style=s,
             volume=True,
             ylabel_lower="volume(shares)",
             figratio=(6, 3),
             figscale=4,
             mav=(20,),
             addplot=add_plot,
             show_nontrading=True,
             # savefig=f"{save_path}/ETF/HOUR/{name.replace('*', '')}.png"
             )


def draw_boolean_rsi(code, is_index=False, period=101, limit=150):
    import mplfinance as mpf
    code = str(code).split('.')[0]
    kline = get_stock_kline_with_indicators(code, is_index=is_index, period=period, limit=limit)
    data = BooleanLine(RSI(kline))
    for i in range(len(data)):
        data[i]['day'] = date.today()+timedelta(days=i)
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
        y_on_right=False,
        marketcolors=mc,
        rc={"font.family": "SimHei"}
    )
    add_plot = [
        mpf.make_addplot(df.get('BBU')),
        mpf.make_addplot(df.get('BBL')),
    ]
    mpf.plot(df,
             type="candle",
             title=f"{code}-CURRENT RSI:{data[-1]['RSI']} HIGH RSI:{max([i['RSI'] for i in data[-20:]])}",
             ylabel="price($)",
             style=s,
             volume=True,
             ylabel_lower="volume(shares)",
             figratio=(12, 6),
             addplot=add_plot,
             show_nontrading=True,
             )


def momentum_stock_draw_channel():
    p1 = find_institutions_holding()
    p2 = select_high_rps_stock(days=[20, 50, 120, 250])
    pool = []
    for _, v in p1.items():
        if v in p2 and not v['code'].startswith('688'):
            pool.append(v)
    logging.warning(f"机构持股&高RPS(剔除科创板)\t{len(pool)}\t{pool}")
    for i in pool:
        draw_channel_by_kline(code=i['code'], name=i['name'])


if __name__ == "__main__":
    draw_channel_by_kline(code="300827")

