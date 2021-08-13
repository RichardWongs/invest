from datetime import date,datetime
from report.Kline import Stock_BaseInfo
from utils.database_connect import set_data_from_mysql
from report.stock_list import STOCKS

sqls = []
stocks = STOCKS[4500:4600]
for i in range(len(stocks)):
    s = Stock_BaseInfo(stocks[i][1].split('.')[0])
    s.name = stocks[i][2]
    s.industry = stocks[i][3]
    s.pe = float(stocks[i][5])
    s.pb = float(stocks[i][15])
    s.rev_yoy = float(stocks[i][-5])
    s.profit_yoy = float(stocks[i][-4])
    s.gpr = float(stocks[i][-3])
    s.npr = float(stocks[i][-2])
    print(i, s)
    sql = f"INSERT INTO stock_momentum(CODE,NAME,INDUSTRY,PE,PB,REV_YOY,PROFIT_YOY,GPR,NPR,MOMENTUM,CUMULATIVE_YIELD,UPDATE_TIME) VALUES ('{s.code}','{s.name}','{s.industry}',{s.pe},{s.pb},{s.rev_yoy},{s.profit_yoy},{s.gpr},{s.npr},{s.momentum.momentum_value if s.momentum.momentum_value else 'NULL'},{s.momentum.cumulative_yield if s.momentum.cumulative_yield else 'NULL'}, '{datetime.today()}')"
    # sqls.append(sql)
    set_data_from_mysql("stock", sql)
