import json
import time
import requests
from datetime import date, timedelta


def billboard():
    # 龙虎榜详情
    today = str(date.today())
    timestamp = int(time.time())
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    params = {
        "callback": f"jQuery112302929319099589267_{timestamp}",
        "sortColumns": "SECURITY_CODE,TRADE_DATE",
        "sortTypes": "1,-1",
        "pageSize": 100,
        "pageNumber": 1,
        "reportName": "RPT_DAILYBILLBOARD_DETAILS",
        "columns": "SECURITY_CODE,SECUCODE,SECURITY_NAME_ABBR,TRADE_DATE,EXPLAIN,CLOSE_PRICE,CHANGE_RATE,BILLBOARD_NET_AMT,BILLBOARD_BUY_AMT,BILLBOARD_SELL_AMT,BILLBOARD_DEAL_AMT,ACCUM_AMOUNT,DEAL_NET_RATIO,DEAL_AMOUNT_RATIO,TURNOVERRATE,FREE_MARKET_CAP,EXPLANATION",
        "source": "WEB",
        "client": "WEB",
        "filter": f"(TRADE_DATE<='{today}')(TRADE_DATE>='{today}')"
    }
    resp = requests.get(url, params=params).text
    resp = json.loads(resp.split('(')[1].split(')')[0])
    resp = resp['result']['data']
    print(len(resp))
    for i in resp:
        print(i)


def JGMMTJ():
    # 机构买卖统计
    today = str(date.today())
    timestamp = int(time.time())
    url = f"https://datacenter-web.eastmoney.com/api/data/v1/get"
    params = {
        "callback": f"jQuery112303006030343434243_{timestamp}",
        "sortColumns": "NET_BUY_AMT,TRADE_DATE,SECURITY_CODE",
        "sortTypes": "-1,-1,1",
        "pageSize": 150,
        "pageNumber": 1,
        "reportName": "RPT_ORGANIZATION_TRADE_DETAILS",
        "columns": "SECUCODE,SECURITY_NAME_ABBR,TRADE_DATE,CLOSE_PRICE,CHANGE_RATE,BUY_TIMES,SELL_TIMES,BUY_AMT,SELL_AMT,NET_BUY_AMT,ACCUM_AMOUNT,RATIO,TURNOVERRATE,FREECAP,EXPLANATION",
        "source": "WEB",
        "client": "WEB",
        "filter": f"(TRADE_DATE<='{today}')(TRADE_DATE>='{today}')",
    }
    resp = requests.get(url, params=params).text
    resp = json.loads(resp.split('(')[1].split(')')[0])
    resp = resp['result']['data']
    print(len(resp))
    for i in resp:
        print(i)


