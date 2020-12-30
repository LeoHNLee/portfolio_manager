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
    rt_krw = ui.PaneControl(searchDepth=4, ClassName='GXWND', AutomationId='3837')


    @staticmethod
    def read_csv(*args, **kwargs):
        df = pd.read_csv(*args, **kwargs)
        return Manipulator(df.values, columns=df.columns, index=df.index)


    @staticmethod
    def get_stock(
        path:str=cfg.PATH_DATA,
        fn:str='origin.csv',
        backup:bool=True
    ):
        manip = Manipulator.read_csv(path, encoding='utf-8')
        if backup:
            manip.backup()
        return manip


    def backup(self, backup_path:str=None):
        if backup_path is None:
            backup_path = f'{cfg.PATH_DATA}backup/{dt2str(dt.now())}.csv'
        self.to_csv(backup_path)


    def manipulate(self, start_time:dt=None, end_time:dt=None):
        if start_time is None:
            start_time=dt.now()
        if end_time is None:
            end_time=start_time+td(minutes=1)

        while dt.now() < start_time:
            time.sleep(10)

        FLOW_KRW = self.get_flow_krw(Manipulator.rt_krw)
        while dt.now() < end_time:
            FLOW = self.get_flow(Manipulator.rt, Manipulator.set_krw)
            USD = 0
            KRW = 0
            self.calculate(FLOW)
            self['virtual_amt'] -= self.apply(self.bid_ask, axis=1)
        self.backup()


    @staticmethod
    def get_flow_krw(
        rt, 
        path:str=cfg.PATH_DATA, 
        fn:str='krw.csv'
    ):
        file_path = path+fn
        rt.SetFocus()
        rt.RightClick()
        ui.MenuItemControl(searchDepth=3, Name='엑셀로 내보내기').Click()
        ui.MenuItemControl(searchDepth=4, Name='CSV').Click()
        ui.EditControl(searchDepth=6, Name='파일 이름(N):').SendKeys(file_path+'{Enter}')
        return Manipulator.read_csv(file_path, encoding='cp949')


    @staticmethod
    def get_flow(
        rt, 
        set_krw, 
        path:str=cfg.PATH_DATA, 
        fn:str='tmp.csv'
    ):
        rt.SetFocus()
        set_krw.Click()
        return Manipulator.get_flow_krw(rt, path, fn)


    def calc_flow_krw(self, krw_df):
        pass


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
        # usd 조정


    @staticmethod
    def ask(amt:int):
        price = Manipulator.bid_ask_price()
        # usd 조정


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