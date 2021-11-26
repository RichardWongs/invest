from fundresults import get_fund


def MA_V2(kline: list, N, key="close"):
    assert len(kline) > N
    for i in range(len(kline)):
        if i >= N:
            tmp = []
            for j in range(i, i - N, -1):
                tmp.append(kline[j][key])
            if key == "close":
                kline[i][f'ma{N}'] = round(sum(tmp) / len(tmp), 2)
            else:
                kline[i][f'ma_{key}_{N}'] = round(sum(tmp) / len(tmp), 2)
    return kline


data = get_fund("007192")
data = MA_V2(MA_V2(data, 10, key="unit_close"), 20, key="unit_close")
for i in data:
    print(i)


