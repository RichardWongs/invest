import json
import logging
import time
import requests
from datetime import date, timedelta, datetime


def billboard(_date=date.today()):
    # 龙虎榜详情
    timestamp = int(time.time())
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    params = {
        "callback": f"jQuery112302929319099589267_{timestamp}",
        "sortColumns": "SECURITY_CODE,TRADE_DATE",
        "sortTypes": "1,-1",
        "pageSize": 100,
        "pageNumber": 1,
        "reportName": "RPT_DAILYBILLBOARD_DETAILS",
        "columns": "SECURITY_CODE,SECURITY_NAME_ABBR,TRADE_DATE,EXPLAIN,CLOSE_PRICE,CHANGE_RATE,BILLBOARD_NET_AMT,BILLBOARD_BUY_AMT,BILLBOARD_SELL_AMT,BILLBOARD_DEAL_AMT,ACCUM_AMOUNT,DEAL_NET_RATIO,DEAL_AMOUNT_RATIO,TURNOVERRATE,FREE_MARKET_CAP,EXPLANATION",
        "source": "WEB",
        "client": "WEB",
        "filter": f"(TRADE_DATE<='{_date}')(TRADE_DATE>='{_date}')"
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


def getBillboardDetail(code, _date=date.today()):
    # 获取营业部席位详情
    exchange = ['SELL', 'BUY']
    NET = 0
    for j in exchange:
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        _date = date.today()-timedelta(days=1)
        timestamp = int(time.time())
        code = str(code).split('.')[0]
        params = {
            "callback": "jQuery1123003577002073495761_1638410343239",
            "reportName": f"RPT_BILLBOARD_DAILYDETAILS{j}",
            # "columns": "SECURITY_CODE,OPERATEDEPT_NAME,CHANGE_RATE,CLOSE_PRICE,ACCUM_AMOUNT,ACCUM_VOLUME,BUY,SELL,NET",
            "columns": "SECURITY_CODE,OPERATEDEPT_NAME,CHANGE_RATE,CLOSE_PRICE,NET",
            "filter": f"(TRADE_DATE='{_date}')(SECURITY_CODE={code})",
            "pageNumber": 1,
            "pageSize": 50,
            "sortTypes": -1,
            "sortColumns": "SELL",
            "source": "WEB",
            "client": "WEB",
            "_": timestamp,
        }
        resp = requests.get(url, params=params).text
        resp = json.loads(resp.split('(')[1].split(')')[0])
        resp = resp['result']['data']
        for i in resp:
            print(i)
            if i['OPERATEDEPT_NAME'] == "机构专用":
                NET += i['NET']
    logging.warning(f"机构净买入:{NET}")


billboard(_date=date.today()-timedelta(days=1))

