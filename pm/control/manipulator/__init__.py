import uiautomation as ui
from uiautomation import uiautomation as ui_ui
import pandas as pd
import time
from datetime import datetime as dt
from datetime import timedelta as td

from pm.config import cfg
from pm.control.calculator import Calculator
from pm.control.casting import dt2str


class Manipulator(Calculator):
    FR_ACNT = ui.WindowControl(searchDepth=2, Name='(3805)주식잔고(해외주식)')

    ORDER = ui.WindowControl(searchDepth=2, Name='(3651)주식주문(미국/홍콩/후강퉁/선강퉁)')
    BTN_ORDER_US = ui.ButtonControl(searchDepth=4, Name='미국', AutomationId='3775')
    MINI_ORDER = ui.WindowControl(searchDepth=2, Name='(3754)미니주문(미국)')

    # MINI_ORDER
    BID_TICKER = ui.EditControl(searchDepth=5, AutomationId='3810')
    BID_AMT = ui.EditControl(searchDepth=5, AutomationId='3809')
    BID_PRICE = ui.ButtonControl(searchDepth=5, Name='매도1', AutomationId='3782')
    BID_BTN = ui.ButtonControl(searchDepth=5, Name='매수', AutomationId='3807')

    # ORDER
    ASK_TICKER = ui.EditControl(searchDepth=7, AutomationId='3812')
    ASK_AMT = ui.EditControl(searchDepth=7, AutomationId='3811')
    ASK_PRICE = ui.ButtonControl(searchDepth=7, Name='매수1', AutomationId='3782')
    ASK_BTN = ui.ButtonControl(searchDepth=7, Name='매도(팔자)', AutomationId='3809')

    RT = ui.PaneControl(searchDepth=5, ClassName='GXWND', AutomationId='3779')
    BTN_RT_KRW = ui.ButtonControl(searchDepth=5, Name='원화기준')


    @staticmethod
    def from_df(df):
        return Manipulator(df.values, columns=df.columns, index=df.index)


    @staticmethod
    def read_csv(*args, **kwargs):
        df = pd.read_csv(*args, **kwargs)
        return Manipulator.from_df(df)


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
    def get_stock(
        path:str=cfg.PATH_DATA,
        fn:str='origin.csv',
        backup:bool=True
    ):
        manip = Manipulator.read_csv(path, encoding='utf-8')
        if backup:
            manip.backup()
        return manip


    @staticmethod
    def get_flow(
        rt, 
        RT_SET_KRW, 
        path:str=cfg.PATH_DATA, 
        fn:str='tmp.csv'
    ):
        file_path = path+fn
        rt.SetFocus()
        RT_SET_KRW.Click()
        rt.RightClick()
        ui.MenuItemControl(searchDepth=3, Name='엑셀로 내보내기').Click()
        ui.MenuItemControl(searchDepth=4, Name='CSV').Click()
        ui.EditControl(searchDepth=6, Name='파일 이름(N):').SendKeys(file_path+'{Enter}')
        return Manipulator.read_csv(file_path, encoding='cp949')


    def bid_ask(self, row) -> int:
        cat = row['cat0']
        pos = row['position']
        diff = row['virtual_diff']
        pivot = row['pivot_val']
        cprice = row['currrent_val']
        amt = self.bid_ask_amt(diff, cprice)

        if cat=='CASH':
            pass

        elif (cat=='KR')\
            or (pos == 'neutral'):
            if diff < -pivot:
                self.bid(cprice, amt)
            elif diff > pivot:
                self.ask(cprice, amt)

        elif pos == 'buy':
            if diff < -pivot:
                return amt
            elif diff > pivot:
                self.ask(cprice, amt)

        elif pos in ('sell', 'out'):
            if diff < -pivot:
                self.bid(cprice, amt)
            elif diff > pivot:
                return amt
        return 0


    def bid(self, ticker:str, amt:str):
        self.MINI_ORDER.SetFocus()
        self.BID_TICKER.SendKeys(ticker+'{Enter}')
        self.BID_AMT.SendKeys(amt+'{Enter}')
        self.BID_PRICE.Click()
        self.BID_BTN.Click()
        ui_ui.SendKeys('{Enter}')
        ui_ui.SendKeys('{Enter}')
        # usd 조정


    def ask(self, ticker, amt):
        self.ORDER.SetFocus()
        # self.BTN_ASK_US.Click()
        self.ASK_TICKER.SendKeys(ticker+'{Enter}')
        self.ASK_AMT.SendKeys(amt+'{Enter}')
        self.ASK_PRICE.Click()
        self.ASK_BTN.Click()
        ui_ui.SendKeys('{Enter}')
        ui_ui.SendKeys('{Enter}')
        # usd 조정


    @staticmethod
    def bid_ask_amt(diff:float, cprice:int) -> int:
        diff = abs(diff)
        if diff < cprice:
            return 1
        else:
            return diff // cprice