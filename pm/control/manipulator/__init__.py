import uiautomation as ui
import pandas as pd
import time
from datetime import datetime as dt
from datetime import timedelta as td

from pm.config import cfg
from pm.control.calculator import Calculator
from pm.control.casting import dt2str


class Manipulator(Calculator):
    rt = ui.PaneControl(searchDepth=5, ClassName='GXWND', AutomationId='3779')
    set_krw = ui.ButtonControl(searchDepth=5, Name='원화기준')


    @staticmethod
    def read_csv(*args, **kwargs):
        df = pd.read_csv(*args, **kwargs)
        return Manipulator(df.values, columns=df.columns, index=df.index)


    @staticmethod
    def get_stock(
        path:str=cfg.PATH_DATA,
        fn:str='origin.csv',
        backup:bool=True
    ) -> Manipulator:
        manip = Manipulator.read_csv(path, encoding='utf-8')
        if backup:
            manip.to_csv(f'{path}backup/{dt2str(dt.now())}.csv')
        return manip
    
    
    @staticmethod
    def get_stock_krw():
        pass


    @staticmethod
    def get_usd():
        pass


    @staticmethod
    def get_krw():
        pass


    def manipulate(self, start_time:dt=None, end_time:dt=None):
        if start_time is None:
            start_time=dt.now()
        if end_time is None:
            end_time=start_time+td(minutes=1)

        while dt.now() < start_time:
            time.sleep(10)

        self.get_stock_krw()
        while dt.now() < end_time:
            FLOW = self.get_flow(Manipulator.rt, Manipulator.set_krw)
            USD = 0
            KRW = 0
            self.calculate(FLOW)
            self['virtual_amt'] -= self.apply(self.bid_ask, axis=1)


    def calc_stock_krw(self):
        pass


    @staticmethod
    def get_flow(
        rt, 
        set_krw, 
        path:str=cfg.PATH_DATA, 
        fn:str='tmp.csv'
    ) -> Manipulator:
        file_path = path+fn
        rt.SetFocus()
        set_krw.Click()
        rt.RightClick()
        ui.MenuItemControl(searchDepth=3, Name='엑셀로 내보내기').Click()
        ui.MenuItemControl(searchDepth=4, Name='CSV').Click()
        ui.EditControl(searchDepth=6, Name='파일 이름(N):').SendKeys(file_path+'{Enter}')
        return Manipulator.read_csv(file_path, encoding='cp949')


    def bid_ask(self, row) -> int:
        pos = row['position']
        diff = row['virtual_diff']
        pivot = row['pivot_val']
        cprice = row['currrent_val']
        amt = self.bid_ask_amt(diff, cprice)

        if pos == 'neutral':
            if diff < -pivot:
                self.bid(amt)
            elif diff > pivot:
                self.ask(amt)

        elif pos == 'buy':
            if diff < -pivot:
                return amt
            elif diff > pivot:
                self.ask(amt)

        elif pos in ('sell', 'out'):
            if diff < -pivot:
                self.bid(amt)
            elif diff > pivot:
                return amt
        return 0


    @staticmethod
    def bid(amt:int):
        price = Manipulator.bid_ask_price()


    @staticmethod
    def ask(amt:int):
        price = Manipulator.bid_ask_price()


    @staticmethod
    def bid_ask_amt(diff:float, cprice:int) -> int:
        diff = abs(diff)
        if diff < cprice:
            return 1
        else:
            return diff // cprice


    @staticmethod
    def bid_ask_price():
        pass