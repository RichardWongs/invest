import logging
import tushare as ts
from datetime import date, timedelta
token = "b625f0b90069039346d199aa3c0d5bc53fd47212437337b45ba87487"
token_bake_up = "ab577af952d337b8be80b3e6119f6765e4e6b07441fd35317701bc11"
pro = ts.pro_api(token)


def get_stock_holder_num(trade_date=str(date.today()-timedelta(days=1)).replace('-', '')):
    pool = {}
    df = pro.bak_basic(trade_date=trade_date)
    for i in df.values:
        if int(i[-1]) > 0:
            tmp = {'day': i[0], 'code': i[1], 'name': i[2], 'industry': i[3], 'holder_num': i[-1]}
            pool[i[1]] = tmp
    return pool


def diff_holder_change():
    result = []
    old = get_stock_holder_num(trade_date=str(date.today()-timedelta(days=30)).replace('-', ''))
    new = get_stock_holder_num()
    counter = 1
    for k, v in old.items():
        for k2, v2 in new.items():
            if k == k2:  # and v['holder_num'] > v2['holder_num']
                v2['ratio'] = round(v2['holder_num']/v['holder_num'], 2)
                # logging.warning(f"{counter}\t{v2}")
                result.append(v2)
                counter += 1
    return sorted(result, key=lambda x: x['ratio'], reverse=False)


def holder_change_weeks():
    # now = get_stock_holder_num()
    # week1 = get_stock_holder_num(trade_date=str(date.today()-timedelta(days=8)).replace('-', ''))
    week2 = get_stock_holder_num(trade_date=str(date.today()-timedelta(days=14)).replace('-', ''))
    # week3 = get_stock_holder_num(trade_date=str(date.today()-timedelta(days=21)).replace('-', ''))
    print(week2)



