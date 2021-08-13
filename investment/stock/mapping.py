from datetime import datetime


class StockObject(object):
    def __init__(self):
        self.code = None
        self.name = None
        self.current_price = None
        self.day_20_applies = None
        self.day_50_applies = None
        self.day_120_applies = None
        self.day_250_applies = None
        self.day_250_highest_price = None
        self.is_new = 0
        self.industry = None
        self.update_time = datetime.now()