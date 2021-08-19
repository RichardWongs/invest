# encoding: utf-8


def get_all_stock_market_value():
    # 获取全市场股票总市值
    import tushare
    pro = tushare.pro_api("b625f0b90069039346d199aa3c0d5bc53fd47212437337b45ba87487")
    data = pro.bak_daily()
    stock_list = []
    for i in data.values:
        if i[23] > 0:
            tmp = {'code': i[0].split('.')[0], 'name': i[2]}    # , 'total_market_value': i[23]
            stock_list.append(tmp)
    # return sorted(stock_list, key=lambda x: x['total_market_value'], reverse=True)
    return stock_list


pool = [{'code': '002585', 'name': '双星新材'}, {'code': '002594', 'name': '比亚迪'}, {'code': '000898', 'name': '鞍钢股份'}, {'code': '002015', 'name': '协鑫能科'}, {'code': '688202', 'name': '美迪西'}, {'code': '002407', 'name': '多氟多'}, {'code': '000848', 'name': '承德露露'}, {'code': '002312', 'name': '川发龙蟒'}, {'code': '000829', 'name': '天音控股'}, {'code': '600219', 'name': '南山铝业'}, {'code': '000155', 'name': '川能动力'}, {'code': '002430', 'name': '杭氧股份'}, {'code': '688139', 'name': '海尔生物'}, {'code': '603599', 'name': '广信股份'}, {'code': '002709', 'name': '天赐材料'}, {'code': '002002', 'name': '鸿达兴业'}, {'code': '000807', 'name': '云铝股份'}, {'code': '002326', 'name': '永太科技'}, {'code': '601600', 'name': '中国铝业'}, {'code': '300207', 'name': '欣旺达'}, {'code': '688188', 'name': '柏楚电子'}, {'code': '002245', 'name': '蔚蓝锂芯'}, {'code': '002155', 'name': '湖南黄金'}]

