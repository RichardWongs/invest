import requests, time, json


class Momentum:

    def __init__(self, code, benchmark=399296):
        '''
        code 代码
        benchmark 业绩基准代码
        benchmark_yield 业绩基准最近12个月收益率
        week52_highest 最近52周最高价
        current_price 本周收盘价
        momentum_value 动量值,当前价/52周最高价的比值
        cumulative_yield 最近12个月(不含本月)的收益率
        excess_yield 相比较业绩基准的超额收益
        '''
        self.code = code
        self.benchmark = benchmark
        self.benchmark_yield = 71.12
        self.week52_highest = None
        self.current_price = None
        self.momentum_value = None
        self.cumulative_yield = None
        self.excess_yield = None

        # self.get_benchmark()

    def __str__(self):
        return f"code:{self.code}\t当前价格:{self.current_price}\t52周最高价:{self.week52_highest}\t动量值:{self.momentum_value}\t12个月累计收益:{self.cumulative_yield}\t超额收益:{self.excess_yield}"

    def get_stock_kline(self, code=None, period=101, limit=120):
        assert period in (5, 15, 30, 60, 101, 102, 103)
        if not code:
            code = self.code
        if str(code)[0] in ('0', '1', '3'):
            secid = f'0.{code}'
        else:
            secid = f'1.{code}'
        url = f"http://67.push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            'cb': "jQuery11240671737283431526_1624931273440",
            'secid': secid,
            'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
            'fields1': 'f1,f2,f3,f4,f5,f6',
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
            'klt': period,
            'fqt': 0,
            'end': '20500101',
            'lmt': limit,
            '_': f'{int(time.time()) * 1000}'
        }
        try:
            r = requests.get(url, params=params).text
            r = r.split('(')[1].split(')')[0]
            r = json.loads(r)
            if 'data' in r.keys():
                if isinstance(r['data'], dict) and 'klines' in r['data'].keys():
                    r = r['data']['klines']
                    data = []
                    for i in range(len(r)):
                        tmp = {}
                        current_data = r[i].split(',')
                        tmp['day'] = current_data[0]
                        tmp['close'] = float(current_data[2])
                        tmp['high'] = float(current_data[3])
                        tmp['low'] = float(current_data[4])
                        if i > 0:
                            tmp['last_close'] = float(r[i - 1].split(',')[2])
                        data.append(tmp)
                    return data[1:]
        except Exception() as e:
            print(e)
            return None

    def get_benchmark(self):
        benchmark_data = self.get_stock_kline(code=self.benchmark, period=103, limit=18)
        self.benchmark_yield = round(
            (benchmark_data[-2]['close'] - benchmark_data[-13]['last_close']) / benchmark_data[-13]['last_close'] * 100,
            2)
        # print(self.benchmark_yield)

    def cumulative_run(self):
        data_week = self.get_stock_kline(period=102)
        if data_week:
            self.week52_highest = max([i['high'] for i in data_week[:-1]])
            self.current_price = data_week[-1]['close']
            self.momentum_value = round(self.current_price / self.week52_highest, 2)
        data_month = self.get_stock_kline(period=103, limit=18)
        if data_month:
            self.cumulative_yield = round(
                (data_month[-2]['close'] - data_month[-13]['last_close']) / data_month[-13]['last_close'] * 100, 2)
            self.excess_yield = round(self.cumulative_yield - self.benchmark_yield, 2)


import tushare
pro = tushare.pro_api("b625f0b90069039346d199aa3c0d5bc53fd47212437337b45ba87487")


class Stock_BaseInfo:
    def __init__(self):
        self.code = None
        self.name = None
        self.industry = None
        self.pe = None
        self.float_share = None
        self.total_share = None
        self.total_assets = None
        self.liquid_assets = None
        self.fixed_assets = None
        self.reserved = None
        self.reserved_pershare = None
        self.eps = None
        self.bvps = None
        self.pb = None
        self.list_date = None
        self.undp = None
        self.per_undp = None
        self.rev_yoy = None
        self.profit_yoy = None
        self.gpr = None
        self.npr = None
        self.holder_num = None

    def __str__(self):
        return f"代码:{self.code}\t名称:{self.name}\t行业:{self.industry}\tPE:{self.pe}\tPB:{self.pb}" \
               f"\t收入同比:{self.rev_yoy}\t利润同比:{self.profit_yoy}\t毛利率:{self.gpr}\t净利润率:{self.npr}" \
               f"\t流通股本:{self.float_share}(亿股)\t总股本:{self.total_share}(亿股)"

    @staticmethod
    def growth_run():
        data = pro.bak_basic(trade_date='20210721')
        tmp = []
        for i in data.values:
            s = Stock_BaseInfo()
            s.code = i[1].split('.')[0]
            s.name = i[2]
            s.industry = i[3]
            s.pe = float(i[5])
            s.pb = float(i[15])
            s.float_share = i[6]
            s.total_share = i[7]
            s.rev_yoy = float(i[-5])
            s.profit_yoy = float(i[-4])
            s.gpr = float(i[-3])
            s.npr = float(i[-2])
            tmp.append(s)
            if s.code.startswith('3') and s.rev_yoy > 80 and s.profit_yoy > 80:
                print(s)


for i in range(300001, 300500):
    m = Momentum(i)
    m.cumulative_run()
    if m.momentum_value and m.cumulative_yield and m.excess_yield:
        if m.momentum_value > 0.9 and m.excess_yield > 0:
            print(m)
