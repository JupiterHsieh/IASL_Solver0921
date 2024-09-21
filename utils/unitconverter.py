
class UnitConverter:
    def __init__(self):
        self.length_factors = {'公分': 0.01, '公尺': 1, '毫米': 0.001, '公里': 1000, "公分毫米": 0.01, "公里公尺": 1000, "公尺公分": 1}
        self.time_factors = {'秒': 1, '分': 60, '分鐘': 60, '時': 3600, '小時': 3600, "分秒": 60, "分鐘秒": 60, "小時分鐘": 3600, "天": 86400, "星期": 604800}
        self.volume_factors = {'毫升': 0.001, '公升': 1, 'cc': 0.001}
        self.weight_factors = {'公克': 1, '公斤': 1000, '公噸': 1000000, 'g': 1, '毫克': 0.001}
        self.unit_factors = {'隻': 1, "雙": 2}

        self.unit_category_map = {}
        for category, factors in {'unit': self.unit_factors,
                                  'length': self.length_factors, 'time': self.time_factors, 'volume': self.volume_factors, 'weight': self.weight_factors}.items():
            for unit in factors:
                self.unit_category_map[unit] = category
