# encoding: utf-8
# 动量模型核心教程  资料来源: 简放
import json
import os
import time
import logging
from datetime import date, timedelta
import numpy as np
import pandas as pd
import tushare as ts
from RPS.stock_pool import NEW_STOCK_LIST
pro = ts.pro_api("b625f0b90069039346d199aa3c0d5bc53fd47212437337b45ba87487")
begin_date = int(str(date.today() - timedelta(days=31)).replace('-', ''))
today = int(str(date.today()).replace('-', ''))
day = 180   # 上市时间满半年
rps_day = 20
quarter = 3


def get_stock_list():
    # 获取沪深股市股票列表, 剔除上市不满半年的次新股
    df = pro.stock_basic(exchange='', list_status='L',
                         fields='ts_code,symbol,name,industry,list_date')  # fields='ts_code,symbol,name,area,industry,'
    df = df[df['list_date'].apply(int).values < int(str(date.today() - timedelta(days=20)).replace('-', ''))]
    # 获取当前所有非新股次新股代码和名称
    codes = df.ts_code.values
    names = df.name.values
    industrys = df.industry.values
    list_dates = df.list_date.values
    stock_list = []
    for code, name, industry, list_date in zip(codes, names, industrys, list_dates):
        tmp = {'code': code, 'name': name, 'industry': industry, 'list_date': list_date}
        stock_list.append(tmp)
    return stock_list


def get_data(code, start=begin_date, end=today):
    # 按照日期范围获取股票交易日期,收盘价
    time.sleep(0.1)
    df = pro.daily(ts_code=code, start_date=start, end_date=end, fields='trade_date,close')
    # 将交易日期设置为索引值
    df.index = pd.to_datetime(df.trade_date)
    df = df.sort_index()
    return df.close


def get_all_data(stock_list):
    # 构建一个空的 dataframe 用来装数据, 获取列表中所有股票指定范围内的收盘价格
    data = pd.DataFrame()
    count = 0
    filename = f'daily_price.csv'
    if filename in os.listdir(os.curdir):
        os.remove(filename)
    for i in stock_list:
        code = i.get('code')
        data[code] = get_data(code)
        print(code, i.get('name'), count)
        count += 1
    data.to_csv(filename, encoding='utf-8')


# 计算收益率
def cal_ret(df, w=5):
    # w:周5;月20;半年：120; 一年250
    df = df / df.shift(w) - 1
    return df.iloc[w:, :].fillna(0)


# 计算RPS
def get_RPS(ser):
    df = pd.DataFrame(ser.sort_values(ascending=False))
    df['n'] = range(1, len(df) + 1)
    df['rps'] = (1 - df['n'] / len(df)) * 100
    return df


# 计算每个交易日所有股票滚动w日的RPS
def all_RPS(data):
    dates = data.index
    # dates = (data.index).strftime('%Y%m%d')
    RPS = {}
    for i in range(len(data)):
        RPS[dates[i]] = pd.DataFrame(get_RPS(data.iloc[i]).values, columns=['收益率', '排名', 'RPS'],
                                     index=get_RPS(data.iloc[i]).index)
    return RPS


# 获取所有股票在某个期间的RPS值
def all_data(rps, ret):
    df = pd.DataFrame(np.NaN, columns=ret.columns, index=ret.index)
    for date in ret.index:
        date = date.strftime('%Y%m%d')
        d = rps[date]
        for c in d.index:
            df.loc[date, c] = d.loc[c, 'RPS']
    return df


def fill_in_data(df, filename="RPS.csv"):
    rps_df = pd.DataFrame()
    if filename in os.listdir(os.curdir):
        os.remove(filename)
    for k, v in df.items():
        print(k)
        for code, rps in zip(v.index, v.values):
            rps_df.loc[code, 'NAME'] = NEW_STOCK_LIST[code]['name']
            rps_df.loc[code, 'INDUSTRY'] = NEW_STOCK_LIST[code]['industry']
            rps_df.loc[code, 'LIST_DATE'] = NEW_STOCK_LIST[code]['list_date']
            rps_df.loc[code, k] = round(float(rps[-1]), 2)
    rps_df.to_csv(filename, encoding='utf-8')


def create_RPS_file():
    # stocks = get_stock_list()  # 获取全市场股票列表
    # get_all_data(stocks)  # 获取行情数据并写入csv文件
    data = pd.read_csv(f'daily_price.csv', encoding='utf-8', index_col='trade_date')
    data.index = pd.to_datetime(data.index, format='%Y%m%d', errors='ignore')
    ret = cal_ret(data, w=rps_day)
    rps = all_RPS(ret)
    fill_in_data(rps, filename=f'RPS{rps_day}.csv')  # 计算个股20日RPS值并写入rps文件


def eliminate_new_stock():
    # 剔除次新股
    df = pd.read_csv(f"RPS{rps_day}.csv", encoding='utf-8')
    pool = []
    for i in df.values:
        if i[-1] > 87 and i[3] < begin_date:
            pool.append({'code': i[0].split('.')[0], 'name': i[1]})
    logging.warning(f"RPS强度大于87,上市时间不小于半年股池数量:{len(pool)}")
    return pool


