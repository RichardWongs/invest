import logging
from monitor import EMA_V2, get_stock_kline_with_indicators, institutions_holding_rps_stock


class Channel:

    def __init__(self, code, name):
        self.code = code
        self.name = name
        self.kline = get_stock_kline_with_indicators(code)
        self.channel_trade_system()

    def channel_trade_system(self):
        N, M = 13, 26
        self.kline = EMA_V2(EMA_V2(self.kline, N), M)
        up_channel_coefficients, down_channel_coefficients = find_channel_coefficients(self.kline)
        logging.warning(f"code: {self.code}\tname: {self.name}\t"
                        f"up_channel_coefficients:{up_channel_coefficients}\t"
                        f"down_channel_coefficients:{down_channel_coefficients}")
        for i in range(len(self.kline)):
            self.kline[i]['up_channel'] = self.kline[i][f'ema{M}'] + up_channel_coefficients * self.kline[i][f'ema{M}']
            self.kline[i]['down_channel'] = self.kline[i][f'ema{M}'] - down_channel_coefficients * self.kline[i][f'ema{M}']

    def calc_coefficients(self, M=26, up_channel_coefficients=0.05, down_channel_coefficients=0.05):
        up_count, down_count = 0, 0
        total_count = len(self.kline)
        for i in range(len(self.kline)):
            self.kline[i]['up_channel'] = self.kline[i][f'ema{M}'] + up_channel_coefficients * self.kline[i][f'ema{M}']
            self.kline[i]['down_channel'] = self.kline[i][f'ema{M}'] - down_channel_coefficients * self.kline[i][f'ema{M}']
        for i in range(len(self.kline)):
            if self.kline[i]['close'] > self.kline[i]['up_channel']:
                up_count += 1
            if self.kline[i]['close'] < self.kline[i]['down_channel']:
                down_count += 1
        return round((total_count - up_count)/total_count, 2), round((total_count - down_count)/total_count, 2)

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
        return round(up_channel_coefficients, 2), round(down_channel_coefficients, 2)


def Channel_Trade_System(kline: list, code=None, name=None):
    N, M = 13, 26
    kline = EMA_V2(EMA_V2(kline, N), M)
    up_channel_coefficients, down_channel_coefficients = find_channel_coefficients(kline)
    logging.warning(f"code: {code}\tname: {name}\t"
                    f"up_channel_coefficients:{up_channel_coefficients}\t"
                    f"down_channel_coefficients:{down_channel_coefficients}")
    for i in range(len(kline)):
        kline[i]['up_channel'] = kline[i][f'ema{M}'] + up_channel_coefficients * kline[i][f'ema{M}']
        kline[i]['down_channel'] = kline[i][f'ema{M}'] - down_channel_coefficients * kline[i][f'ema{M}']
    return kline


def calc_coefficients(kline, M=26, up_channel_coefficients=0.05, down_channel_coefficients=0.05):
    up_count, down_count = 0, 0
    total_count = len(kline)
    for i in range(len(kline)):
        kline[i]['up_channel'] = kline[i][f'ema{M}'] + up_channel_coefficients * kline[i][f'ema{M}']
        kline[i]['down_channel'] = kline[i][f'ema{M}'] - down_channel_coefficients * kline[i][f'ema{M}']
    for i in range(len(kline)):
        if kline[i]['close'] > kline[i]['up_channel']:
            up_count += 1
        if kline[i]['close'] < kline[i]['down_channel']:
            down_count += 1
    return round((total_count - up_count)/total_count, 2), round((total_count - down_count)/total_count, 2)


def find_channel_coefficients(kline: list):
    up_channel_coefficients, down_channel_coefficients = 0.05, 0.05
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
    return round(up_channel_coefficients, 2), round(down_channel_coefficients, 2)







