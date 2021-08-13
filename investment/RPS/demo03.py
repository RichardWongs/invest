# encoding: utf-8
from datetime import date, timedelta
import requests
from bs4 import BeautifulSoup
import opencc
from security.stock_pool import whole_pool
cc = opencc.OpenCC('t2s')


def foreignCapitalHistoryHolding(exchange, holding_date=date.today()):
    url = f"https://www.hkexnews.hk/sdw/search/mutualmarket_c.aspx?t=sh&t={exchange}"
    body = {
        "today": str(date.today()).replace('-', ''),
        "sortBy": "stockcode",
        "sortDirection": "desc",
        "txtShareholdingDate": str(holding_date).replace('-', '/'),
        "btnSearch": "搜寻"
    }
    html = requests.post(url, json=body).text
    soup = BeautifulSoup(html, 'html.parser').select('div[class="mobile-list-body"]')
    data = [i.text for i in soup]
    fc_data = []
    for code, name, count in zip(range(0, len(data), 4), range(1, len(data), 4), range(2, len(data), 4)):
        tmp = {'code': data[code], 'name': cc.convert(data[name]), 'holdingCount': int(data[count].replace(',', ''))}
        fc_data.append(tmp)

    for i in whole_pool:
        for j in fc_data:
            if i['name'] == j['name']:
                j['code'] = i['code']
    return fc_data


def FC_history_Query():
    exchanges = ['sh', 'sz']
    fc_total = []
    for i in exchanges:
        data = foreignCapitalHistoryHolding(i, holding_date=date.today()-timedelta(days=42))
        fc_total += data
    print(fc_total)


FC_history_Query()
