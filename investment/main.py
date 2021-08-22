''':cvar
<<股票魔法师II>>
股票必须符合以下8条标准，才能确认其已经处在上涨趋势的第二阶段。
（1）股价高于150日（30周）和200日（40周）均线。
（2）150日均线高于200日均线。
（3）200日均线上涨至少1个月（最好4至5个月或更长）。
（4）50日均线（10周均线）高于150日和200日均线。
（5）目前的股价比52周内最低点至少高出25%（许多最好的股票在健康的筑底期后能比52周最低点高出100%、300%甚至更高）。
（6）目前的股价处在其52周高点的25%以内（越接近新高越好）。
（7）相对实力（RS）排名不低于70，更好的选择一般是在90左右（注：RS线不应该有明显的下跌趋势，我希望RS线上涨至少6周，最好是13周以上）
（8）因股价上涨突破前期底部，现价格应在50日均线之上。
'''
from RPS.quantitative_screening import get_RPS_stock_pool


def get_average_price(closes, weeks):
    assert len(closes) >= weeks
    return sum(closes[-weeks:])/weeks


def stock_filter(code):
    from security import get_stock_kline_with_volume
    data = get_stock_kline_with_volume(code, period=102, limit=60)
    close = data[-1]['close']
    close_list = [i['close'] for i in data]
    high_list = [i['high'] for i in data]
    highest = max(high_list[-52:])
    low_list = [i['low'] for i in data]
    lowest = min(low_list[-52:])
    week_10 = get_average_price(close_list, weeks=10)
    week_30 = get_average_price(close_list, weeks=30)
    week_40 = get_average_price(close_list, weeks=40)
    week_diff1 = get_average_price(close_list[:-12], weeks=40)
    week_diff2 = get_average_price(close_list[:-6], weeks=40)
    if close > week_30 > week_40:
        if week_40 > week_diff2 > week_diff1:
            if week_10 > week_30:
                if close > lowest * 1.25 and close > highest * 0.75 and close > week_10:
                    return True


if __name__ == '__main__':
    pool = get_RPS_stock_pool()
    for i in pool:
        if stock_filter(i[0]):
            print(i)
