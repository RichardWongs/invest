from monitor import EMA_V2, get_stock_kline_with_indicators


def channel_trade_system(kline: list):
    def find_channel_coefficients(kline: list):
        def calc_coefficients(kline, up_channel_coefficients=0.01, down_channel_coefficients=0.01):
            M = 26
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
            return round((total_count - up_count) / total_count,
                         2), round((total_count - down_count) / total_count, 2)
        up_channel_coefficients, down_channel_coefficients = 0.01, 0.01
        standard = 0.95
        ucc, dcc = None, None
        while True:
            up_ratio, down_ratio = calc_coefficients(kline=kline, up_channel_coefficients=up_channel_coefficients,
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
    N, M = 13, 26
    kline = EMA_V2(kline, M)
    up_channel_coefficients, down_channel_coefficients = find_channel_coefficients(kline=kline)
    for i in range(len(kline)):
        kline[i]['up_channel'] = kline[i][f'ema{M}'] + up_channel_coefficients * kline[i][f'ema{M}']
        kline[i]['down_channel'] = kline[i][f'ema{M}'] - down_channel_coefficients * kline[i][f'ema{M}']
    return kline