def get_fund_holdings(quarter, year=date.today().year):
    # 基金持股
    logging.warning("查询基金持股数据")
    return [{'code': '836239', 'name': '长虹能源'}, {'code': '835368', 'name': '连城数控'}, {'code': '835185', 'name': '贝特瑞'}, {'code': '833994', 'name': '翰博高新'}, {'code': '831961', 'name': '创远仪器'}, {'code': '831370', 'name': '新安洁'}, {'code': '831370', 'name': '新安洁'}, {'code': '830799', 'name': '艾融软件'}, {'code': '830799', 'name': '艾融软件'}, {'code': '688981', 'name': '中芯国际'}, {'code': '688700', 'name': '东威科技'}, {'code': '688699', 'name': '明微电子'}, {'code': '688696', 'name': '极米科技'}, {'code': '688682', 'name': '霍莱沃'}, {'code': '688680', 'name': '海优新材'}, {'code': '688677', 'name': '海泰新光'}, {'code': '688665', 'name': '四方光电'}, {'code': '688661', 'name': '和林微纳'}, {'code': '688639', 'name': '华恒生物'}, {'code': '688636', 'name': '智明达'}, {'code': '688626', 'name': '翔宇医疗'}, {'code': '688621', 'name': '阳光诺和'}, {'code': '688617', 'name': '惠泰医疗'}, {'code': '688608', 'name': '恒玄科技'}, {'code': '688607', 'name': '康众医疗'}, {'code': '688601', 'name': '力芯微'}, {'code': '688599', 'name': '天合光能'}, {'code': '688598', 'name': '金博股份'}, {'code': '688595', 'name': '芯海科技'}, {'code': '688580', 'name': '伟思医疗'}, {'code': '688556', 'name': '高测股份'}, {'code': '688551', 'name': '科威尔'}, {'code': '688536', 'name': '思瑞浦'}, {'code': '688521', 'name': '芯原股份'}, {'code': '688519', 'name': '南亚新材'}, {'code': '688518', 'name': '联赢激光'}, {'code': '688516', 'name': '奥特维'}, {'code': '688510', 'name': '航亚科技'}, {'code': '688508', 'name': '芯朋微'}, {'code': '688499', 'name': '利元亨'}, {'code': '688408', 'name': '中信博'}, {'code': '688390', 'name': '固德威'}, {'code': '688389', 'name': '普门科技'}, {'code': '688388', 'name': '嘉元科技'}, {'code': '688383', 'name': '新益昌'}, {'code': '688369', 'name': '致远互联'}, {'code': '688368', 'name': '晶丰明源'}, {'code': '688367', 'name': '工大高科'}, {'code': '688363', 'name': '华熙生物'}, {'code': '688359', 'name': '三孚新科'}, {'code': '688358', 'name': '祥生医疗'}, {'code': '688357', 'name': '建龙微纳'}, {'code': '688356', 'name': '键凯科技'}, {'code': '688339', 'name': '亿华通'}, {'code': '688310', 'name': '迈得医疗'}, {'code': '688301', 'name': '奕瑞科技'}, {'code': '688299', 'name': '长阳科技'}, {'code': '688276', 'name': '百克生物'}, {'code': '688268', 'name': '华特气体'}, {'code': '688208', 'name': '道通科技'}, {'code': '688202', 'name': '美迪西'}, {'code': '688200', 'name': '华峰测控'}, {'code': '688198', 'name': '佰仁医疗'}, {'code': '688188', 'name': '柏楚电子'}, {'code': '688186', 'name': '广大特材'}, {'code': '688169', 'name': '石头科技'}, {'code': '688158', 'name': '优刻得'}, {'code': '688157', 'name': '松井股份'}, {'code': '688155', 'name': '先惠技术'}, {'code': '688139', 'name': '海尔生物'}, {'code': '688131', 'name': '皓元医药'}, {'code': '688126', 'name': '沪硅产业'}, {'code': '688122', 'name': '西部超导'}, {'code': '688116', 'name': '天奈科技'}, {'code': '688111', 'name': '金山办公'}, {'code': '688106', 'name': '金宏气体'}, {'code': '688100', 'name': '威胜信息'}, {'code': '688099', 'name': '晶晨股份'}, {'code': '688093', 'name': '世华科技'}, {'code': '688089', 'name': '嘉必优'}, {'code': '688083', 'name': '中望软件'}, {'code': '688078', 'name': '龙软科技'}, {'code': '688076', 'name': '诺泰生物'}, {'code': '688066', 'name': '航天宏图'}, {'code': '688059', 'name': '华锐精密'}, {'code': '688058', 'name': '宝兰德'}, {'code': '688056', 'name': '莱伯泰科'}, {'code': '688050', 'name': '爱博医疗'}, {'code': '688037', 'name': '芯源微'}, {'code': '688036', 'name': '传音控股'}, {'code': '688033', 'name': '天宜上佳'}, {'code': '688029', 'name': '南微医学'}, {'code': '688026', 'name': '洁特生物'}, {'code': '688023', 'name': '安恒信息'}, {'code': '688021', 'name': '奥福环保'}, {'code': '688020', 'name': '方邦股份'}, {'code': '688019', 'name': '安集科技'}, {'code': '688018', 'name': '乐鑫科技'}, {'code': '688016', 'name': '心脉医疗'}, {'code': '688015', 'name': '交控科技'}, {'code': '688012', 'name': '中微公司'}, {'code': '688008', 'name': '澜起科技'}, {'code': '688006', 'name': '杭可科技'}, {'code': '688005', 'name': '容百科技'}, {'code': '688002', 'name': '睿创微纳'}, {'code': '605499', 'name': '东鹏饮料'}, {'code': '605369', 'name': '拱东医疗'}, {'code': '605358', 'name': '立昂微'}, {'code': '605338', 'name': '巴比食品'}, {'code': '605305', 'name': '中际联合'}, {'code': '605288', 'name': '凯迪股份'}, {'code': '605277', 'name': '新亚电子'}, {'code': '605266', 'name': '健之佳'}, {'code': '605186', 'name': '健麾信息'}, {'code': '605117', 'name': '德业股份'}, {'code': '605080', 'name': '浙江自然'}, {'code': '605066', 'name': '天正电气'}, {'code': '603997', 'name': '继峰股份'}, {'code': '603995', 'name': '甬金股份'}, {'code': '603993', 'name': '洛阳钼业'}, {'code': '603992', 'name': '松霖科技'}, {'code': '603989', 'name': '艾华集团'}, {'code': '603987', 'name': '康德莱'}, {'code': '603986', 'name': '兆易创新'}, {'code': '603970', 'name': '中农立华'}, {'code': '603960', 'name': '克来机电'}, {'code': '603938', 'name': '三孚股份'}, {'code': '603915', 'name': '国茂股份'}, {'code': '603909', 'name': '合诚股份'}, {'code': '603906', 'name': '龙蟠科技'}, {'code': '603901', 'name': '永创智能'}, {'code': '603899', 'name': '晨光文具'}, {'code': '603897', 'name': '长城科技'}, {'code': '603896', 'name': '寿仙谷'}, {'code': '603893', 'name': '瑞芯微'}, {'code': '603885', 'name': '吉祥航空'}, {'code': '603883', 'name': '老百姓'}, {'code': '603882', 'name': '金域医学'}, {'code': '603877', 'name': '太平鸟'}, {'code': '603855', 'name': '华荣股份'}, {'code': '603833', 'name': '欧派家居'}, {'code': '603816', 'name': '顾家家居'}, {'code': '603806', 'name': '福斯特'}, {'code': '603799', 'name': '华友钴业'}, {'code': '603738', 'name': '泰晶科技'}, {'code': '603733', 'name': '仙鹤股份'}, {'code': '603727', 'name': '博迈科'}, {'code': '603713', 'name': '密尔克卫'}, {'code': '603712', 'name': '七一二'}, {'code': '603708', 'name': '家家悦'}, {'code': '603707', 'name': '健友股份'}, {'code': '603699', 'name': '纽威股份'}, {'code': '603690', 'name': '至纯科技'}, {'code': '603688', 'name': '石英股份'}, {'code': '603681', 'name': '永冠新材'}, {'code': '603678', 'name': '火炬电子'}, {'code': '603667', 'name': '五洲新春'}, {'code': '603666', 'name': '亿嘉和'}, {'code': '603662', 'name': '柯力传感'}, {'code': '603659', 'name': '璞泰来'}, {'code': '603639', 'name': '海利尔'}, {'code': '603613', 'name': '国联股份'}, {'code': '603612', 'name': '索通发展'}, {'code': '603605', 'name': '珀莱雅'}, {'code': '603601', 'name': '再升科技'}, {'code': '603600', 'name': '永艺股份'}, {'code': '603599', 'name': '广信股份'}, {'code': '603596', 'name': '伯特利'}, {'code': '603588', 'name': '高能环境'}, {'code': '603587', 'name': '地素时尚'}, {'code': '603565', 'name': '中谷物流'}, {'code': '603558', 'name': '健盛集团'}, {'code': '603538', 'name': '美诺华'}, {'code': '603529', 'name': '爱玛科技'}, {'code': '603518', 'name': '锦泓集团'}, {'code': '603517', 'name': '绝味食品'}, {'code': '603501', 'name': '韦尔股份'}, {'code': '603486', 'name': '科沃斯'}, {'code': '603456', 'name': '九洲药业'}, {'code': '603444', 'name': '吉比特'}, {'code': '603429', 'name': '集友股份'}, {'code': '603392', 'name': '万泰生物'}, {'code': '603369', 'name': '今世缘'}, {'code': '603368', 'name': '柳药股份'}, {'code': '603348', 'name': '文灿股份'}, {'code': '603345', 'name': '安井食品'}, {'code': '603338', 'name': '浙江鼎力'}, {'code': '603337', 'name': '杰克股份'}, {'code': '603323', 'name': '苏农银行'}, {'code': '603308', 'name': '应流股份'}, {'code': '603290', 'name': '斯达半导'}, {'code': '603279', 'name': '景津环保'}, {'code': '603267', 'name': '鸿远电子'}, {'code': '603260', 'name': '合盛硅业'}, {'code': '603259', 'name': '药明康德'}, {'code': '603236', 'name': '移远通信'}, {'code': '603225', 'name': '新凤鸣'}, {'code': '603218', 'name': '日月股份'}, {'code': '603208', 'name': '江山欧派'}, {'code': '603198', 'name': '迎驾贡酒'}, {'code': '603195', 'name': '公牛集团'}, {'code': '603189', 'name': '网达软件'}, {'code': '603187', 'name': '海容冷链'}, {'code': '603185', 'name': '上机数控'}, {'code': '603181', 'name': '皇马科技'}, {'code': '603180', 'name': '金牌厨柜'}, {'code': '603179', 'name': '新泉股份'}, {'code': '603158', 'name': '腾龙股份'}, {'code': '603131', 'name': '上海沪工'}, {'code': '603129', 'name': '春风动力'}, {'code': '603128', 'name': '华贸物流'}, {'code': '603127', 'name': '昭衍新药'}, {'code': '603113', 'name': '金能科技'}, {'code': '603108', 'name': '润达医疗'}, {'code': '603105', 'name': '芯能科技'}, {'code': '603098', 'name': '森特股份'}, {'code': '603096', 'name': '新经典'}, {'code': '603068', 'name': '博通集成'}, {'code': '603067', 'name': '振华股份'}, {'code': '603063', 'name': '禾望电气'}, {'code': '603055', 'name': '台华新材'}, {'code': '603026', 'name': '石大胜华'}, {'code': '603018', 'name': '华设集团'}, {'code': '603008', 'name': '喜临门'}, {'code': '601968', 'name': '宝钢包装'}, {'code': '601966', 'name': '玲珑轮胎'}, {'code': '601939', 'name': '建设银行'}, {'code': '601928', 'name': '凤凰传媒'}, {'code': '601899', 'name': '紫金矿业'}, {'code': '601898', 'name': '中煤能源'}, {'code': '601888', 'name': '中国中免'}, {'code': '601877', 'name': '正泰电器'}, {'code': '601865', 'name': '福莱特'}, {'code': '601838', 'name': '成都银行'}, {'code': '601799', 'name': '星宇股份'}, {'code': '601778', 'name': '晶科科技'}, {'code': '601702', 'name': '华峰铝业'}, {'code': '601699', 'name': '潞安环能'}, {'code': '601689', 'name': '拓普集团'}, {'code': '601688', 'name': '华泰证券'}, {'code': '601678', 'name': '滨化股份'}, {'code': '601677', 'name': '明泰铝业'}, {'code': '601669', 'name': '中国电建'}, {'code': '601668', 'name': '中国建筑'}, {'code': '601666', 'name': '平煤股份'}, {'code': '601658', 'name': '邮储银行'}, {'code': '601636', 'name': '旗滨集团'}, {'code': '601633', 'name': '长城汽车'}, {'code': '601615', 'name': '明阳智能'}, {'code': '601601', 'name': '中国太保'}, {'code': '601600', 'name': '中国铝业'}, {'code': '601598', 'name': '中国外运'}, {'code': '601567', 'name': '三星医疗'}, {'code': '601528', 'name': '瑞丰银行'}, {'code': '601377', 'name': '兴业证券'}, {'code': '601369', 'name': '陕鼓动力'}, {'code': '601318', 'name': '中国平安'}, {'code': '601233', 'name': '桐昆股份'}, {'code': '601225', 'name': '陕西煤业'}, {'code': '601222', 'name': '林洋能源'}, {'code': '601211', 'name': '国泰君安'}, {'code': '601208', 'name': '东材科技'}, {'code': '601166', 'name': '兴业银行'}, {'code': '601128', 'name': '常熟银行'}, {'code': '601127', 'name': '小康股份'}, {'code': '601117', 'name': '中国化学'}, {'code': '601111', 'name': '中国国航'}, {'code': '601101', 'name': '昊华能源'}, {'code': '601100', 'name': '恒立液压'}, {'code': '601098', 'name': '中南传媒'}, {'code': '601069', 'name': '西部黄金'}, {'code': '601058', 'name': '赛轮轮胎'}, {'code': '601021', 'name': '春秋航空'}, {'code': '601012', 'name': '隆基股份'}, {'code': '601009', 'name': '南京银行'}, {'code': '601003', 'name': '柳钢股份'}, {'code': '601001', 'name': '晋控煤业'}, {'code': '600999', 'name': '招商证券'}, {'code': '600988', 'name': '赤峰黄金'}, {'code': '600987', 'name': '航民股份'}, {'code': '600985', 'name': '淮北矿业'}, {'code': '600984', 'name': '建设机械'}, {'code': '600971', 'name': '恒源煤电'}, {'code': '600970', 'name': '中材国际'}, {'code': '600967', 'name': '内蒙一机'}, {'code': '600966', 'name': '博汇纸业'}, {'code': '600958', 'name': '东方证券'}, {'code': '600926', 'name': '杭州银行'}, {'code': '600919', 'name': '江苏银行'}, {'code': '600905', 'name': '三峡能源'}, {'code': '600900', 'name': '长江电力'}, {'code': '600893', 'name': '航发动力'}, {'code': '600888', 'name': '新疆众和'}, {'code': '600887', 'name': '伊利股份'}, {'code': '600885', 'name': '宏发股份'}, {'code': '600884', 'name': '杉杉股份'}, {'code': '600882', 'name': '妙可蓝多'}, {'code': '600875', 'name': '东方电气'}, {'code': '600862', 'name': '中航高科'}, {'code': '600848', 'name': '上海临港'}, {'code': '600845', 'name': '宝信软件'}, {'code': '600837', 'name': '海通证券'}, {'code': '600809', 'name': '山西汾酒'}, {'code': '600808', 'name': '马钢股份'}, {'code': '600803', 'name': '新奥股份'}, {'code': '600801', 'name': '华新水泥'}, {'code': '600782', 'name': '新钢股份'}, {'code': '600779', 'name': '水井坊'}, {'code': '600765', 'name': '中航重机'}, {'code': '600763', 'name': '通策医疗'}, {'code': '600760', 'name': '中航沈飞'}, {'code': '600754', 'name': '锦江酒店'}, {'code': '600745', 'name': '闻泰科技'}, {'code': '600741', 'name': '华域汽车'}, {'code': '600711', 'name': '盛屯矿业'}, {'code': '600703', 'name': '三安光电'}, {'code': '600702', 'name': '舍得酒业'}, {'code': '600690', 'name': '海尔智家'}, {'code': '600674', 'name': '川投能源'}, {'code': '600660', 'name': '福耀玻璃'}, {'code': '600641', 'name': '万业企业'}, {'code': '600612', 'name': '老凤祥'}, {'code': '600600', 'name': '青岛啤酒'}, {'code': '600596', 'name': '新安股份'}, {'code': '600588', 'name': '用友网络'}, {'code': '600581', 'name': '八一钢铁'}, {'code': '600577', 'name': '精达股份'}, {'code': '600570', 'name': '恒生电子'}, {'code': '600563', 'name': '法拉电子'}, {'code': '600546', 'name': '山煤国际'}, {'code': '600529', 'name': '山东药玻'}, {'code': '600521', 'name': '华海药业'}, {'code': '600519', 'name': '贵州茅台'}, {'code': '600507', 'name': '方大特钢'}, {'code': '600499', 'name': '科达制造'}, {'code': '600487', 'name': '亨通光电'}, {'code': '600486', 'name': '扬农化工'}, {'code': '600460', 'name': '士兰微'}, {'code': '600459', 'name': '贵研铂业'}, {'code': '600455', 'name': '博通股份'}, {'code': '600438', 'name': '通威股份'}, {'code': '600436', 'name': '片仔癀'}, {'code': '600435', 'name': '北方导航'}, {'code': '600426', 'name': '华鲁恒升'}, {'code': '600418', 'name': '江淮汽车'}, {'code': '600416', 'name': '湘电股份'}, {'code': '600399', 'name': '抚顺特钢'}, {'code': '600398', 'name': '海澜之家'}, {'code': '600395', 'name': '盘江股份'}, {'code': '600391', 'name': '航发科技'}, {'code': '600383', 'name': '金地集团'}, {'code': '600372', 'name': '中航电子'}, {'code': '600350', 'name': '山东高速'}, {'code': '600348', 'name': '华阳股份'}, {'code': '600346', 'name': '恒力石化'}, {'code': '600338', 'name': '西藏珠峰'}, {'code': '600328', 'name': '中盐化工'}, {'code': '600327', 'name': '大东方'}, {'code': '600323', 'name': '瀚蓝环境'}, {'code': '600316', 'name': '洪都航空'}, {'code': '600315', 'name': '上海家化'}, {'code': '600309', 'name': '万华化学'}, {'code': '600298', 'name': '安琪酵母'}, {'code': '600297', 'name': '广汇汽车'}, {'code': '600295', 'name': '鄂尔多斯'}, {'code': '600285', 'name': '羚锐制药'}, {'code': '600282', 'name': '南钢股份'}, {'code': '600276', 'name': '恒瑞医药'}, {'code': '600258', 'name': '首旅酒店'}, {'code': '600256', 'name': '广汇能源'}, {'code': '600248', 'name': '陕西建工'}, {'code': '600219', 'name': '南山铝业'}, {'code': '600216', 'name': '浙江医药'}, {'code': '600210', 'name': '紫江企业'}, {'code': '600202', 'name': '哈空调'}, {'code': '600201', 'name': '生物股份'}, {'code': '600195', 'name': '中牧股份'}, {'code': '600188', 'name': '兖州煤业'}, {'code': '600183', 'name': '生益科技'}, {'code': '600176', 'name': '中国巨石'}, {'code': '600172', 'name': '黄河旋风'}, {'code': '600171', 'name': '上海贝岭'}, {'code': '600153', 'name': '建发股份'}, {'code': '600150', 'name': '中国船舶'}, {'code': '600141', 'name': '兴发集团'}, {'code': '600138', 'name': '中青旅'}, {'code': '600132', 'name': '重庆啤酒'}, {'code': '600131', 'name': '国网信通'}, {'code': '600123', 'name': '兰花科创'}, {'code': '600115', 'name': '中国东航'}, {'code': '600111', 'name': '北方稀土'}, {'code': '600110', 'name': '诺德股份'}, {'code': '600096', 'name': '云天化'}, {'code': '600089', 'name': '特变电工'}, {'code': '600079', 'name': '人福医药'}, {'code': '600075', 'name': '新疆天业'}, {'code': '600073', 'name': '上海梅林'}, {'code': '600060', 'name': '海信视像'}, {'code': '600048', 'name': '保利发展'}, {'code': '600038', 'name': '中直股份'}, {'code': '600036', 'name': '招商银行'}, {'code': '600031', 'name': '三一重工'}, {'code': '600030', 'name': '中信证券'}, {'code': '600029', 'name': '南方航空'}, {'code': '600026', 'name': '中远海能'}, {'code': '600011', 'name': '华能国际'}, {'code': '600009', 'name': '上海机场'}, {'code': '430047', 'name': '诺思兰德'}, {'code': '430047', 'name': '诺思兰德'}, {'code': '301002', 'name': '崧盛股份'}, {'code': '300986', 'name': '志特新材'}, {'code': '300979', 'name': '华利集团'}, {'code': '300977', 'name': '深圳瑞捷'}, {'code': '300973', 'name': '立高食品'}, {'code': '300957', 'name': '贝泰妮'}, {'code': '300917', 'name': '特发服务'}, {'code': '300911', 'name': '亿田智能'}, {'code': '300896', 'name': '爱美客'}, {'code': '300894', 'name': '火星人'}, {'code': '300887', 'name': '谱尼测试'}, {'code': '300873', 'name': '海晨股份'}, {'code': '300871', 'name': '回盛生物'}, {'code': '300870', 'name': '欧陆通'}, {'code': '300866', 'name': '安克创新'}, {'code': '300861', 'name': '美畅股份'}, {'code': '300857', 'name': '协创数据'}, {'code': '300855', 'name': '图南股份'}, {'code': '300850', 'name': '新强联'}, {'code': '300833', 'name': '浩洋股份'}, {'code': '300829', 'name': '金丹科技'}, {'code': '300825', 'name': '阿尔特'}, {'code': '300816', 'name': '艾可蓝'}, {'code': '300815', 'name': '玉禾田'}, {'code': '300813', 'name': '泰林生物'}, {'code': '300811', 'name': '铂科新材'}, {'code': '300806', 'name': '斯迪克'}, {'code': '300802', 'name': '矩子科技'}, {'code': '300799', 'name': '左江科技'}, {'code': '300792', 'name': '壹网壹创'}, {'code': '300790', 'name': '宇瞳光学'}, {'code': '300788', 'name': '中信出版'}, {'code': '300782', 'name': '卓胜微'}, {'code': '300777', 'name': '中简科技'}, {'code': '300776', 'name': '帝尔激光'}, {'code': '300775', 'name': '三角防务'}, {'code': '300772', 'name': '运达股份'}, {'code': '300769', 'name': '德方纳米'}, {'code': '300767', 'name': '震安科技'}, {'code': '300763', 'name': '锦浪科技'}, {'code': '300762', 'name': '上海瀚讯'}, {'code': '300760', 'name': '迈瑞医疗'}, {'code': '300759', 'name': '康龙化成'}, {'code': '300751', 'name': '迈为股份'}, {'code': '300750', 'name': '宁德时代'}, {'code': '300747', 'name': '锐科激光'}, {'code': '300733', 'name': '西菱动力'}, {'code': '300726', 'name': '宏达电子'}, {'code': '300725', 'name': '药石科技'}, {'code': '300724', 'name': '捷佳伟创'}, {'code': '300702', 'name': '天宇股份'}, {'code': '300699', 'name': '光威复材'}, {'code': '300696', 'name': '爱乐达'}, {'code': '300687', 'name': '赛意信息'}, {'code': '300685', 'name': '艾德生物'}, {'code': '300682', 'name': '朗新科技'}, {'code': '300681', 'name': '英搏尔'}, {'code': '300677', 'name': '英科医疗'}, {'code': '300676', 'name': '华大基因'}, {'code': '300674', 'name': '宇信科技'}, {'code': '300662', 'name': '科锐国际'}, {'code': '300661', 'name': '圣邦股份'}, {'code': '300659', 'name': '中孚信息'}, {'code': '300655', 'name': '晶瑞电材'}, {'code': '300638', 'name': '广和通'}, {'code': '300636', 'name': '同和药业'}, {'code': '300634', 'name': '彩讯股份'}, {'code': '300631', 'name': '久吾高科'}, {'code': '300630', 'name': '普利制药'}, {'code': '300628', 'name': '亿联网络'}, {'code': '300627', 'name': '华测导航'}, {'code': '300624', 'name': '万兴科技'}, {'code': '300616', 'name': '尚品宅配'}, {'code': '300613', 'name': '富瀚微'}, {'code': '300604', 'name': '长川科技'}, {'code': '300601', 'name': '康泰生物'}, {'code': '300595', 'name': '欧普康视'}, {'code': '300593', 'name': '新雷能'}, {'code': '300587', 'name': '天铁股份'}, {'code': '300575', 'name': '中旗股份'}, {'code': '300573', 'name': '兴齐眼药'}, {'code': '300572', 'name': '安车检测'}, {'code': '300568', 'name': '星源材质'}, {'code': '300567', 'name': '精测电子'}, {'code': '300558', 'name': '贝达药业'}, {'code': '300529', 'name': '健帆生物'}, {'code': '300525', 'name': '博思软件'}, {'code': '300508', 'name': '维宏股份'}, {'code': '300502', 'name': '新易盛'}, {'code': '300496', 'name': '中科创达'}, {'code': '300490', 'name': '华自科技'}, {'code': '300487', 'name': '蓝晓科技'}, {'code': '300482', 'name': '万孚生物'}, {'code': '300476', 'name': '胜宏科技'}, {'code': '300474', 'name': '景嘉微'}, {'code': '300470', 'name': '中密控股'}, {'code': '300458', 'name': '全志科技'}, {'code': '300454', 'name': '深信服'}, {'code': '300451', 'name': '创业慧康'}, {'code': '300450', 'name': '先导智能'}, {'code': '300443', 'name': '金雷股份'}, {'code': '300433', 'name': '蓝思科技'}, {'code': '300432', 'name': '富临精工'}, {'code': '300421', 'name': '力星股份'}, {'code': '300416', 'name': '苏试试验'}, {'code': '300415', 'name': '伊之密'}, {'code': '300413', 'name': '芒果超媒'}, {'code': '300408', 'name': '三环集团'}, {'code': '300406', 'name': '九强生物'}, {'code': '300400', 'name': '劲拓股份'}, {'code': '300395', 'name': '菲利华'}, {'code': '300390', 'name': '天华超净'}, {'code': '300382', 'name': '斯莱克'}, {'code': '300379', 'name': '东方通'}, {'code': '300378', 'name': '鼎捷软件'}, {'code': '300374', 'name': '中铁装配'}, {'code': '300369', 'name': '绿盟科技'}, {'code': '300365', 'name': '恒华科技'}, {'code': '300363', 'name': '博腾股份'}, {'code': '300357', 'name': '我武生物'}, {'code': '300348', 'name': '长亮科技'}, {'code': '300347', 'name': '泰格医药'}, {'code': '300332', 'name': '天壕环境'}, {'code': '300331', 'name': '苏大维格'}, {'code': '300327', 'name': '中颖电子'}, {'code': '300323', 'name': '华灿光电'}, {'code': '300319', 'name': '麦捷科技'}, {'code': '300316', 'name': '晶盛机电'}, {'code': '300298', 'name': '三诺生物'}, {'code': '300285', 'name': '国瓷材料'}, {'code': '300280', 'name': '紫天科技'}, {'code': '300274', 'name': '阳光电源'}, {'code': '300263', 'name': '隆华科技'}, {'code': '300260', 'name': '新莱应材'}, {'code': '300257', 'name': '开山股份'}, {'code': '300253', 'name': '卫宁健康'}, {'code': '300251', 'name': '光线传媒'}, {'code': '300244', 'name': '迪安诊断'}, {'code': '300233', 'name': '金城医药'}, {'code': '300223', 'name': '北京君正'}, {'code': '300207', 'name': '欣旺达'}, {'code': '300203', 'name': '聚光科技'}, {'code': '300196', 'name': '长海股份'}, {'code': '300193', 'name': '佳士科技'}, {'code': '300188', 'name': '美亚柏科'}, {'code': '300179', 'name': '四方达'}, {'code': '300171', 'name': '东富龙'}, {'code': '300149', 'name': '睿智医药'}, {'code': '300144', 'name': '宋城演艺'}, {'code': '300143', 'name': '盈康生命'}, {'code': '300142', 'name': '沃森生物'}, {'code': '300133', 'name': '华策影视'}, {'code': '300124', 'name': '汇川技术'}, {'code': '300123', 'name': '亚光科技'}, {'code': '300122', 'name': '智飞生物'}, {'code': '300119', 'name': '瑞普生物'}, {'code': '300118', 'name': '东方日升'}, {'code': '300087', 'name': '荃银高科'}, {'code': '300083', 'name': '创世纪'}, {'code': '300077', 'name': '国民技术'}, {'code': '300073', 'name': '当升科技'}, {'code': '300070', 'name': '碧水源'}, {'code': '300065', 'name': '海兰信'}, {'code': '300059', 'name': '东方财富'}, {'code': '300058', 'name': '蓝色光标'}, {'code': '300054', 'name': '鼎龙股份'}, {'code': '300037', 'name': '新宙邦'}, {'code': '300036', 'name': '超图软件'}, {'code': '300035', 'name': '中科电气'}, {'code': '300034', 'name': '钢研高纳'}, {'code': '300033', 'name': '同花顺'}, {'code': '300015', 'name': '爱尔眼科'}, {'code': '300014', 'name': '亿纬锂能'}, {'code': '300012', 'name': '华测检测'}, {'code': '300009', 'name': '安科生物'}, {'code': '300007', 'name': '汉威科技'}, {'code': '300003', 'name': '乐普医疗'}, {'code': '06865', 'name': '福莱特玻璃'}, {'code': '06049', 'name': '保利物业'}, {'code': '03958', 'name': '东方证券'}, {'code': '03908', 'name': '中金公司'}, {'code': '03898', 'name': '时代电气'}, {'code': '03759', 'name': '康龙化成'}, {'code': '02883', 'name': '中海油田服务'}, {'code': '02333', 'name': '长城汽车'}, {'code': '01816', 'name': '中广核电力'}, {'code': '01776', 'name': '广发证券'}, {'code': '01772', 'name': '赣锋锂业'}, {'code': '01171', 'name': '兖州煤业股份'}, {'code': '01138', 'name': '中远海能'}, {'code': '00981', 'name': '中芯国际'}, {'code': '00956', 'name': '新天绿色能源'}, {'code': '00939', 'name': '建设银行'}, {'code': '00902', 'name': '华能国际电力股份'}, {'code': '00728', 'name': '中国电信'}, {'code': '00670', 'name': '中国东方航空股份'}, {'code': '003816', 'name': '中国广核'}, {'code': '003038', 'name': '鑫铂股份'}, {'code': '003022', 'name': '联泓新科'}, {'code': '003021', 'name': '兆威机电'}, {'code': '003016', 'name': '欣贺股份'}, {'code': '003012', 'name': '东鹏控股'}, {'code': '002987', 'name': '京北方'}, {'code': '002985', 'name': '北摩高科'}, {'code': '002982', 'name': '湘佳股份'}, {'code': '002968', 'name': '新大正'}, {'code': '002967', 'name': '广电计量'}, {'code': '002960', 'name': '青鸟消防'}, {'code': '002957', 'name': '科瑞技术'}, {'code': '002948', 'name': '青岛银行'}, {'code': '002938', 'name': '中银证券健康产业混合'}, {'code': '002938', 'name': '鹏鼎控股'}, {'code': '002930', 'name': '宏川智慧'}, {'code': '002928', 'name': '华夏航空'}, {'code': '002925', 'name': '盈趣科技'}, {'code': '002920', 'name': '德赛西威'}, {'code': '002913', 'name': '奥士康'}, {'code': '002897', 'name': '意华股份'}, {'code': '002895', 'name': '川恒股份'}, {'code': '002884', 'name': '凌霄泵业'}, {'code': '002879', 'name': '长缆科技'}, {'code': '002876', 'name': '三利谱'}, {'code': '002870', 'name': '香山股份'}, {'code': '002867', 'name': '周大生'}, {'code': '002851', 'name': '麦格米特'}, {'code': '002850', 'name': '科达利'}, {'code': '002841', 'name': '视源股份'}, {'code': '002837', 'name': '英维克'}, {'code': '002833', 'name': '弘亚数控'}, {'code': '002832', 'name': '比音勒芬'}, {'code': '002831', 'name': '裕同科技'}, {'code': '002821', 'name': '凯莱英'}, {'code': '002812', 'name': '恩捷股份'}, {'code': '002810', 'name': '山东赫达'}, {'code': '002791', 'name': '坚朗五金'}, {'code': '002777', 'name': '久远银海'}, {'code': '002756', 'name': '永兴材料'}, {'code': '002745', 'name': '木林森'}, {'code': '002727', 'name': '一心堂'}, {'code': '002714', 'name': '牧原股份'}, {'code': '002713', 'name': '东易日盛'}, {'code': '002709', 'name': '天赐材料'}, {'code': '002706', 'name': '良信股份'}, {'code': '002705', 'name': '新宝股份'}, {'code': '002698', 'name': '博实股份'}, {'code': '002677', 'name': '浙江美大'}, {'code': '002675', 'name': '东诚药业'}, {'code': '002655', 'name': '共达电声'}, {'code': '002651', 'name': '利君股份'}, {'code': '002648', 'name': '卫星化学'}, {'code': '002643', 'name': '万润股份'}, {'code': '002625', 'name': '光启技术'}, {'code': '002624', 'name': '完美世界'}, {'code': '002623', 'name': '亚玛顿'}, {'code': '002609', 'name': '捷顺科技'}, {'code': '002601', 'name': '中银证券价值精选灵活配置混合'}, {'code': '002601', 'name': '龙佰集团'}, {'code': '002599', 'name': '盛通股份'}, {'code': '002597', 'name': '金禾实业'}, {'code': '002595', 'name': '豪迈科技'}, {'code': '002594', 'name': '比亚迪'}, {'code': '002585', 'name': '双星新材'}, {'code': '002568', 'name': '百润股份'}, {'code': '002563', 'name': '森马服饰'}, {'code': '002557', 'name': '洽洽食品'}, {'code': '002555', 'name': '三七互娱'}, {'code': '002541', 'name': '鸿路钢构'}, {'code': '002539', 'name': '云图控股'}, {'code': '002531', 'name': '天顺风能'}, {'code': '002508', 'name': '老板电器'}, {'code': '002497', 'name': '雅化集团'}, {'code': '002493', 'name': '荣盛石化'}, {'code': '002487', 'name': '大金重工'}, {'code': '002484', 'name': '江海股份'}, {'code': '002481', 'name': '双塔食品'}, {'code': '002475', 'name': '中邮睿利增强债券'}, {'code': '002475', 'name': '立讯精密'}, {'code': '002472', 'name': '双环传动'}, {'code': '002466', 'name': '天齐锂业'}, {'code': '002460', 'name': '赣锋锂业'}, {'code': '002459', 'name': '晶澳科技'}, {'code': '002454', 'name': '松芝股份'}, {'code': '002452', 'name': '长高集团'}, {'code': '002444', 'name': '巨星科技'}, {'code': '002439', 'name': '启明星辰'}, {'code': '002438', 'name': '江苏神通'}, {'code': '002436', 'name': '兴森科技'}, {'code': '002430', 'name': '杭氧股份'}, {'code': '002425', 'name': '凯撒文化'}, {'code': '002415', 'name': '海康威视'}, {'code': '002414', 'name': '高德红外'}, {'code': '002410', 'name': '广联达'}, {'code': '002409', 'name': '雅克科技'}, {'code': '002407', 'name': '多氟多'}, {'code': '002402', 'name': '和而泰'}, {'code': '002398', 'name': '垒知集团'}, {'code': '002396', 'name': '星网锐捷'}, {'code': '002390', 'name': '信邦制药'}, {'code': '002389', 'name': '航天彩虹'}, {'code': '002386', 'name': '天原股份'}, {'code': '002385', 'name': '大北农'}, {'code': '002376', 'name': '新北洋'}, {'code': '002375', 'name': '亚厦股份'}, {'code': '002372', 'name': '伟星新材'}, {'code': '002371', 'name': '北方华创'}, {'code': '002353', 'name': '杰瑞股份'}, {'code': '002352', 'name': '顺丰控股'}, {'code': '002340', 'name': '格林美'}, {'code': '002332', 'name': '仙琚制药'}, {'code': '002327', 'name': '富安娜'}, {'code': '002326', 'name': '永太科技'}, {'code': '002318', 'name': '久立特材'}, {'code': '002315', 'name': '焦点科技'}, {'code': '002311', 'name': '海大集团'}, {'code': '002304', 'name': '洋河股份'}, {'code': '002299', 'name': '圣农发展'}, {'code': '002291', 'name': '星期六'}, {'code': '002271', 'name': '东方雨虹'}, {'code': '002268', 'name': '卫士通'}, {'code': '002266', 'name': '浙富控股'}, {'code': '002254', 'name': '泰和新材'}, {'code': '002245', 'name': '蔚蓝锂芯'}, {'code': '002241', 'name': '歌尔股份'}, {'code': '002240', 'name': '盛新锂能'}, {'code': '002237', 'name': '恒邦股份'}, {'code': '002236', 'name': '大华股份'}, {'code': '002234', 'name': '民和股份'}, {'code': '002230', 'name': '科大讯飞'}, {'code': '002223', 'name': '中邮尊享一年定开混合发起式'}, {'code': '002223', 'name': '鱼跃医疗'}, {'code': '002214', 'name': '大立科技'}, {'code': '002206', 'name': '海利得'}, {'code': '002192', 'name': '融捷股份'}, {'code': '002183', 'name': '怡亚通'}, {'code': '002182', 'name': '云海金属'}, {'code': '002180', 'name': '纳思达'}, {'code': '002179', 'name': '中航光电'}, {'code': '002176', 'name': '江特电机'}, {'code': '002170', 'name': '芭田股份'}, {'code': '002159', 'name': '三特索道'}, {'code': '002158', 'name': '汉钟精机'}, {'code': '002157', 'name': '正邦科技'}, {'code': '002154', 'name': '报喜鸟'}, {'code': '002153', 'name': '石基信息'}, {'code': '002145', 'name': '中核钛白'}, {'code': '002142', 'name': '宁波银行'}, {'code': '002138', 'name': '顺络电子'}, {'code': '002135', 'name': '东南网架'}, {'code': '002129', 'name': '中环股份'}, {'code': '002120', 'name': '韵达股份'}, {'code': '002111', 'name': '威海广泰'}, {'code': '002110', 'name': '三钢闽光'}, {'code': '002105', 'name': '信隆健康'}, {'code': '002088', 'name': '鲁阳节能'}, {'code': '002080', 'name': '中材科技'}, {'code': '002078', 'name': '太阳纸业'}, {'code': '002064', 'name': '华峰化学'}, {'code': '002050', 'name': '三花智控'}, {'code': '002049', 'name': '紫光国微'}, {'code': '002048', 'name': '宁波华翔'}, {'code': '002046', 'name': '国机精工'}, {'code': '002043', 'name': '兔宝宝'}, {'code': '002041', 'name': '登海种业'}, {'code': '002036', 'name': '联创电子'}, {'code': '002028', 'name': '思源电气'}, {'code': '002027', 'name': '分众传媒'}, {'code': '002026', 'name': '山东威达'}, {'code': '002025', 'name': '航天电器'}, {'code': '002019', 'name': '亿帆医药'}, {'code': '002013', 'name': '中航机电'}, {'code': '002008', 'name': '大族激光'}, {'code': '002003', 'name': '伟星股份'}, {'code': '001979', 'name': '招商蛇口'}, {'code': '001914', 'name': '招商积余'}, {'code': '00168', 'name': '青岛啤酒股份'}, {'code': '000998', 'name': '隆平高科'}, {'code': '000988', 'name': '华工科技'}, {'code': '000983', 'name': '山西焦煤'}, {'code': '000977', 'name': '浪潮信息'}, {'code': '000975', 'name': '银泰黄金'}, {'code': '000968', 'name': '蓝焰控股'}, {'code': '000961', 'name': '中南建设'}, {'code': '000959', 'name': '首钢股份'}, {'code': '000951', 'name': '中国重汽'}, {'code': '000933', 'name': '神火股份'}, {'code': '000932', 'name': '华菱钢铁'}, {'code': '000921', 'name': '中邮现金驿站货币A'}, {'code': '000921', 'name': '海信家电'}, {'code': '000912', 'name': '泸天化'}, {'code': '000910', 'name': '大亚圣象'}, {'code': '000906', 'name': '浙商中拓'}, {'code': '000902', 'name': '新洋丰'}, {'code': '000895', 'name': '双汇发展'}, {'code': '000887', 'name': '中鼎股份'}, {'code': '000860', 'name': '顺鑫农业'}, {'code': '000858', 'name': '五粮液'}, {'code': '000848', 'name': '承德露露'}, {'code': '000830', 'name': '鲁西化工'}, {'code': '000829', 'name': '天音控股'}, {'code': '000825', 'name': '太钢不锈'}, {'code': '000822', 'name': '山东海化'}, {'code': '000807', 'name': '云铝股份'}, {'code': '000799', 'name': '酒鬼酒'}, {'code': '000786', 'name': '北新建材'}, {'code': '000776', 'name': '广发证券'}, {'code': '000768', 'name': '中航西飞'}, {'code': '000762', 'name': '西藏矿业'}, {'code': '000739', 'name': '普洛药业'}, {'code': '000738', 'name': '航发控制'}, {'code': '000733', 'name': '振华科技'}, {'code': '000731', 'name': '四川美丰'}, {'code': '000725', 'name': '京东方A'}, {'code': '000708', 'name': '中信特钢'}, {'code': '000683', 'name': '远兴能源'}, {'code': '000661', 'name': '长春高新'}, {'code': '000657', 'name': '中钨高新'}, {'code': '000656', 'name': '金科股份'}, {'code': '000650', 'name': '仁和药业'}, {'code': '000636', 'name': '风华高科'}, {'code': '000635', 'name': '英力特'}, {'code': '000603', 'name': '盛达资源'}, {'code': '000596', 'name': '古井贡酒'}, {'code': '000591', 'name': '太阳能'}, {'code': '000568', 'name': '泸州老窖'}, {'code': '000547', 'name': '航天发展'}, {'code': '000538', 'name': '云南白药'}, {'code': '000537', 'name': '广宇发展'}, {'code': '000519', 'name': '中兵红箭'}, {'code': '000516', 'name': '国际医学'}, {'code': '000513', 'name': '丽珠集团'}, {'code': '000501', 'name': '鄂武商A'}, {'code': '000429', 'name': '粤高速A'}, {'code': '000403', 'name': '派林生物'}, {'code': '000401', 'name': '冀东水泥'}, {'code': '000400', 'name': '许继电气'}, {'code': '000338', 'name': '潍柴动力'}, {'code': '000333', 'name': '美的集团'}, {'code': '000301', 'name': '东方盛虹'}, {'code': '000166', 'name': '申万宏源'}, {'code': '000069', 'name': '华侨城A'}, {'code': '000063', 'name': '中兴通讯'}, {'code': '000012', 'name': '南玻A'}, {'code': '000009', 'name': '中国宝安'}, {'code': '000002', 'name': '万科A'}, {'code': '000001', 'name': '平安银行'}]
    pool = []
    eliminate_pool = eliminate_new_stock()
    data = ts.fund_holdings(year=year, quarter=quarter)
    for i in data.values:
        code = i[7]
        name = i[3]
        fundHoldingdRatio = float(i[6])
        if fundHoldingdRatio >= 2:
            pool.append({'code': code, 'name': name})
    logging.warning(f"基金持股占比大于2%个股数量:{len(pool)}\t{pool}")
    # 剔除二十日强度不足,上市不满半年,基金持股不足2%的个股
    target = [i for i in pool if i in eliminate_pool]
    for i in target:
        i['industry'] = NEW_STOCK_LIST[i['code'] + (".SH" if i['code'].startswith('6') else ".SZ")]['industry']
    logging.warning(f"最终股池: {target}")
    return target


