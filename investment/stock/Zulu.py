import tushare
pro = tushare.pro_api("b625f0b90069039346d199aa3c0d5bc53fd47212437337b45ba87487")


class Stock_BaseInfo:
    def __init__(self):
        self.code = None    # 股票代碼
        self.name = None    # 股票名稱
        self.industry = None    # 行业
        self.pe = None      # 市盈率
        self.float_share = None  # 流通股本
        self.total_share = None  # 总股本
        self.total_assets = None    # 总资产
        self.liquid_assets = None   # 流动资产
        self.fixed_assets = None    # 固定资产
        self.reserved = None    # 公积金
        self.reserved_pershare = None   # 每股公积金
        self.eps = None     # 每股收益
        self.bvps = None    # 每股净资产
        self.pb = None      # 市净率
        self.list_date = None   # 上市日期
        self.undp = None    # 未分配利润
        self.per_undp = None    # 每股未分配利润
        self.rev_yoy = None     # 收入同比
        self.profit_yoy = None  # 利润同比
        self.gpr = None     # 毛利率
        self.npr = None     # 净利润率
        self.holder_num = None  # 股东人数

    def __str__(self):
        return f"代码:{self.code}\t名称:{self.name}\t行业:{self.industry}\tPE:{self.pe}\tPB:{self.pb}" \
               f"\t收入同比:{self.rev_yoy}\t利润同比:{self.profit_yoy}\t每股收益:{self.eps}\t每股未分配利润:{self.per_undp}" \
               f"\t每股公积金:{self.reserved_pershare}\t每股净资产:{self.bvps}\t毛利率:{self.gpr}\t净利润率:{self.npr}"

    def get_yield(self, day=365):
        from datetime import date, timedelta
        days = int(str(date.today() - timedelta(days=day)).replace('-', ''))
        data = pro.daily(ts_code=self.code, start_date=days, fields='trade_date,close')
        now = data.values[0][1]
        last_year = data.values[-1][1]
        yields = round((now - last_year) / last_year * 100, 2)
        return yields

    @staticmethod
    def growth_run():
        data = pro.bak_basic(trade_date='20191231')
        for i in data.values:
            if 0 < int(i[16]) < 20200101:
                s = Stock_BaseInfo()
                s.code = i[1]
                s.name = i[2]
                s.industry = i[3]
                s.pe = float(i[5])
                s.pb = float(i[15])
                s.reserved_pershare = float(i[12])
                s.eps = float(i[13])
                s.bvps = float(i[14])
                s.float_share = i[6]
                s.total_share = i[7]
                s.per_undp = float(i[18])
                s.rev_yoy = float(i[-5])
                s.profit_yoy = float(i[-4])
                s.gpr = float(i[-3])
                s.npr = float(i[-2])
                s.peg = round(s.pe / s.profit_yoy, 2) if s.profit_yoy != 0 else 0
                # s.one_year_yield = s.get_yield()
                # s.one_month_yield = s.get_yield(30)
                if 0 < s.pe and 0 < s.peg:
                    print(f"代码:{s.code}\t名称:{s.name}\tPE:{s.pe}\t每股收益:{s.eps}\t利润同比:{s.profit_yoy}\t收入同比:{s.rev_yoy}\tPEG:{s.peg}\t")  # 一年涨幅:{s.one_year_yield}\t一月涨幅:{s.one_month_yield}


Stock_BaseInfo().growth_run()

