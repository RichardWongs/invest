from monitor import EMA_V2
from RPS.RPS_DATA import *


def get_stock_list():
    # 获取沪深股市股票列表, 剔除上市不满一年的次新股
    df = pro.stock_basic(exchange='', list_status='L',
                         fields='ts_code,symbol,name,industry,list_date')  # fields='ts_code,symbol,name,area,industry,'
    df = df[df['list_date'].apply(int).values < begin_date]
    # 获取当前所有非新股次新股代码和名称
    codes = df.ts_code.values
    names = df.name.values
    industrys = df.industry.values
    stock_list = []
    for code, name, industry in zip(codes, names, industrys):
        tmp = {'code': code, 'name': name, 'industry': industry}
        stock_list.append(tmp)
    return stock_list


def get_data(code, start=begin_date, end=today):
    # 按照日期范围获取股票交易日期,收盘价
    time.sleep(0.1)
    df = pro.weekly(ts_code=code, start_date=start, end_date=end, fields='trade_date,close')
    # 将交易日期设置为索引值
    df.index = pd.to_datetime(df.trade_date)
    df = df.sort_index()
    return df.close


def get_all_data(stock_list):
    # 构建一个空的 dataframe 用来装数据, 获取列表中所有股票指定范围内的收盘价格
    data = pd.DataFrame()
    count = 0
    filename = f'weekly_data.csv'
    if filename in os.listdir(os.curdir):
        os.remove(filename)
    for i in stock_list:
        code = i.get('code')
        if str(code)[0] in ('0', '3', '6'):
            data[code] = get_data(code)
            print(code, i.get('name'), count)
            count += 1
        else:
            logging.warning(f"{code}\t{i.get('name')}\t非沪深交易所标的,暂不收录")
    data.to_csv(filename, encoding='utf-8')