def get_fund_holdings_V2(year=date.today().year):
    quarter = [2, 3]
    pool = {}
    data = ts.fund_holdings(year=year, quarter=quarter[0])
    for i in data.values:
        pool[i[-2]] = {'code': i[-2], 'name': i[3], 'fund': float(i[6])}
    new_data = ts.fund_holdings(year=date.today().year, quarter=quarter[1])
    for i in new_data.values:
        pool[i[-2]] = {'code': i[-2], 'name': i[3], 'fund': float(i[6])}
    print(len(pool), pool)


def get_finally_pool():
    from momentum import fund_holding
    eliminate = eliminate_new_stock()
    pool = [i for i in fund_holding if i in eliminate]
    for i in pool:
        i['industry'] = NEW_STOCK_LIST[i['code'] + (".SH" if i['code'].startswith('6') else ".SZ")]['industry']
    return pool


def get_industry_momentum():
    df = pd.read_csv(f"RPS{rps_day}.csv", encoding='utf-8')
    fund_pool = get_fund_holdings(quarter=quarter)
    result = {}
    for i in range(4, len(df.columns)):
        all_data = []
        high_data = []
        for j in df.values:
            all_data.append(j[2])
            if j[i] >= 87 and j[3] < int(str(date.today() - timedelta(days=180)).replace('-', '')) \
                    and {'code': j[0].replace('.SH', '').replace('.SZ', ''), 'name': j[1]} in fund_pool:
                high_data.append(j[2])
        all_data_count = {}
        high_data_count = {}
        for j in all_data:
            all_data_count[j] = all_data.count(j)
        for j in high_data:
            high_data_count[j] = high_data.count(j)
        momentum = []
        for j in all_data_count.keys():
            if j in high_data_count.keys():
                tmp = {'industry': j,
                       'rank_count': high_data_count[j],
                       'member_count': all_data_count[j],
                       'momentum_score': round(high_data_count[j] * high_data_count[j] / all_data_count[j], 2)}
                momentum.append(tmp)
        result[df.columns[i]] = sorted(momentum, key=lambda x: x['momentum_score'], reverse=True)
    return result


