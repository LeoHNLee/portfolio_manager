import time
from datetime import datetime as dt
from datetime import timedelta as td
import uiautomation as ui
from uiautomation import uiautomation as ui_ui
import pandas as pd
import numpy as np

from pm.config import cfg
from pm.log import dt2log, log, log_err, log_order, log_bid, log_ask, log_bid_fail, log_ask_fail, log_backup, log_save
from pm.control import Controller
from pm.control.casting import fstr2int
from pm.control.view import pbar_cntr, tb_cntr


class SHI(Controller):
    @staticmethod
    def from_df(df):
        return SHI(df.values, columns=df.columns, index=df.index)


    @staticmethod
    def read_csv(*args, **kwargs):
        df = pd.read_csv(*args, **kwargs)
        return SHI.from_df(df)


    def save(self, my_path:str=None):
        if my_path is None:
            my_path = f'{cfg.PATH}{cfg.PATH_DATA[:-1]}\\origin.csv'
        self.to_csv(my_path, index=False, encoding='cp949')
        log_save(my_path)


    def backup(self, backup_path:str=None):
        if backup_path is None:
            backup_path = f'{cfg.PATH_DATA}backup/{dt2log(dt.now())}.csv'
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
            n_try = 0
            while n_try < 10:
                try:
                    tmp_df = self.get_flow()
                except LookupError as e:
                    n_try += 1
                    log_err('LooupError', e)
                    if n_try >= 10:
                        raise LookupError(str(e))
                else:
                    break
            self.calculate(tmp_df=tmp_df)
            self['virtual_amt'] -= self.apply(lambda row: self.order(row, trans_tb), axis=1)
            self['position'] = self.apply(self.adjust_pos, axis=1)
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
        t_diff = row['target_diff']
        v_diff = row['virtual_diff']
        pivot = row['pivot_val']
        cprice = row['current_val']
        v_amt = self.order_amt(v_diff, cprice)
        t_amt = self.order_amt(t_diff, cprice)

        if cat!='US':
            pass

        elif pos == 'neutral':
            if t_diff < -pivot:
                self.ask(ticker, t_amt, cprice, bf_amt, trans_tb)
            elif t_diff > pivot:
                self.bid(ticker, t_amt, cprice, bf_amt, trans_tb)

        elif pos == 'buy':
            if v_diff < -pivot:
                log_order('VIRTUAL_ASK', ticker, self.usd, exec_amt=v_amt, pivot=pivot, diff=v_diff)
                return v_amt
            elif v_diff > pivot:
                self.bid(ticker, v_amt, cprice, bf_amt, trans_tb)

        elif pos in ('sell', 'out'):
            if v_diff < -pivot:
                self.ask(ticker, v_amt, cprice, bf_amt, trans_tb)
            elif v_diff > pivot:
                log_order('VIRTUAL_BID', ticker, self.usd, exec_amt=v_amt, pivot=pivot, diff=v_diff)
                return v_amt
        return 0


    def bid(self, ticker:str, amt:int, cprice:int, bf_amt, trans_tb):
        if self.usd < cprice*2:
            return log_bid_fail(ticker, self.usd, cprice)

        try:
            ui.WindowControl(searchDepth=2, Name='(3754)미니주문(미국)').SetFocus()
            ui.EditControl(searchDepth=5, AutomationId='3810').SendKeys(ticker+'{Enter}')
            time.sleep(0.5)
            ui.EditControl(searchDepth=5, AutomationId='3809').SendKeys(str(amt)+'{Enter}')
            ui.ButtonControl(searchDepth=5, Name='매도1', AutomationId='3782').Click()
            ui.ButtonControl(searchDepth=5, Name='매수', AutomationId='3807').Click()
            ui_ui.SendKeys('{Enter}')
            ui_ui.SendKeys('{Enter}')
        except LookupError as e:
            log_bid_fail(ticker, self.usd, cprice)
        else:
            self.usd -= amt*cprice
            log_bid(ticker, self.usd, amt, cprice, bf_amt)
            tb_cntr.plus(trans_tb, 1)


    def ask(self, ticker:str, amt:int, cprice:int, bf_amt:int, trans_tb):
        if bf_amt < amt:
            return log_ask_fail(ticker, self.usd, amt, bf_amt)

        try:
            ui.WindowControl(searchDepth=2, Name='(3651)주식주문(미국/홍콩/후강퉁/선강퉁)').SetFocus()
            ui.EditControl(searchDepth=7, AutomationId='3812').SendKeys(ticker+'{Enter}')
            time.sleep(0.5)
            ui.EditControl(searchDepth=7, AutomationId='3811').SendKeys(str(amt)+'{Enter}')
            ui.ButtonControl(searchDepth=7, Name='매수1', AutomationId='3782').Click()
            ui.ButtonControl(searchDepth=7, Name='매도(팔자)', AutomationId='3809').Click()
            ui_ui.SendKeys('{Enter}')
            ui_ui.SendKeys('{Enter}')
        except LookupError as e:
            log_ask_fail(ticker, self.usd, amt, bf_amt)
        else:
            self.usd += amt*cprice
            log_ask(ticker, self.usd, amt, cprice, bf_amt)
            tb_cntr.plus(trans_tb, 1)


    @staticmethod
    def order_amt(diff:float, cprice:int) -> int:
        diff = abs(diff)
        if (cprice==0) or (np.isnan(diff)) or (diff < cprice):
            return 1
        else:
            return int(diff // cprice)


    def adjust_pos(self, row):
        if (row['position'] in ('buy', 'sell'))\
            and (row['virtual_amt']==0):
            return 'neutral'
        return row['position']