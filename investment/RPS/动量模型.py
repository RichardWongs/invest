# encoding: utf-8
import json
import logging
import os
import pickle
from datetime import date, timedelta

from RPS.holding import fund_holding, fc_holding
from RPS.stock_pool import NEW_STOCK_LIST
from monitor import get_market_data, get_stock_kline_with_indicators, MA_V2, get_industry_by_code
from monitor.whole_market import RedisConn
from momentum.concept import get_concept_list, get_industry_list, get_concept_kline, select_composition_stock
start_date = int(str(date.today() - timedelta(days=400)).replace('-', ''))
host = "172.16.1.162"
# host = "192.168.124.20"


def saveMarketData2Redis():
    # 查询全市场股票行情数据存储到redis中
    N = 20
    day = 1
    client = RedisConn(host=host)
    key = f"stock:momentum:*"
    keys = client.keys(key)
    keys = [i.decode() for i in keys]
    counter = 1
    for k, v in NEW_STOCK_LIST.items():
        if f"stock:momentum:{k}" not in keys:
            # kline = get_market_data(k, start_date=start_date)
            kline = get_stock_kline_with_indicators(k, limit=300)
            if kline:
                if len(kline) > 0:
                    if len(kline) > 20:
                        v['applies_20'] = round(
                            (kline[-day]['close'] - kline[-(N + day)]['close']) / kline[-(N + day)]['close'], 2)
                    else:
                        v['applies_20'] = round(
                            (kline[-day]['close'] - kline[0]['close']) / kline[0]['close'], 2)
                    v['kline'] = kline
                    client.set(f"stock:momentum:{k}", json.dumps(v))
                print(counter, v)
                counter += 1


def saveMarketData2Local():
    client = RedisConn(host=host)
    keys = [i.decode() for i in client.keys(f"stock:momentum:*")]
    target = []
    limit = 1600
    count = 0
    fileNO = 1
    lastOne = json.loads(client.get(keys[-1]))
    for i in keys:
        target.append(json.loads(client.get(i)))
        count += 1
        if count >= limit or json.loads(client.get(i)) == lastOne:
            with open(f"MomentumMarketData-{fileNO}.bin", 'wb') as f:
                f.write(pickle.dumps(target))
            fileNO += 1
            count = 0
            target = []


def readMarketDataFromLocal():
    # 从本地文件中读取行情数据
    files = os.listdir(os.curdir)
    target = []
    for i in files:
        if i.startswith('MomentumMarketData'):
            with open(i, 'rb') as f:
                content = pickle.loads(f.read())
                target += content
    return target


def find_institutions_holding():
    # 剔除基金持股小于2%或外资持股小于0.5%的个股
    pool = {}
    f = fund_holding + fc_holding
    for i in f:
        pool[i['code']] = i
    logging.warning(f"机构持股: {len(pool)}\t{pool}")
    return pool


def find_high_rps_stock():
    # 剔除20日RPS强度小于85的个股
    content = readMarketDataFromLocal()
    stockCount = int(len(content) * 0.15)
    result = []
    for i in content:
        del i['kline']
        result.append(i)
    result = sorted(result, key=lambda x: x['applies_20'], reverse=True)
    return result[:stockCount]


def find_new_stock(pool):
    # 剔除上市不足一个月的新股
    target = []
    for i in pool:
        if int(i['list_date']) < int(
                str(date.today() - timedelta(30)).replace('-', '')):
            target.append(i)
    return target


def week52_new_high():
    # 统计当日创下一年新高的数量
    target = []
    content = readMarketDataFromLocal()
    for i in content:
        if len(i['kline']) > 250:
            kline = i['kline'][-250:]
        else:
            kline = i['kline']
        highest = max([i['high'] for i in kline])
        if highest == kline[-1]['high']:
            del i['kline']
            target.append(i)
    return target


def industry_distribution():
    # 全市场个股行业分布统计
    r = []
    for _, v in NEW_STOCK_LIST.items():
        if v['industry']:
            r.append(v['industry'])
    s = set(r)
    t = {}
    for i in s:
        t[i] = r.count(i)
    return t


def find_trend_pool():
    from stock.StockFinancial import read_quarter_report
    quarter = read_quarter_report()  # 季报正增长
    for i in quarter:
        i['code'] = f"{i['code']}.SH" if i['code'].startswith(
            '6') else f"{i['code']}.SZ"
    tmp = find_institutions_holding()
    ins = []    # 机构&外资持股
    for _, v in tmp.items():
        ins.append(v)
    result = [i for i in ins if i in quarter]
    k = readMarketDataFromLocal()
    movements = []
    for i in k:
        kline = MA_V2(MA_V2(MA_V2(i['kline'], 50), 150), 200)
        highest = max([i['high'] for i in kline])
        lowest = min([i['low'] for i in kline])
        close = kline[-1]['close']
        if close > kline[-1]['ma50'] > kline[-1]['ma150'] > kline[-1]['ma200']:
            if close > lowest * 1.3 and close > highest * 0.75:
                movements.append({'code': i['code'], 'name': i['name']})
    print(len(result), result)
    print(len(movements), movements)
    results = [i for i in result if i in movements]
    print(len(results), results)