def run():
    filename = "行业动量模型.csv"
    create_RPS_file()
    data = get_industry_momentum()
    df = pd.DataFrame()
    for k, v in data.items():
        for i in v:
            df.loc[i['industry'], k] = i['momentum_score']
    df.to_csv(filename, encoding='utf-8')


def momentum_stock_filter(industry, fund_holding):
    pool = []
    fund_holding = [i['code'] for i in fund_holding]
    df = pd.read_csv(f'RPS{rps_day}.csv', encoding='utf-8')
    for i in df.values:
        if i[2] == industry and i[-1] > 87 and i[0].split('.')[0] in fund_holding:
            pool.append({'code': i[0], 'name': i[1]})
    return pool


def get_momentum_rank_top(filename="行业动量模型.csv"):
    industry_list = []
    fund_holding = get_fund_holdings(quarter=quarter)
    df = pd.read_csv(filename, encoding='utf-8')
    for i in df.values:
        if i[-1] > 1:
            industry_pool = momentum_stock_filter(industry=i[0], fund_holding=fund_holding)
            industry_list.append({'industry': i[0], df.columns[-5]: i[-5], df.columns[-4]: i[-4], df.columns[-3]: i[-3], df.columns[-2]: i[-2], df.columns[-1]: i[-1], 'industry_pool': industry_pool})
    industry_list = sorted(industry_list, key=lambda x: x[df.columns[-1]], reverse=True)
    for i in industry_list:
        print(i)


if __name__ == '__main__':
    run()

