import time
from datetime import datetime as dt
from datetime import timedelta as td
import uiautomation as ui
from uiautomation import uiautomation as ui_ui
import pandas as pd

from pm.config import cfg
from pm.log import log, log_order, log_bid, log_ask, log_backup, log_save
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


    @staticmethod
    def from_df(df):
        return SHI(df.values, columns=df.columns, index=df.index)


    @staticmethod
    def read_csv(*args, **kwargs):
        df = pd.read_csv(*args, **kwargs)
        return SHI.from_df(df)


    def save(self, my_path:str=None):
        if my_path is None:
            my_path = f'{cfg.PATH_DATA}origin.csv'
        self.to_csv(index=False, encoding='cp949')
        log_save(my_path)


    def backup(self, backup_path:str=None):
        if backup_path is None:
            backup_path = f'{cfg.PATH_DATA}backup/{dt2str(dt.now())}.csv'
        self.to_csv(backup_path, index=False, encoding='cp949')
        log_backup(backup_path)


    def run(
        self, start_time:dt=None, end_time:dt=None,
        pbar=None, iter_tb=None, trans_tb=None,
    ):
        log('RUN_SHI_CONTROLLER')
        if start_time is None:
            start_time=dt.now()
        if end_time is None:
            end_time=start_time+td(minutes=1)

        while dt.now() < start_time:
            log('WAIT UNTIL OPEN MARCKET')
            time.sleep(60)

        while dt.now() < end_time:
            if pbar is not None:
                pbar_cntr.timer(pbar, start_time, end_time)
            if iter_tb is not None:
                tb_cntr.plus(iter_tb, 1)
            tmp_df = self.get_flow()
            self.calculate(tmp_df=tmp_df)
            self['virtual_amt'] -= self.apply(lambda row: self.order(row, trans_tb), axis=1)
            self.save()


    @staticmethod
    def get_flow(
        root_path:str=cfg.PATH,
        dir_path:str=cfg.PATH_DATA, 
        fn:str='tmp.csv',
    ):
        file_path = f'{root_path}{dir_path[:-1]}\\{fn}'
        rt = ui.PaneControl(searchDepth=5, ClassName='GXWND', AutomationId='3779')
        rt.SetFocus()
        ui.ButtonControl(searchDepth=5, Name='원화기준').Click()
        rt.RightClick()
        ui.MenuItemControl(searchDepth=3, Name='엑셀로 내보내기').Click()
        ui.MenuItemControl(searchDepth=4, Name='CSV').Click()
        ui.EditControl(searchDepth=6, Name='파일 이름(N):').SendKeys(file_path+'{Enter}')
        ui.ButtonControl(searchDepth=6, Name='예(Y)', AutomationId='CommandButton_6').Click()
        ret = SHI.read_csv(file_path, encoding='cp949')
        ret['현재가'] = ret['현재가'].apply(fstr2int)
        log('GET_FLOW')
        return ret


    def order(self, row, trans_tb=None) -> int:
        ticker = row['name']
        cat = row['cat0']
        pos = row['position']
        bf_amt = row['current_amt']
        diff = row['virtual_diff']
        pivot = row['pivot_val']
        cprice = row['current_val']
        amt = self.order_amt(diff, cprice)

        if cat=='CASH':
            pass

        elif cat == 'KR':
            if (diff < -pivot) or (diff > pivot):
                return amt

        elif pos == 'neutral':
            if diff < -pivot:
                self.bid(ticker, amt)
                self.after_order('BID', ticker, amt, cprice, bf_amt, avg_price, trans_tb)
            elif diff > pivot:
                self.ask(ticker, amt)
                self.after_order('ASK', ticker, amt, cprice, bf_amt, avg_price, trans_tb)

        elif pos == 'buy':
            if diff < -pivot:
                return amt
            elif diff > pivot:
                self.ask(ticker, amt)
                self.after_order('ASK', ticker, amt, cprice, bf_amt, avg_price, trans_tb)

        elif pos in ('sell', 'out'):
            if diff < -pivot:
                self.bid(ticker, amt)
                self.after_order('BID', ticker, amt, cprice, bf_amt, avg_price, trans_tb)
            elif diff > pivot:
                return amt
        log_order(
            'ORDER',
            ticker,
            self.usd,
            exec_amt=amt,
            pivot=pivot,
            diff=diff,
        )
        return 0


    def bid(self, ticker:str, amt:int):
        self.MINI_ORDER.SetFocus()
        self.BID_TICKER.SendKeys(ticker+'{Enter}')
        self.BID_AMT.SendKeys(str(amt)+'{Enter}')
        self.BID_PRICE.Click()
        self.BID_BTN.Click()
        ui_ui.SendKeys('{Enter}')
        ui_ui.SendKeys('{Enter}')


    def ask(self, ticker:str, amt:int):
        self.ORDER.SetFocus()
        self.ASK_TICKER.SendKeys(ticker+'{Enter}')
        self.ASK_AMT.SendKeys(str(amt)+'{Enter}')
        self.ASK_PRICE.Click()
        self.ASK_BTN.Click()
        ui_ui.SendKeys('{Enter}')
        ui_ui.SendKeys('{Enter}')


    def after_order(self, type, ticker, amt, cprice, bf_amt, avg_price, trans_tb=None):
        if trans_tb is not None:
            tb_cntr.plus(trans_tb, 1)

        if type=='BID':
            self.usd -= amt*cprice
            log_bid(ticker, self.usd, amt, cprice, bf_amt)

        elif type=='ASK':
            self.usd += amt*cprice
            gain = amt*(cprice-avg_price)
            log_ask(ticker, self.usd, amt, cprice, bf_amt, gain)


    @staticmethod
    def order_amt(diff:float, cprice:int) -> int:
        diff = abs(diff)
        if diff < cprice:
            return 1
        else:
            return diff // cprice