def run():
    # 主线板块统计
    rps_pool = find_high_rps_stock()
    rps_pool = find_new_stock(rps_pool)
    institution_pool = find_institutions_holding()
    result = []
    for i in rps_pool:
        if i['code'] in institution_pool.keys():
            result.append(i)
    logging.warning(f"机构动量榜详情: {len(result)}\t{result}")
    all_new_high = week52_new_high()
    institution_new_high = [i for i in result if i in all_new_high]
    logging.warning(
        f"全市场创新高个股数量:{len(all_new_high)}\t机构动量榜个股数量:{len(result)}\t创新高个股数量:{len(institution_new_high)}\t全市场创新高个股详情:{all_new_high}")
    industrys = [i['industry'] for i in result]
    industrySet = set(industrys)
    target = []
    t = industry_distribution()
    for i in industrySet:
        count = industrys.count(i)
        total_count = t[i]
        tmp = {'industry': i, 'score': round(count * count / total_count, 2), 'count': count,
               'pool': [f"{j['code']}-{j['name']}" for j in result if j['industry'] == i]}
        target.append(tmp)
    target = sorted(target, key=lambda x: x['score'], reverse=True)
    for i in target:
        logging.warning(i)
    return result


def run_v2():
    from momentum.concept import get_concept_list, get_industry_list, select_composition_stock
    CONCEPT_LIST = get_concept_list() + get_industry_list()
    rps_pool = find_high_rps_stock()
    rps_pool = find_new_stock(rps_pool)
    institution_pool = find_institutions_holding()
    result = []
    for i in rps_pool:
        if i['code'] in institution_pool.keys():
            result.append(i)
    for i in CONCEPT_LIST:
        i['score'] = 0
        i['momentumPool'] = []
        i['pool'] = select_composition_stock(i['code'])
        tmp_name = [i['name'] for i in i['pool']]
        i['momentumPool'] = [
            f"{i['code']}-{i['name']}" for i in result if i['name'] in tmp_name]
        i['score'] = round(len(i['momentumPool']) *
                           len(i['momentumPool']) / len(i['pool']), 2)
    CONCEPT_LIST = sorted(CONCEPT_LIST, key=lambda x: x['score'], reverse=True)
    for i in CONCEPT_LIST:
        del i['pool']
        if i['score'] >= 1:
            logging.warning(i)
    return CONCEPT_LIST


def run_v3():
    # 计算各行业板块最近20日的累计涨跌幅和板块成份股
    industry_list = get_industry_list()
    for i in industry_list:
        kline = get_concept_kline(i['code'])
        i['applies'] = round((kline[-1] - kline[0]) / kline[0] * 100, 2)
        i['pool'] = select_composition_stock(i['code'])
    industry_list = sorted(
        industry_list,
        key=lambda x: x['applies'],
        reverse=True)
    for i in industry_list:
        logging.warning(i)


def find_new_high_stock():
    # 寻找过去N天内曾创一年新高的个股
    N, M = 10, 250
    target = []
    data = readMarketDataFromLocal()
    count = 1
    for i in data:
        kline = i['kline']
        if len(kline) > (N + M):
            highest = max([i['high'] for i in kline[-(N + M):-N]])
        else:
            highest = max([i['high'] for i in kline])
        if max([i['high'] for i in kline[-N:]]) > highest:
            del i['kline']
            del i['applies_20']
            del i['list_date']
            # if i['industry'] in ('半导体', '电气设备', '汽车配件', '电器仪表', '元器件',
            # '新型电力', '互联网', '专用机械', '软件服务'):
            logging.warning(f"{count}\t{i}")
            target.append(i)
            count += 1
    return target


def find_new_low_stock():
    # 寻找长期趋势向下,且过去N天内不再创新低的个股(寻找反转)
    N, M = 50, 250
    target = []
    data = readMarketDataFromLocal()
    institutions = find_institutions_holding()
    institutions = [i for i in institutions]
    count = 1
    for i in data:
        if len(i['kline']) > M and i['code'] in institutions:
            kline = MA_V2(i['kline'], 150)
            if kline[-1]['ma150'] < kline[-2]['ma150']:
                lowest = min([i['low'] for i in kline[:-N]])
                lowest_latest = min([i['low'] for i in kline[-N:]])
                if lowest_latest > lowest:
                    del i['kline']
                    del i['list_date']
                    logging.warning(f"{count}\t{i}")
                    target.append(i)
                    count += 1
    return target


if __name__ == "__main__":
    saveMarketData2Redis()
    saveMarketData2Local()
    # run()
    # find_new_low_stock()
