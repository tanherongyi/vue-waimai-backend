from math import radians, cos, sin, asin, sqrt


def cal_dis(lat1, lng1, lat2, lng2):
    # 将十进制度数转化为弧度
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    # 计算结果
    dlon = lng2 - lng1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371
    return c * r
