# encoding: utf-8
# 基金业绩排名
import json
import logging
import time
import requests
from datetime import date, timedelta
from .fundresults import get_fund_yield, get_fund_year_yield


def get_fund_rank(sort, top_count=500):
    # time.sleep(2)
    url = f"https://api.doctorxiong.club/v1/fund/rank"
    headers = {
        'Content-Type': 'application/json'
    }
    body = {
        'sort': sort,
        'fundType': ['gp', 'hh'],
        'pageIndex': 1,
        'pageSize': top_count
    }
    response = requests.post(url, json=body).json()
    # logging.warning(response)
    return response['data']['rank']


def get_all_funds():
    url = f"https://api.doctorxiong.club/v1/fund/all"
    response = requests.get(url).json()
    print(len(response['data']))


def get_fund_detail(code, start_date, end_date):
    url = "https://api.doctorxiong.club/v1/fund/detail"
    params = {
        'code': code,
        'startDate': start_date,
        'endDate': end_date
    }
    response = requests.get(url, params=params).json()
    response = response['data']
    print(json.dumps(response, indent=4, ensure_ascii=False))


def get_fund_detail_list(fund_list: list, start_date=date.today()-timedelta(days=1), end_date=date.today()):
    # 批量获取基金详情
    code = ",".join([i['code'] for i in fund_list])
    url = "https://api.doctorxiong.club/v1/fund/detail/list"
    params = {
        'code': code,
        'startDate': start_date,
        'endDate': end_date
    }
    response = requests.get(url, params=params).json()
    # logging.warning(f"response: {response}")
    response = response['data']
    for i in response:
        if 'totalWorth' in i.keys():
            del i['totalWorth']
        del i['type']
        del i['netWorth']
        del i['expectWorth']
        del i['expectGrowth']
        del i['dayGrowth']
        del i['lastWeekGrowth']
        del i['lastMonthGrowth']
        del i['lastThreeMonthsGrowth']
        del i['lastSixMonthsGrowth']
        del i['lastYearGrowth']
        del i['buyMin']
        del i['buyRate']
        del i['buySourceRate']
        del i['netWorthDate']
        del i['expectWorthDate']
        del i['netWorthData']
        del i['totalNetWorthData']
    return response


def fund_ranking_summary():
    # 基金业绩排行汇总
    # data_3m = get_fund_rank('3y', top_count=1000)
    # data_6m = get_fund_rank('6y', top_count=1000)
    data_1y = get_fund_rank('1n', top_count=500)
    data_2y = get_fund_rank('2n', top_count=500)
    data_3y = get_fund_rank('3n', top_count=500)
    data_5y = get_fund_rank('5n', top_count=500)
    # t1 = [i for i in data_6m if i in data_3m]
    t2 = [i for i in data_2y if i in data_1y]
    t3 = [i for i in data_5y if i in data_3y]
    # target = [i for i in t1 if i in [i for i in t3 if i in t2]]
    target = [i for i in t2 if i in t3]
    for i in target:
        del i['netWorthDate']
        del i['netWorth']
        del i['dayGrowth']
        del i['fundType']
        del i['expectWorthDate']
        del i['expectWorth']
        del i['expectGrowth']
        del i['lastWeekGrowth']
        del i['lastMonthGrowth']
        del i['lastThreeMonthsGrowth']
        del i['lastSixMonthsGrowth']
        del i['lastYearGrowth']
        del i['thisYearGrowth']
    logging.warning(f"target: {len(target)}\t{target}")
    return target


def fund_performance_calc(fund_list):
    years = (2017, 2018, 2019, 2020, 2021)
    data = []
    for fund in fund_list:
        for y in years:
            fund[y] = get_fund_yield(code=fund['code'], year=y)
        fund['3y'] = get_fund_year_yield(fund['code'], 3)
        fund['5y'] = get_fund_year_yield(fund['code'], 5)
        print(fund)
        data.append(fund)
    return fund_list


