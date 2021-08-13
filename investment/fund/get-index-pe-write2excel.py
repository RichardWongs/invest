import xlwt
import json
import requests
from datetime import datetime,date



def set_style(name,height,bold=False):
	style = xlwt.XFStyle()
	font = xlwt.Font()
	font.name = name
	font.bold = bold
	font.color_index = 4
	font.height = height
	style.font = font
	return style


def write_excel(token):
    f = xlwt.Workbook(style_compression=2)
    sheet1 = f.add_sheet('加权PE', cell_overwrite_ok=True)
    row0 = ["指数","日期","收盘点位","静态PE", "动态PE", "PB"]

    #写第一行
    for i in range(0,len(row0)):
        sheet1.write(0,i,row0[i],set_style('Times New Roman',220,True))
    row = 1
    for i in add_weight_PE(token):
        colum0 = [i.get('marketId'), i.get('date'), i.get('close'), i.get('pe'), i.get('peTtm'), i.get('pb')]
        column = 0
        for j in range(0, len(colum0)):
            print(row, column, colum0[j])
            sheet1.write(row, column, colum0[j], set_style('Times New Roman', 220, True))
            column += 1
        row += 1
    f.save('沪深300加权PE百分位.xls')


def get_marketcap_gdp():
    url = "https://legulegu.com/stockdata/marketcap-gdp/get-marketcap-gdp"
    params = {
        "token": "430193a6f22c81c76b3c08aa8e3411db"
    }
    response = requests.get(url, params=params)
    content = response.content.decode()
    # print(content)
    contents = []
    for i in json.loads(content):
        timestamp = i.get("date")
        i["date"] = date.fromtimestamp(timestamp/1000).strftime("%Y-%m-%d")
        i["总市值比GDP"] = round(i["marketCap"]/i["gdp"], 2)
        contents.append(i)
    return contents


def get_equal_weight_pe():
    # 沪深300等权动态市盈率
    url = "https://legulegu.com/api/stockdata/market-ttm-lyr/get-data"
    params = {
        "marketId": "000300.XSHG",
        "token": "430193a6f22c81c76b3c08aa8e3411db"
    }
    response = requests.get(url, params=params)
    conent = response.content.decode()
    contents = []
    for i in json.loads(conent):
        timestamp = i.get("date")
        i["date"] = date.fromtimestamp(timestamp/1000).strftime("%Y-%m-%d")
        del i["averagePELYR"]
        del i["middlePELYR"]
        del i["middlePETTM"]
        contents.append(i)
    return contents


def add_weight_PE(token):
    # 加权市盈率
    url = "https://legulegu.com/api/stock-data/weight-pe"
    params = {
        "marketId": "000300.SH",
        "token": token
    }
    response = requests.get(url, params=params).json()
    if "data" in response.keys():
        data = response.get('data')
        for i in data:
            timestamp = i.get('date')
            i['date'] = datetime.fromtimestamp(timestamp/1000).strftime("%Y-%m-%d")
    return response.get('data')


if __name__ == "__main__":
    write_excel("42f8d09942bd11ddf11b2b6ae76439cd")
