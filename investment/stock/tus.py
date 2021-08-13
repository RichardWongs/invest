import tushare as ts
ts.set_token('b625f0b90069039346d199aa3c0d5bc53fd47212437337b45ba87487')


class FundHoldings(object):
    def __init__(self):
        self.code = None
        self.name = None
        self.date = None
        self.fundHoldingdCount = None
        self.fundHoldingdRatio = None


def get_fund_holdings():
    data = ts.fund_holdings(2021, 2)
    for i in data.values:
        s = FundHoldings()
        s.code = i[7]
        s.name = i[3]
        s.date = i[5]
        s.fundHoldingdCount = float(i[1])*10000
        s.fundHoldingdRatio = float(i[6])
        if s.fundHoldingdRatio >= 2:
            print(s.code, s.name, s.date, s.fundHoldingdRatio, s.fundHoldingdCount)