p = [{'code': '000336', 'name': '农银研究精选混合', 'manager': '赵诣', 'fundScale': '50.61亿'}, {'code': '540008', 'name': '汇丰晋信低碳先锋股票A', 'manager': '陆彬', 'fundScale': '108.63亿'}, {'code': '400015', 'name': '东方新能源汽车混合', 'manager': '李瑞', 'fundScale': '201.37亿'}, {'code': '001643', 'name': '汇丰晋信智造先锋股票A', 'manager': '陆彬', 'fundScale': '23.07亿'}, {'code': '001644', 'name': '汇丰晋信智造先锋股票C', 'manager': '陆彬', 'fundScale': '13.51亿'}, {'code': '001245', 'name': '工银生态环境股票', 'manager': '何肖颉', 'fundScale': '46.38亿'}, {'code': '001704', 'name': '国投瑞银进宝灵活配置混合', 'manager': '施成', 'fundScale': '32.39亿'}, {'code': '398051', 'name': '中海环保新能源混合', 'manager': '左剑', 'fundScale': '23.06亿'}, {'code': '001298', 'name': '金鹰民族新兴混合', 'manager': '韩广哲', 'fundScale': '10.54亿'}, {'code': '000828', 'name': '泰达转型机遇股票A', 'manager': '王鹏', 'fundScale': '41.79亿'}, {'code': '001156', 'name': '申万菱信新能源汽车混合', 'manager': '周小波', 'fundScale': '47.41亿'}, {'code': '000689', 'name': '前海开源新经济混合A', 'manager': '崔宸龙', 'fundScale': '63.08亿'}, {'code': '002083', 'name': '新华鑫动力灵活配置混合A', 'manager': '刘彬', 'fundScale': '21.76亿'}, {'code': '002084', 'name': '新华鑫动力灵活配置混合C', 'manager': '刘彬', 'fundScale': '12.98亿'}, {'code': '090018', 'name': '大成新锐产业混合', 'manager': '韩创', 'fundScale': '130.97亿'}, {'code': '000409', 'name': '鹏华环保产业股票', 'manager': '孟昊', 'fundScale': '36.04亿'}, {'code': '550009', 'name': '信诚中小盘混合', 'manager': '孙浩中', 'fundScale': '4.95亿'}, {'code': '001476', 'name': '中银智能制造股票A', 'manager': '王伟', 'fundScale': '16.27亿'}, {'code': '001569', 'name': '泰信国策驱动灵活配置混合', 'manager': '吴秉韬', 'fundScale': '2.70亿'}, {'code': '400032', 'name': '东方主题精选混合', 'manager': '蒋茜', 'fundScale': '13.36亿'}, {'code': '001951', 'name': '金鹰改革红利混合', 'manager': '韩广哲', 'fundScale': '48.07亿'}, {'code': '210008', 'name': '金鹰策略配置混合', 'manager': '韩广哲', 'fundScale': '12.47亿'}, {'code': '001300', 'name': '大成睿景灵活配置混合A', 'manager': '韩创', 'fundScale': '28.11亿'}, {'code': '000126', 'name': '招商安润混合', 'manager': '任琳娜', 'fundScale': '11.17亿'}, {'code': '700003', 'name': '平安策略先锋混合', 'manager': '神爱前', 'fundScale': '6.58亿'}, {'code': '001301', 'name': '大成睿景灵活配置混合C', 'manager': '韩创', 'fundScale': '25.27亿'}, {'code': '001822', 'name': '华商智能生活灵活配置混合', 'manager': '高兵', 'fundScale': '5.82亿'}, {'code': '481010', 'name': '工银中小盘混合', 'manager': '黄安乐', 'fundScale': '24.70亿'}, {'code': '002669', 'name': '华商万众创新混合', 'manager': '梁皓', 'fundScale': '23.04亿'}, {'code': '210003', 'name': '金鹰行业优势混合', 'manager': '倪超', 'fundScale': '7.24亿'}, {'code': '165516', 'name': '信诚周期轮动混合(LOF)', 'manager': '张弘', 'fundScale': '31.89亿'}, {'code': '001716', 'name': '工银新趋势灵活配置混合A', 'manager': '何肖颉', 'fundScale': '5.54亿'}, {'code': '000729', 'name': '建信中小盘先锋股票A', 'manager': '周智硕', 'fundScale': '9.47亿'}, {'code': '001702', 'name': '东方创新科技混合', 'manager': '蒋茜', 'fundScale': '9.81亿'}, {'code': '001933', 'name': '华商新兴活力混合', 'manager': '高兵', 'fundScale': '2.09亿'}, {'code': '001997', 'name': '工银新趋势灵活配置混合C', 'manager': '何肖颉', 'fundScale': '1.81亿'}, {'code': '001858', 'name': '建信鑫利灵活配置混合', 'manager': '陶灿', 'fundScale': '4.21亿'}, {'code': '162202', 'name': '泰达宏利周期混合', 'manager': '张勋', 'fundScale': '4.52亿'}, {'code': '001616', 'name': '嘉实环保低碳股票', 'manager': '姚志鹏', 'fundScale': '56.39亿'}, {'code': '519126', 'name': '浦银安盛新经济结构混合A', 'manager': '蒋佳良', 'fundScale': '37.69亿'}, {'code': '000592', 'name': '建信改革红利股票', 'manager': '陶灿', 'fundScale': '6.70亿'}, {'code': '519702', 'name': '交银趋势混合A', 'manager': '杨金金', 'fundScale': '78.18亿'}, {'code': '000462', 'name': '农银主题轮动混合', 'manager': '张燕', 'fundScale': '5.64亿'}, {'code': '040015', 'name': '华安动态灵活配置混合A', 'manager': '蒋璆', 'fundScale': '9.80亿'}, {'code': '002168', 'name': '嘉实智能汽车股票', 'manager': '姚志鹏', 'fundScale': '54.69亿'}, {'code': '000739', 'name': '平安新鑫先锋A', 'manager': '张晓泉', 'fundScale': '1.13亿'}, {'code': '001279', 'name': '中海积极增利混合', 'manager': '左剑', 'fundScale': '3.38亿'}, {'code': '550015', 'name': '中信保诚至远动力混合A', 'manager': '王睿', 'fundScale': '48.18亿'}, {'code': '000603', 'name': '易方达创新驱动灵活配置混合', 'manager': '贾健', 'fundScale': '58.14亿'}, {'code': '001515', 'name': '平安新鑫先锋C', 'manager': '张晓泉', 'fundScale': '0.80亿'}, {'code': '000924', 'name': '宝盈先进制造混合A', 'manager': '张仲维', 'fundScale': '13.05亿'}, {'code': '530001', 'name': '建信恒久价值混合', 'manager': '陶灿', 'fundScale': '13.36亿'}, {'code': '167002', 'name': '平安鼎越混合(LOF)', 'manager': '张俊生', 'fundScale': '1.71亿'}, {'code': '003624', 'name': '创金合信资源股票发起式A', 'manager': '李游', 'fundScale': '6.39亿'}, {'code': '550016', 'name': '中信保诚至远动力混合C', 'manager': '王睿', 'fundScale': '6.52亿'}, {'code': '003625', 'name': '创金合信资源股票发起式C', 'manager': '李游', 'fundScale': '6.37亿'}, {'code': '610006', 'name': '信达澳银产业升级混合', 'manager': '曾国富', 'fundScale': '8.45亿'}, {'code': '001740', 'name': '光大中国制造2025混合', 'manager': '魏晓雪', 'fundScale': '13.79亿'}, {'code': '001410', 'name': '信达澳银新能源产业股票', 'manager': '冯明远', 'fundScale': '148.10亿'}, {'code': '001054', 'name': '工银新金融股票A', 'manager': '鄢耀', 'fundScale': '91.05亿'}, {'code': '270028', 'name': '广发制造业精选混合A', 'manager': '李巍', 'fundScale': '14.63亿'}, {'code': '002256', 'name': '金信行业优选混合发起式', 'manager': '孔学兵', 'fundScale': '1.14亿'}, {'code': '519095', 'name': '新华行业周期轮换混合', 'manager': '刘彬', 'fundScale': '3.32亿'}, {'code': '519002', 'name': '华安安信消费混合A', 'manager': '王斌', 'fundScale': '25.01亿'}, {'code': '001808', 'name': '银华互联网主题灵活配置混合', 'manager': '王浩', 'fundScale': '1.28亿'}, {'code': '398021', 'name': '中海能源策略混合', 'manager': '姚晨曦', 'fundScale': '16.32亿'}, {'code': '519196', 'name': '万家新兴蓝筹灵活配置混合', 'manager': '莫海波', 'fundScale': '17.81亿'}, {'code': '000756', 'name': '建信潜力新蓝筹股票', 'manager': '周智硕', 'fundScale': '1.19亿'}, {'code': '200015', 'name': '长城优化升级混合A', 'manager': '周诗博', 'fundScale': '3.26亿'}, {'code': '377240', 'name': '上投摩根新兴动力混合A', 'manager': '杜猛', 'fundScale': '72.54亿'}, {'code': '001701', 'name': '中融产业升级混合', 'manager': '甘传琦', 'fundScale': '2.20亿'}, {'code': '001487', 'name': '宝盈优势产业混合A', 'manager': '肖肖', 'fundScale': '21.93亿'}, {'code': '000601', 'name': '华宝创新优选混合', 'manager': '代云锋', 'fundScale': '19.87亿'}, {'code': '001158', 'name': '工银新材料新能源股票', 'manager': '张剑峰', 'fundScale': '25.62亿'}, {'code': '002170', 'name': '东吴移动互联混合C', 'manager': '刘元海', 'fundScale': '0.03亿'}, {'code': '519089', 'name': '新华优选成长混合', 'manager': '栾超', 'fundScale': '5.50亿'}, {'code': '002340', 'name': '富国价值优势混合', 'manager': '孙彬', 'fundScale': '46.86亿'}, {'code': '610004', 'name': '信达澳银中小盘混合', 'manager': '曾国富', 'fundScale': '10.11亿'}, {'code': '001323', 'name': '东吴移动互联混合A', 'manager': '刘元海', 'fundScale': '0.82亿'}, {'code': '519909', 'name': '华安安顺混合', 'manager': '高钥群', 'fundScale': '14.08亿'}, {'code': '001809', 'name': '中信建投智信物联网A', 'manager': '周紫光', 'fundScale': '3.46亿'}, {'code': '001366', 'name': '金鹰产业整合混合', 'manager': '杨晓斌', 'fundScale': '2.55亿'}, {'code': '202027', 'name': '南方高端装备灵活配置混合A', 'manager': '张磊', 'fundScale': '14.99亿'}, {'code': '001811', 'name': '中欧明睿新常态混合A', 'manager': '周应波', 'fundScale': '88.46亿'}, {'code': '001827', 'name': '富国研究优选沪港深混合', 'manager': '厉叶淼', 'fundScale': '1.55亿'}, {'code': '660015', 'name': '农银行业轮动混合', 'manager': '邢军亮', 'fundScale': '2.78亿'}, {'code': '000242', 'name': '景顺长城策略精选灵活配置混合', 'manager': '张靖', 'fundScale': '14.22亿'}, {'code': '002213', 'name': '中海顺鑫灵活配置混合', 'manager': '邱红丽', 'fundScale': '1.03亿'}, {'code': '001718', 'name': '工银物流产业股票', 'manager': '张宇帆', 'fundScale': '15.45亿'}, {'code': '001387', 'name': '中融新经济混合A', 'manager': '甘传琦', 'fundScale': '2.11亿'}, {'code': '519091', 'name': '新华泛资源优势混合', 'manager': '栾超', 'fundScale': '11.29亿'}, {'code': '001388', 'name': '中融新经济混合C', 'manager': '甘传琦', 'fundScale': '0.76亿'}, {'code': '000124', 'name': '华宝服务优选混合', 'manager': '代云锋', 'fundScale': '8.43亿'}, {'code': '540003', 'name': '汇丰晋信动态策略混合A', 'manager': '陆彬', 'fundScale': '77.97亿'}, {'code': '166019', 'name': '中欧价值智选混合A', 'manager': '袁维德', 'fundScale': '103.56亿'}, {'code': '001887', 'name': '中欧价值智选混合E', 'manager': '袁维德', 'fundScale': '24.29亿'}, {'code': '673060', 'name': '西部利得景瑞灵活配置混合A', 'manager': '陈保国', 'fundScale': '4.39亿'}, {'code': '310358', 'name': '申万菱信新经济混合', 'manager': '付娟', 'fundScale': '25.87亿'}, {'code': '000547', 'name': '建信健康民生混合', 'manager': '姜锋', 'fundScale': '7.56亿'}, {'code': '519195', 'name': '万家品质', 'manager': '莫海波', 'fundScale': '10.03亿'}, {'code': '001471', 'name': '融通新能源灵活配置混合', 'manager': '彭炜', 'fundScale': '6.73亿'}, {'code': '000431', 'name': '鹏华品牌传承混合', 'manager': '孟昊', 'fundScale': '6.40亿'}, {'code': '240022', 'name': '华宝资源优选混合A', 'manager': '蔡目荣', 'fundScale': '19.11亿'}, {'code': '163807', 'name': '中银优选灵活配置混合A', 'manager': '王伟', 'fundScale': '13.42亿'}, {'code': '375010', 'name': '上投摩根中国优势混合', 'manager': '杜猛', 'fundScale': '27.42亿'}, {'code': '040035', 'name': '华安逆向策略混合A', 'manager': '崔莹', 'fundScale': '58.97亿'}, {'code': '002281', 'name': '建信裕利灵活配置混合', 'manager': '江映德', 'fundScale': '0.96亿'}, {'code': '001018', 'name': '易方达新经济混合', 'manager': '陈皓', 'fundScale': '31.07亿'}, {'code': '003304', 'name': '前海开源沪港深核心资源混合A', 'manager': '吴国清', 'fundScale': '2.86亿'}, {'code': '003305', 'name': '前海开源沪港深核心资源混合C', 'manager': '吴国清', 'fundScale': '1.68亿'}, {'code': '310368', 'name': '申万菱信竞争优势混合', 'manager': '廖明兵', 'fundScale': '1.21亿'}, {'code': '001070', 'name': '建信信息产业股票', 'manager': '邵卓', 'fundScale': '6.76亿'}, {'code': '377530', 'name': '上投摩根行业轮动混合A', 'manager': '孙芳', 'fundScale': '13.32亿'}, {'code': '000308', 'name': '建信创新中国混合', 'manager': '邵卓', 'fundScale': '2.69亿'}, {'code': '550002', 'name': '中信保诚精萃成长混合', 'manager': '王睿', 'fundScale': '20.22亿'}, {'code': '000039', 'name': '农银高增长混合', 'manager': '张燕', 'fundScale': '2.65亿'}, {'code': '370024', 'name': '上投摩根核心优选混合', 'manager': '孙芳', 'fundScale': '18.27亿'}, {'code': '000698', 'name': '宝盈科技30混合', 'manager': '张仲维', 'fundScale': '14.11亿'}, {'code': '160421', 'name': '华安智增精选混合', 'manager': '王春', 'fundScale': '1.54亿'}, {'code': '690011', 'name': '民生加银积极成长混合发起式', 'manager': '金耀', 'fundScale': '3.25亿'}, {'code': '519158', 'name': '新华趋势领航混合', 'manager': '栾超', 'fundScale': '4.52亿'}, {'code': '000985', 'name': '嘉实逆向策略股票', 'manager': '曲盛伟', 'fundScale': '9.37亿'}, {'code': '001220', 'name': '民生加银研究精选混合', 'manager': '蔡晓', 'fundScale': '3.00亿'}, {'code': '001000', 'name': '中欧明睿新起点混合', 'manager': '葛兰', 'fundScale': '39.23亿'}, {'code': '000404', 'name': '易方达新兴成长灵活配置', 'manager': '刘武', 'fundScale': '47.47亿'}, {'code': '001072', 'name': '华安智能装备主题股票A', 'manager': '李欣', 'fundScale': '9.20亿'}, {'code': '162208', 'name': '泰达宏利首选企业股票', 'manager': '张勋', 'fundScale': '6.22亿'}, {'code': '160919', 'name': '大成产业升级股票(LOF)', 'manager': '李林益', 'fundScale': '3.23亿'}, {'code': '257070', 'name': '国联安优选行业混合', 'manager': '潘明', 'fundScale': '13.58亿'}, {'code': '050010', 'name': '博时特许价值混合A', 'manager': '曾鹏', 'fundScale': '6.35亿'}, {'code': '460001', 'name': '华泰柏瑞盛世中国混合', 'manager': '牛勇', 'fundScale': '22.62亿'}, {'code': '630016', 'name': '华商价值共享混合发起式', 'manager': '何奇峰', 'fundScale': '1.92亿'}, {'code': '001677', 'name': '中银战略新兴产业股票A', 'manager': '钱亚风云', 'fundScale': '4.98亿'}]

