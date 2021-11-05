# ecoding: utf-8
import backtrader as bt
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import backtrader.analyzers as btanalyzers


class Ketler(bt.Indicator):
    params = dict(ema=20, atr=17)
    lines = ('expo', 'atr', 'upper', 'lower')
    plotinfo = dict(subplot=False)
    plotlines = dict(
        upper=dict(ls='--'),
        lower=dict(_samecolor=True)
    )

    def __init__(self):
        self.l.expo = bt.talib.EMA(
            self.datas[0].close,
            timeperiod=self.params.ema)
        self.l.atr = bt.talib.ATR(
            self.data.high,
            self.data.low,
            self.data.close,
            timeperiod=self.params.atr)
        self.l.upper = self.l.expo + self.l.atr
        self.l.lower = self.l.expo - self.l.atr


class Strategy(bt.Strategy):
    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        self.ketler = Ketler()
        self.close = self.data.close

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: {:.2f}, Cost: {:.2f}, Comm {:.2f}'.format(
                        order.executed.price,
                        order.executed.value,
                        order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log('SELL EXECUTED, Price: {:.2f}, Cost: {:.2f}, Comm {:.2f}'.format(
                    order.executed.price,
                    order.executed.value,
                    order.executed.comm))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        if not self.position:
            if self.close[0] > self.ketler.upper[0]:
                self.order = self.order_target_percent(target=0.95)
        else:
            if self.close[0] < self.ketler.expo[0]:
                self.order = self.sell()


if __name__ == '__main__':
    cerebro = bt.Cerebro()

    data = bt.feeds.YahooFinanceData(
        dataname='BILI',
        fromdate=datetime.datetime(2019, 1, 1),
        todate=datetime.datetime(2020, 12, 31),
        timeframe=bt.TimeFrame.Days
    )

    cerebro.adddata(data)

    cerebro.addstrategy(Strategy)
    cerebro.broker.setcash(1000000)
    cerebro.broker.setcommission(commission=0)
    cerebro.addsizer(bt.sizers.PercentSizer, percents=98)

    cerebro.addanalyzer(btanalyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(btanalyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(btanalyzers.Returns, _name='returns')

    print('Starte Portfolio Value {}'.format(cerebro.broker.getvalue()))
    back = cerebro.run()
    print('end portfolio value {}'.format(cerebro.broker.getvalue()))

    par_list = [[x.analyzers.returns.get_analysis()['rtot'],
                 x.analyzers.returns.get_analysis()['rnorm100'],
                 x.analyzers.drawdown.get_analysis()['max']['drawdown'],
                 x.analyzers.sharpe.get_analysis()['sharperatio']
                 ] for x in back]
    par_df = pd.DataFrame(
        par_list,
        columns=[
            'Total Return',
            'APR',
            'Drawdown',
            'SharpRatio'])
    print(par_df)

    cerebro.plot(style='candle')
