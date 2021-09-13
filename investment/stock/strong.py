from security import get_stock_kline_with_volume
# 笑傲牛熊, 曼斯菲尔德相对强度


def index_applies():
    indexes = ['000001', '000300', '000905', '399006', '000688']
    applies_120 = 0
    result = []
    for index in indexes:
        data120 = get_stock_kline_with_volume(index, is_index=True, limit=120)
        pre, current = data120[0]['close'], data120[-1]['close']
        if applies_120 < current/pre:
            applies_120 = current/pre
            result = data120
    return result if result else None


def GET_RSMANSIFIELD(code):
    index = index_applies()
    index_applies_list = [i['applies'] for i in index]
    data120 = get_stock_kline_with_volume(code, limit=120)
    stock_applies_list = [i['applies'] for i in data120]


