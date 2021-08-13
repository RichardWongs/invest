from datetime import date, timedelta
import requests,json
import time


def get_style_index(index_code):
    # 国证指数K线数据
    url = f"http://hq.cnindex.com.cn/market/market/getIndexDailyDataWithDataFormat"
    begin_time = date.today() - timedelta(days=365)
    end_time = date.today()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36"
    }
    params = {
        "indexCode": index_code,
        "startDate": begin_time,
        "endDate": end_time,
        "frequency": "day"
    }
    response = requests.get(url,headers=headers, params=params).json()
    data = response.get("data").get("data")
    return list(reversed(data))

def RSI_DAY(data):
    rsi_day = 14
    up = [i if i > 0 else 0 for i in [i[6] for i in data[:14]]]
    down = [i * -1 if i < 0 else 0 for i in [i[6] for i in data[:14]]]
    smooth_up_14 = sum(up) / len(up)
    smooth_down_14 = sum(down) / len(down)
    new_data = []
    for i in range(len(data)):
        tmp_list = {}
        tmp_list["date"] = data[i][0]
        up_column = data[i][6] if data[i][6] > 0 else 0
        tmp_list["up_column"] = up_column
        down_column = data[i][6] * -1 if data[i][6] < 0 else 0
        tmp_list["down_column"] = down_column
        if i == 13:
            smooth_up = smooth_up_14
            smooth_down = smooth_down_14
        elif i > 13:
            smooth_up = (new_data[i - 1]["smooth_up"] * (rsi_day - 1) + up_column) / rsi_day
            smooth_down = (new_data[i - 1]["smooth_down"] * (rsi_day - 1) + down_column) / rsi_day
        else:
            smooth_up = smooth_down = None
        tmp_list["smooth_up"] = smooth_up
        tmp_list["smooth_down"] = smooth_down
        relative_intensity = smooth_up / smooth_down if (smooth_up is not None or smooth_down is not None) else None
        tmp_list["relative_intensity"] = relative_intensity
        if relative_intensity:
            tmp_list["RSI"] = round(100 - (100 / (1 + relative_intensity)), 2)
        new_data.append(tmp_list)
    return new_data

def RSI_HOURS(data):
    rsi_day = 14
    up = [i if i > 0 else 0 for i in [i["applies"] for i in data[:14]]]
    down = [i * -1 if i < 0 else 0 for i in [i["applies"] for i in data[:14]]]
    smooth_up_14 = sum(up) / len(up)
    smooth_down_14 = sum(down) / len(down)
    new_data = []
    for i in range(len(data)):
        tmp_list = {}
        tmp_list["date"] = data[i]["day"]
        up_column = data[i]["applies"] if data[i]["applies"] > 0 else 0
        tmp_list["up_column"] = up_column
        down_column = data[i]["applies"] * -1 if data[i]["applies"] < 0 else 0
        tmp_list["down_column"] = down_column
        if i == 13:
            smooth_up = smooth_up_14
            smooth_down = smooth_down_14
        elif i > 13:
            smooth_up = (new_data[i - 1]["smooth_up"] * (rsi_day - 1) + up_column) / rsi_day
            smooth_down = (new_data[i - 1]["smooth_down"] * (rsi_day - 1) + down_column) / rsi_day
        else:
            smooth_up = smooth_down = None
        tmp_list["smooth_up"] = smooth_up
        tmp_list["smooth_down"] = smooth_down
        relative_intensity = smooth_up / smooth_down if (smooth_up is not None or smooth_down is not None) else None
        tmp_list["relative_intensity"] = relative_intensity
        if relative_intensity:
            tmp_list["RSI"] = round(100 - (100 / (1 + relative_intensity)), 2)
        new_data.append(tmp_list)
    return new_data

def get_hour_k_line_info(code):
    timestamp = int(time.time()*1000)
    url = f"https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_sz{code}_60_{timestamp}=/CN_MarketDataService.getKLineData"
    params = {
        "symbol": f"sz{code}",
        "scale": 60,
        "ma": "no",
        "datalen": 180
    }
    response = requests.get(url, params=params)
    content = response.text.split("=(")[1].split(");")[0]
    content = json.loads(content)
    for i in range(len(content)):
        del content[i]["volume"]
        del content[i]["open"]
        del content[i]["high"]
        del content[i]["low"]
        if i>0:
            content[i]["applies"] = round(float(content[i]["close"])-float(content[i-1]["close"]), 3)
    del content[0]
    return content



get_hour_k_line_info(399296)
# data = [{'day': '2021-05-25 14:00:00', 'close': '7386.964', 'applies': 0}, {'day': '2021-05-25 15:00:00', 'close': '7398.989', 'applies': 12.025}, {'day': '2021-05-26 10:30:00', 'close': '7350.742', 'applies': -48.247}, {'day': '2021-05-26 11:30:00', 'close': '7316.375', 'applies': -34.367}, {'day': '2021-05-26 14:00:00', 'close': '7352.579', 'applies': 36.204}, {'day': '2021-05-26 15:00:00', 'close': '7328.462', 'applies': -24.117}, {'day': '2021-05-27 10:30:00', 'close': '7373.673', 'applies': 45.211}, {'day': '2021-05-27 11:30:00', 'close': '7388.120', 'applies': 14.447}, {'day': '2021-05-27 14:00:00', 'close': '7392.209', 'applies': 4.089}, {'day': '2021-05-27 15:00:00', 'close': '7430.839', 'applies': 38.63}, {'day': '2021-05-28 10:30:00', 'close': '7522.400', 'applies': 91.561}, {'day': '2021-05-28 11:30:00', 'close': '7509.831', 'applies': -12.569}, {'day': '2021-05-28 14:00:00', 'close': '7407.477', 'applies': -102.354}, {'day': '2021-05-28 15:00:00', 'close': '7410.861', 'applies': 3.384}, {'day': '2021-05-31 10:30:00', 'close': '7552.790', 'applies': 141.929}, {'day': '2021-05-31 11:30:00', 'close': '7496.321', 'applies': -56.469}, {'day': '2021-05-31 14:00:00', 'close': '7570.350', 'applies': 74.029}, {'day': '2021-05-31 15:00:00', 'close': '7589.044', 'applies': 18.694}, {'day': '2021-06-01 10:30:00', 'close': '7434.013', 'applies': -155.031}, {'day': '2021-06-01 11:30:00', 'close': '7584.690', 'applies': 150.677}, {'day': '2021-06-01 14:00:00', 'close': '7590.246', 'applies': 5.556}, {'day': '2021-06-01 15:00:00', 'close': '7590.623', 'applies': 0.377}, {'day': '2021-06-02 10:30:00', 'close': '7495.611', 'applies': -95.012}, {'day': '2021-06-02 11:30:00', 'close': '7429.817', 'applies': -65.794}, {'day': '2021-06-02 14:00:00', 'close': '7400.069', 'applies': -29.748}, {'day': '2021-06-02 15:00:00', 'close': '7409.844', 'applies': 9.775}, {'day': '2021-06-03 10:30:00', 'close': '7351.882', 'applies': -57.962}, {'day': '2021-06-03 11:30:00', 'close': '7416.469', 'applies': 64.587}, {'day': '2021-06-03 14:00:00', 'close': '7359.731', 'applies': -56.738}, {'day': '2021-06-03 15:00:00', 'close': '7316.514', 'applies': -43.217}]
# new_data = RSI_HOURS(data)
# for i in new_data:
#     if "RSI" in i.keys():
#         print(i["date"], i["RSI"])
