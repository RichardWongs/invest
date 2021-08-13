import time
import requests,json
from datetime import datetime,date,timedelta


def get_ten_year_Treasury_yields():
    url = "https://api-ddc.wallstcn.com/market/real?fields=symbol%2Cen_name%2Cprod_name%2Clast_px%2Cpx_change%2Cpx_change_rate%2Chigh_px%2Clow_px%2Copen_px%2Cpreclose_px%2Cmarket_value%2Cturnover_volume%2Cturnover_ratio%2Cturnover_value%2Cdyn_pb_rate%2Camplitude%2Cdyn_pe%2Ctrade_status%2Ccirculation_value%2Cupdate_time%2Cprice_precision%2Cweek_52_high%2Cweek_52_low%2Cstatic_pe%2Csource&prod_code=CN10YR.OTC"
    headers = {
        'Content-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.106 Safari/537.36"
    }
    response = requests.get(url, headers=headers).json()
    yields = response['data']['snapshot']['CN10YR.OTC'][2]
    print(yields)
    # print(json.dumps(response, indent=4, ensure_ascii=False))



def fund_rank():
    # 基金业绩排行榜
    page = 1
    fund_type = 1
    # fund_type: 0 全部  1 股票型  2 债券型  3 混合型  4 指数型  6 QDII  7 LOF
    sort = 13
    # sort: 6 近一周 7 近一月 8 近三月 9 近六月 10 近一年 11 近两年 12 近三年 13 今年来 14 成立以来
    timestamp = int(time.time())*1000
    url = f"http://fund.jrj.com.cn/json/netrank/open?type={fund_type}&mana=0&limit=300&page={page}&sort={sort}&order=1&vname=fundranklist&_={timestamp}"
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.106 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    response.encoding = "utf-8"
    resp = response.text.split('var fundranklist=')[1]
    resp = json.loads(resp)
    for i in resp['list']:
        print(i['fundSName'], i['fundCode'])


# 沪深300 399300
# 中证500 399905
# 中小100 399005
# 创业板指 399006
code = 399006
url = f"http://push2his.eastmoney.com/api/qt/stock/kline/get?cb=jQuery112405503131440309301_1624288788353&secid=0.{code}&ut=fa5fd1943c7b386f172d6893dbfba10b&fields1=f1%2Cf2%2Cf3%2Cf4%2Cf5&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57%2Cf58&klt=101&fqt=0&beg=20210101&end=20220101&_=1624288788410"
r = requests.get(url)
# print(r.text)
r = r.text.split('(')[1].split(')')[0]
# r = r.split(')')[0]
print(r)
