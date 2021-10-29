# encoding: gbk
import logging
import requests
import matplotlib.pyplot as plt
from monitor import EMA_V2, get_stock_kline_with_indicators, institutions_holding_rps_stock, KAMA
plt.rcParams["font.sans-serif"] = ["SimHei"]  # 设置字体
plt.rcParams["axes.unicode_minus"] = False  # 该语句解决图像中的“-”负号的乱码问题


class Channel:

    def __init__(self, code, name):
        self.code = code
        self.name = name
        self.kline = get_stock_kline_with_indicators(code, limit=250)
        self.channel_trade_system()

    def channel_trade_system(self):
        N, M = 13, 26
        self.kline = KAMA(EMA_V2(EMA_V2(EMA_V2(self.kline, N), M), 50))
        up_channel_coefficients, down_channel_coefficients = find_channel_coefficients(
            self.kline)
        logging.warning(f"code: {self.code}\tname: {self.name}\t"
                        f"up_channel_coefficients:{up_channel_coefficients}\t"
                        f"down_channel_coefficients:{down_channel_coefficients}")
        for i in range(len(self.kline)):
            self.kline[i]['up_channel'] = self.kline[i][f'ema{M}'] + \
                up_channel_coefficients * self.kline[i][f'ema{M}']
            self.kline[i]['down_channel'] = self.kline[i][f'ema{M}'] - \
                down_channel_coefficients * self.kline[i][f'ema{M}']

    def calc_coefficients(
            self, M=26, up_channel_coefficients=0.01, down_channel_coefficients=0.01):
        up_count, down_count = 0, 0
        total_count = len(self.kline)
        for i in range(len(self.kline)):
            self.kline[i]['up_channel'] = self.kline[i][f'ema{M}'] + \
                up_channel_coefficients * self.kline[i][f'ema{M}']
            self.kline[i]['down_channel'] = self.kline[i][f'ema{M}'] - \
                down_channel_coefficients * self.kline[i][f'ema{M}']
        for i in range(len(self.kline)):
            if self.kline[i]['close'] > self.kline[i]['up_channel']:
                up_count += 1
            if self.kline[i]['close'] < self.kline[i]['down_channel']:
                down_count += 1
        return round((total_count - up_count) / total_count,
                     2), round((total_count - down_count) / total_count, 2)

    def find_channel_coefficients(self):
        up_channel_coefficients, down_channel_coefficients = 0.05, 0.05
        standard = 0.95
        ucc, dcc = None, None
        while True:
            up_ratio, down_ratio = self.calc_coefficients(up_channel_coefficients=up_channel_coefficients,
                                                          down_channel_coefficients=down_channel_coefficients)
            if up_ratio < standard:
                up_channel_coefficients += 0.01
            else:
                ucc = up_channel_coefficients
            if down_ratio < standard:
                down_channel_coefficients += 0.01
            else:
                dcc = down_channel_coefficients
            if ucc and dcc:
                break
        return round(up_channel_coefficients, 2), round(
            down_channel_coefficients, 2)


def Channel_Trade_System(kline: list, code=None, name=None):
    N, M = 13, 26
    kline = EMA_V2(EMA_V2(kline, N), M)
    up_channel_coefficients, down_channel_coefficients = find_channel_coefficients(
        kline)
    logging.warning(f"code: {code}\tname: {name if name else 'UNKNOWN'}\t"
                    f"上通道系数:{up_channel_coefficients}\t"
                    f"下通道系数:{down_channel_coefficients}")
    for i in range(len(kline)):
        kline[i]['up_channel'] = kline[i][f'ema{M}'] + \
            up_channel_coefficients * kline[i][f'ema{M}']
        kline[i]['down_channel'] = kline[i][f'ema{M}'] - \
            down_channel_coefficients * kline[i][f'ema{M}']
    return kline


