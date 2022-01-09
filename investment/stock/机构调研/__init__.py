import json

import requests
import time
from datetime import date, timedelta

start_date = date.today()-timedelta(days=90)
timestamp = int(time.time()*1000)
callback = f"jQuery11230991464756484082_{timestamp}"
url = f"https://datacenter-web.eastmoney.com/api/data/v1/get?callback={callback}&sortColumns=NOTICE_DATE%2CSUM%2CRECEIVE_START_DATE%2CSECURITY_CODE&sortTypes=-1%2C-1%2C-1%2C1&pageSize=50&pageNumber=1&reportName=RPT_ORG_SURVEYNEW&columns=ALL&quoteColumns=f2~01~SECURITY_CODE~CLOSE_PRICE%2Cf3~01~SECURITY_CODE~CHANGE_RATE&source=WEB&client=WEB&filter=(NUMBERNEW%3D%221%22)(IS_SOURCE%3D%221%22)(RECEIVE_START_DATE%3E%27{start_date}%27)"
resp = requests.get(url).text
resp = resp.split(f"{callback}(")[1].split(');')[0]
resp = json.loads(resp)
resp = resp['result']['data']
resp = sorted(resp, key=lambda x:x['SUM'], reverse=True)
for i in resp:
    del i['SECUCODE']
    del i['ORG_CODE']
    del i['NOTICE_DATE']
    del i['RECEIVE_END_DATE']
    del i['RECEIVE_TIME_EXPLAIN']
    del i['SOURCE']
    del i['OBJECT_CODE']
    del i['END_DATE']
    del i['RECEIVE_WAY']
    del i['RECEIVE_OBJECT_TYPE']
    del i['REMARK']
    print(i)

