from . import *


df = pro.daily(ts_code='603993.SH')  # daily为tushare的股票数据接口。

# 将获取到的DataFrame数据进行标准化处理，转换为方便自己使用的一种规范格式。
df = df.loc[:, ['trade_date', 'open', 'high', 'low', 'close', 'vol']]
df.rename(
    columns={
        'trade_date': 'Date', 'open': 'Open',
        'high': 'High', 'low': 'Low',
        'close': 'Close', 'vol': 'Volume'},
    inplace=True)       # 重定义列名，方便统一规范操作。
df['Date'] = pd.to_datetime(df['Date'])  # 转换日期列的格式，便于作图
df.set_index(['Date'], inplace=True)  # 将日期列作为行索引
df = df.sort_index()  # 倒序，因为Tushare的数据是最近的交易日数据显示在DataFrame上方，倒序后方能保证作图时X轴从左到右时间序列递增。

# 提取收盘价，最高价，最低价数据
Close = df.Close
High = df.High
Low = df.Low


# 定义布林带通道函数bbands()
def bbands(tsPrice, period=20, times=2):
    upBBand = pd.Series(0.0, index=tsPrice.index)
    midBBand = pd.Series(0.0, index=tsPrice.index)
    downBBand = pd.Series(0.0, index=tsPrice.index)
    sigma = pd.Series(0.0, index=tsPrice.index)
    for i in range(period - 1, len(tsPrice)):
        midBBand[i] = np.nanmean(
            tsPrice[i - (period - 1):(i + 1)])   # nanmean忽略Nan计算均值
        # nanstd忽略Nan计算标准差
        sigma[i] = np.nanstd(tsPrice[i - (period - 1):(i + 1)])
        upBBand[i] = midBBand[i] + times * sigma[i]
        downBBand[i] = midBBand[i] - times * sigma[i]
    BBands = pd.DataFrame({'upBBand': upBBand[(period - 1):],
                           'midBBand': midBBand[(period - 1):],
                           'downBBand': downBBand[(period - 1):],
                           'sigma': sigma[(period - 1):]})
    return(BBands)


# 计算20日布林带通道线
LymyBBands = bbands(Close, 20, 2)
# 提取数据
UpBBands = LymyBBands.upBBand['2020']
DownBBands = LymyBBands.downBBand['2020']
MidBBands = LymyBBands.midBBand['2020']

s = mpf.make_mpf_style(
    base_mpf_style='nightclouds', rc={
        'font.family': 'SimHei'})
add_plot = [
    mpf.make_addplot(UpBBands),
    mpf.make_addplot(DownBBands),
    mpf.make_addplot(MidBBands)]
mpf.plot(
    df['2020'],
    type='candle',
    style=s,
    title="洛阳钼业2020年K线图及布林带通道线",
    addplot=add_plot,
    volume=True)


# 构建布林带风险函数
def CalBollRisk(tsPrice, multiplier):
    k = len(multiplier)
    overUp = []
    belowDown = []
    BollRisk = []
    for i in range(k):
        BBands = bbands(tsPrice, 20, multiplier[i])
        a = 0
        b = 0
        for j in range(len(BBands)):
            tsPrice = tsPrice[-(len(BBands)):]
            if tsPrice[j] > BBands.upBBand[j]:
                a += 1
            elif tsPrice[j] < BBands.downBBand[j]:
                b += 1
        overUp.append(a)
        belowDown.append(b)
        BollRisk.append(100 * (a + b) / len(tsPrice))
    return BollRisk