def calc_coefficients(kline, M=26, up_channel_coefficients=0.01,
                      down_channel_coefficients=0.01):
    up_count, down_count = 0, 0
    total_count = len(kline)
    for i in range(len(kline)):
        kline[i]['up_channel'] = kline[i][f'ema{M}'] + \
            up_channel_coefficients * kline[i][f'ema{M}']
        kline[i]['down_channel'] = kline[i][f'ema{M}'] - \
            down_channel_coefficients * kline[i][f'ema{M}']
    for i in range(len(kline)):
        if kline[i]['close'] > kline[i]['up_channel']:
            up_count += 1
        if kline[i]['close'] < kline[i]['down_channel']:
            down_count += 1
    return round((total_count - up_count) / total_count,
                 2), round((total_count - down_count) / total_count, 2)


def find_channel_coefficients(kline: list):
    up_channel_coefficients, down_channel_coefficients = 0.01, 0.01
    standard = 0.95
    ucc, dcc = None, None
    while True:
        up_ratio, down_ratio = calc_coefficients(kline,
                                                 up_channel_coefficients=up_channel_coefficients,
                                                 down_channel_coefficients=down_channel_coefficients)
        if up_ratio < standard:
            up_channel_coefficients += 0.01
        else:
            ucc = up_channel_coefficients
        if down_ratio < standard:
            down_channel_coefficients += 0.01
        else:
            dcc = down_channel_coefficients
        if ucc and dcc:
            break
    return round(up_channel_coefficients, 2), round(
        down_channel_coefficients, 2)


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
        'Cookie': "kbzw__Session=fs8oure2m3mrir3m4toc4cbh77; Hm_lvt_164fe01b1433a19b507595a43bf58262=1635233006; kbz_newcookie=1; kbzw_r_uname=RichardWongs; kbzw__user_login=7Obd08_P1ebax9aXycvZydjp18_Q3sjnmrCW6c3q1e3Q6dvR1YyhmNjcqpqwzdrI25HZ2qzbkabF2NrWy97R2cbckqyopJmcndbd3dPGpJ2skq-Sq6qUs47FotLWoLbo5uDO4sKmrKGogZi43efZ2PDfl7DKgainoaickLjd56udtIzvmKqKl7jj6M3VuNnbwNLtm6yVrY-qrZOgrLi1wcWhieXV4seWqNza3ueKkKTc6-TW3puwlqSRpaupqJeemKWZyMrfzenLpZaqrqGrlw..; Hm_lpvt_164fe01b1433a19b507595a43bf58262=1635233039"
    }
    body = {
        'is_search': 'N',
        'rp': 50,
        'page': 1
    }
    r = requests.post(url, headers=headers).json()
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


def draw_line_by_input(code, name="UNKNOWN", save_path=r"C:\Users\Administrator\Desktop\STOCK_CHANNEL/ETF"):
    c = Channel(code, name)
    x = [i for i in range(len(c.kline))]
    close = [i['close'] for i in c.kline]
    ema13 = [i['ema13'] for i in c.kline]
    ema26 = [i['ema26'] for i in c.kline]
    ema50 = [i['ema50'] for i in c.kline]
    up_channel = [i['up_channel'] for i in c.kline]
    down_channel = [i['down_channel'] for i in c.kline]
    kama = [i['KAMA'] for i in c.kline]
    plt.plot(x, close, color='black')
    plt.plot(x, ema13, color='blue')
    plt.plot(x, ema26, color='green')
    plt.plot(x, ema50, color='pink')
    plt.plot(x, up_channel, color="red", linestyle='dashed')
    plt.plot(x, down_channel, color="green", linestyle='dashed')
    plt.plot(x, kama, color="red")
    plt.title(name)
    # plt.savefig(f'{save_path}/{name}.png', dpi=180)
    plt.show()
    plt.close()


def stock_filter_by_down_channle():
    pool = institutions_holding_rps_stock()
    result = []
    for i in pool:
        c = Channel(i['code'], i['name'])
        if c.kline[-1]['ema50'] >= c.kline[-2]['ema50']:
            if c.kline[-1]['close'] <= c.kline[-1]['down_channel'] * 1.03:
                logging.warning(i)
                result.append(i)
    return result



