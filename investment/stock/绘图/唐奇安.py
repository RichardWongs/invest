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

# 设定上、下、中通道线初始值
upboundDC = pd.Series(0.0, index=Close.index)
downboundDC = pd.Series(0.0, index=Close.index)
midboundDC = pd.Series(0.0, index=Close.index)

# 求唐奇安上、中、下通道
for i in range(20, len(Close)):
    upboundDC[i] = max(High[(i-20):i])
    downboundDC[i] = min(Low[(i-20):i])
    midboundDC[i] = 0.5 * (upboundDC[i] + downboundDC[i])

upboundDC = upboundDC[20:]
downboundDC = downboundDC[20:]
midboundDC = midboundDC[20:]

# 绘制2020年洛阳钼业价格唐奇安通道上中下轨道线图
# plt.rcParams['font.sans-serif'] = ['SimHei']
# plt.plot(Close['2020'], label="Close", color="k")
# plt.plot(upboundDC['2020'], label="upboundDC", color="b", linestyle="dashed")
# plt.plot(midboundDC['2020'], label="midboundDC", color="r", linestyle="-.")
# plt.plot(downboundDC['2020'],label="downboundDC", color="b", linestyle="dashed")
# plt.title("2020年洛阳钼业股价唐奇安通道")
# plt.xlabel('日期')
# plt.ylabel('values')
# plt.grid(True)
# plt.legend()
# plt.show()

s = mpf.make_mpf_style(base_mpf_style='nightclouds', rc={'font.family': 'SimHei'})   # 解决mplfinance绘制输出中文乱码
add_plot = [
    mpf.make_addplot(upboundDC['2020']),
    mpf.make_addplot(midboundDC['2020']),
    mpf.make_addplot(downboundDC['2020'])]
mpf.plot(df['2020'], type='candle', style=s, title='洛阳钼业2020年K线图及唐奇安通道线', addplot=add_plot, volume=True)


# 首先，先定义向上突破和向下突破函数upbreak()和downbreak()
def upbreak(tsLine, tsRefLine):
    n = min(len(tsLine), len(tsRefLine))
    tsLine = tsLine[-n:]
    tsRefLine = tsRefLine[-n:]
    signal = pd.Series(0, index=tsLine.index)
    for i in range(1, len(tsLine)):
        if all([tsLine[i]>tsRefLine[i], tsLine[i-1]<tsRefLine[i-1]]):
            signal[i] = 1
    return(signal)


def downbreak(tsLine, tsRefLine):
    n = min(len(tsLine), len(tsRefLine))
    tsLine = tsLine[-n:]
    tsRefLine = tsRefLine[-n:]
    signal = pd.Series(0, index=tsLine.index)
    for i in range(1, len(tsLine)):
        if all([tsLine[i] < tsRefLine[i], tsLine[i-1] > tsRefLine[i-1]]):
            signal[i] = 1
    return(signal)


# 唐奇安通道突破策略
UpBreak = upbreak(Close[upboundDC.index[0]:], upboundDC)
DownBreak = downbreak(Close[downboundDC.index[0]:], downboundDC)

# 制定交易策略
# 上穿，signal为1
# 下穿，signal为-1
# 合并上下穿突破总信号
BreakSig = UpBreak - DownBreak
# 计算预测获胜率
tradeSig = BreakSig.shift(1)['2020']
ret = Close / Close.shift(1) - 1  # 这里的Close依然是全时间序列的
tradeRet = (ret * tradeSig).dropna()  # 一次乘法加dropna()之后，Close()多的时间序列就被过滤掉了。
winRate = len(tradeRet[tradeRet > 0]) / len(tradeRet[tradeRet != 0])
print(f"胜率:{round(winRate, 2)}")


# 在20到60的时间跨度中寻找该股票唐奇安通道突破策略胜率最大 的时间跨度
list1 = []
list2 = []
for m in range(20, 61):
    upboundDC = pd.Series(0.0, index=Close.index)
    downboundDC = pd.Series(0.0, index=Close.index)
    midboundDC = pd.Series(0.0, index=Close.index)
    # 求唐奇安上、下通道
    for i in range(m,len(Close)):
        upboundDC[i] = max(High[(i-m):i])
        downboundDC[i] = min(Low[(i-m):i])

    upboundDC = upboundDC[m:]
    downboundDC = downboundDC[m:]
    midboundDC = midboundDC[m:]

    # 唐奇安通道突破策略
    UpBreak = upbreak(Close[upboundDC.index[0]:], upboundDC)
    DownBreak = downbreak(Close[downboundDC.index[0]:], downboundDC)
    BreakSig = UpBreak - DownBreak
    # 计算预测获胜率
    tradeSig = BreakSig.shift(1)['2020']
    ret = Close / Close.shift(1) - 1  # 这里的Close依然是全时间序列的
    tradeRet = (ret * tradeSig).dropna()  # 一次乘法加dropna()之后，Close()多出的时间序列就被过滤掉了。
    winRate = len(tradeRet[tradeRet > 0]) / len(tradeRet[tradeRet != 0])
    list1.append(m)
    list2.append(winRate)
print('该股票2020年唐奇安道路突破策略时间跨度为m为{}时胜率最大为{}'.format(list1[list2.index(max(list2))], max(list2)))
