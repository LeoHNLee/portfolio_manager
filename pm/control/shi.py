import asyncio
import time
from datetime import datetime as dt
from datetime import timedelta as td
import uiautomation as ui
from uiautomation import uiautomation as ui_ui
import pandas as pd

from pm.config import cfg
from pm.control import Controller
from pm.control.casting import dt2str, fstr2int
from pm.control.view import pbar_cntr, tb_cntr


class SHI(Controller):
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
        return SHI(df.values, columns=df.columns, index=df.index)


    @staticmethod
    def read_csv(*args, **kwargs):
        df = pd.read_csv(*args, **kwargs)
        return SHI.from_df(df)


    def backup(self, backup_path:str=None):
        if backup_path is None:
            backup_path = f'{cfg.PATH_DATA}backup/{dt2str(dt.now())}.csv'
        self.to_csv(backup_path)


    async def run(
        self, start_time:dt=None, end_time:dt=None, backup=False,
        pbar=None, iter_tb=None, trans_tb=None,
    ):
        if start_time is None:
            start_time=dt.now()
        if end_time is None:
            end_time=start_time+td(minutes=1)

        while dt.now() < start_time:
            await asyncio.sleep(60)

        if backup:
            self.backup()

        while dt.now() < end_time:
            if pbar is not None:
                pbar_cntr(pbar, start_time, end_time)
            if iter_tb is not None:
                tb_cntr.plus(iter_tb, 1)
            tmp_df = self.get_flow(SHI.rt, SHI.RT_SET_KRW)
            self.calculate(tmp_df=tmp_df)
            self['virtual_amt'] -= self.apply(lambda row: self.order(row, trans_tb), axis=1)
        self.backup()


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
        ret = SHI.read_csv(file_path, encoding='cp949')
        ret['현재가'] = ret['현재가'].apply(fstr2int)
        return ret


    def order(self, row, trans_tb=None) -> int:
        ticker = row['name']
        cat = row['cat0']
        pos = row['position']
        diff = row['virtual_diff']
        pivot = row['pivot_val']
        cprice = row['currrent_val']
        amt = self.order_amt(diff, cprice)

        if cat=='CASH':
            pass

        elif (cat=='KR')\
            or (pos == 'neutral'):
            if diff < -pivot:
                self.bid(ticker, amt, cprice, trans_tb)
            elif diff > pivot:
                self.ask(ticker, amt, cprice, trans_tb)

        elif pos == 'buy':
            if diff < -pivot:
                return amt
            elif diff > pivot:
                self.ask(ticker, amt, cprice, trans_tb)

        elif pos in ('sell', 'out'):
            if diff < -pivot:
                self.bid(ticker, amt, cprice, trans_tb)
            elif diff > pivot:
                return amt
        return 0


    def bid(self, ticker:str, amt:int, cprice:float, trans_tb=None):
        if trans_tb is not None:
            tb_cntr.plus(trans_tb, 1)
        self.MINI_ORDER.SetFocus()
        self.BID_TICKER.SendKeys(ticker+'{Enter}')
        self.BID_AMT.SendKeys(str(amt)+'{Enter}')
        self.BID_PRICE.Click()
        self.BID_BTN.Click()
        ui_ui.SendKeys('{Enter}')
        ui_ui.SendKeys('{Enter}')
        self.usd -= amt*cprice


    def ask(self, ticker:str, amt:int, cprice:float, trans_tb=None):
        if trans_tb is not None:
            tb_cntr.plus(trans_tb, 1)
        self.ORDER.SetFocus()
        self.ASK_TICKER.SendKeys(ticker+'{Enter}')
        self.ASK_AMT.SendKeys(str(amt)+'{Enter}')
        self.ASK_PRICE.Click()
        self.ASK_BTN.Click()
        ui_ui.SendKeys('{Enter}')
        ui_ui.SendKeys('{Enter}')
        self.usd += amt*cprice


    @staticmethod
    def order_amt(diff:float, cprice:int) -> int:
        diff = abs(diff)
        if diff < cprice:
            return 1
        else:
            return diff // cprice