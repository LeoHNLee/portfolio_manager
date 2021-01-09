import time
import subprocess
from datetime import datetime as dt
from datetime import timedelta as td
import uiautomation as ui
from uiautomation import uiautomation as ui_ui
from _ctypes import COMError
import pandas as pd
import numpy as np

from pm.config import cfg
from pm.log import dt2log, log, log_err, log_order, log_bid, log_ask, log_bid_fail, log_ask_fail, log_backup, log_save
from pm.control import Controller
from pm.control.casting import fstr2int, to_win_path
from pm.control.view import pbar_cntr, tb_cntr


class SHI(Controller):
    @staticmethod
    def from_df(df):
        return SHI(df.values, columns=df.columns, index=df.index)


    @staticmethod
    def read_csv(*args, **kwargs):
        df = pd.read_csv(*args, **kwargs)
        return SHI.from_df(df)


    def save(self, root_path=cfg.PATH_ROOT, dir_path=cfg.PATH_DATA, fn=cfg.PATH_ORIGIN):
        file_path = to_win_path(root_path, dir_path, fn)
        self.to_csv(file_path, index=False, encoding='cp949')
        log_save(file_path)


    def backup(self, root_path=cfg.PATH_ROOT, dir_path=cfg.PATH_DATA):
        file_path = to_win_path(root_path, dir_path, f'backup/{dt2log(dt.now())}.csv')
        self.to_csv(file_path, index=False, encoding='cp949')
        log_backup(file_path)


    @staticmethod
    def open(path:str=cfg.PATH_SHI):
        subprocess.Popen(path)


    @staticmethod
    def popup():
        menu = ui.EditControl(searchDepth=6, AutomationId='1001')
        menu.SetFocus()
        time.sleep(1)
        menu.SendKeys('3651') # order
        time.sleep(1)
        menu.SendKeys('3805') # fr acnt
        time.sleep(1)
        menu.SendKeys('3754') # mini order
        time.sleep(1)
        ui.PaneControl(searchDepth=5, ClassName='GXWND', AutomationId='3779').SetFocus()
        time.sleep(1)
        ui.ButtonControl(searchDepth=5, Name='원화기준').Click()
        time.sleep(1)
        ui.WindowControl(searchDepth=2, Name='(3651)주식주문(미국/홍콩/후강퉁/선강퉁)').SetFocus()
        time.sleep(1)
        ui.ButtonControl(searchDepth=4, Name='미국', AutomationId='3775').Click()
        time.sleep(1)
        ui.WindowControl(searchDepth=2, Name='(3754)미니주문(미국)').SetFocus()


    @staticmethod
    def quit():
        quit = ui.ButtonControl(searchDepth=4, AutomationId='1358')
        quit.SetFocus()
        quit.Click()
        ok = ui.ButtonControl(searchDepth=4, Name='신한아이 종료', AutomationId='3787')
        ok.SetFocus()
        ok.Click()


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
                except (LookupError, COMError) as e:
                    n_try += 1
                    log_err('LooupError', e)
                    if n_try >= 10:
                        raise LookupError(str(e))
                    ui_ui.SendKeys('{Escape}')
                    ui_ui.SendKeys('{Enter}')
                else:
                    break
            self.calculate(tmp_df=tmp_df)
            self['position'] = self.apply(self.adjust_pos, axis=1)
            self['pivot_rate'] = self.apply(self.adjust_threshold, axis=1)
            self['virtual_amt'] -= self.apply(lambda row: self.order(row, trans_tb), axis=1)
            self.save()


    @staticmethod
    def get_flow(
        root_path:str=cfg.PATH_ROOT,
        dir_path:str=cfg.PATH_DATA, 
        fn:str='tmp.csv',
    ):
        file_path = to_win_path(root_path, dir_path, fn)
        rt = ui.PaneControl(searchDepth=5, ClassName='GXWND', AutomationId='3779')
        rt.SetFocus()
        time.sleep(1)
        ui.ButtonControl(searchDepth=4, Name='조 회', AutomationId='3813').Click()
        time.sleep(1)
        rt.RightClick()
        time.sleep(1)
        ui.MenuItemControl(searchDepth=3, Name='엑셀로 내보내기').Click()
        time.sleep(1)
        ui.MenuItemControl(searchDepth=4, Name='CSV').Click()
        time.sleep(1)
        ui.EditControl(searchDepth=6, Name='파일 이름(N):').SendKeys(file_path+'{Enter}')
        time.sleep(1)
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

        elif pos == 'in':
            self.bid(ticker, 1, 0, 0, trans_tb)

        return 0


    def bid(self, ticker:str, amt:int, cprice:int, bf_amt, trans_tb):
        if self.usd < cprice*2:
            return log_bid_fail(ticker, self.usd, cprice)

        try:
            ui.WindowControl(searchDepth=2, Name='(3754)미니주문(미국)').SetFocus()
            time.sleep(1)
            ui.EditControl(searchDepth=5, AutomationId='3810').SendKeys(ticker+'{Enter}')
            time.sleep(1)
            ui.EditControl(searchDepth=5, AutomationId='3809').SendKeys(str(amt)+'{Enter}')
            time.sleep(1)
            ui.ButtonControl(searchDepth=5, Name='매도1', AutomationId='3782').Click()
            time.sleep(1)
            ui.ButtonControl(searchDepth=5, Name='매수', AutomationId='3807').Click()
            time.sleep(1)
            ui_ui.SendKeys('{Enter}')
            time.sleep(1)
            ui_ui.SendKeys('{Enter}')
        except (LookupError, COMError) as e:
            log_bid_fail(ticker, self.usd, cprice)
        else:
            self.usd -= amt*cprice
            log_bid(ticker, self.usd, amt, cprice, bf_amt)
            tb_cntr.plus(trans_tb, amt)


    def ask(self, ticker:str, amt:int, cprice:int, bf_amt:int, trans_tb):
        if bf_amt < amt:
            return log_ask_fail(ticker, self.usd, amt, bf_amt)

        try:
            ui.WindowControl(searchDepth=2, Name='(3651)주식주문(미국/홍콩/후강퉁/선강퉁)').SetFocus()
            time.sleep(1)
            ui.EditControl(searchDepth=7, AutomationId='3812').SendKeys(ticker+'{Enter}')
            time.sleep(1)
            ui.EditControl(searchDepth=7, AutomationId='3811').SendKeys(str(amt)+'{Enter}')
            time.sleep(1)
            ui.ButtonControl(searchDepth=7, Name='매수1', AutomationId='3782').Click()
            time.sleep(1)
            ui.ButtonControl(searchDepth=7, Name='매도(팔자)', AutomationId='3809').Click()
            time.sleep(1)
            ui_ui.SendKeys('{Enter}')
            time.sleep(1)
            ui_ui.SendKeys('{Enter}')
        except (LookupError, COMError) as e:
            log_ask_fail(ticker, self.usd, amt, bf_amt)
        else:
            self.usd += amt*cprice
            log_ask(ticker, self.usd, amt, cprice, bf_amt)
            tb_cntr.plus(trans_tb, amt)


    @staticmethod
    def order_amt(diff:float, cprice:int) -> int:
        diff = abs(diff)
        if (cprice==0) or (np.isnan(diff)) or (diff < cprice):
            return 1
        else:
            return int(diff // cprice)


    def adjust_pos(self, row):
        if (
            row['position'] != 'neutral'
            and row['virtual_amt']<1
        ):
            return 'neutral'
        elif (
            row['position'] == 'in'
            and row['current_amt'] > 0
        ):
            return 'buy'
        return row['position']


    def adjust_threshold(self, row):
        if (row['position'] == 'neutral')\
            and (row['pivot_rate'] < 0.8):
            return 0.8
        return row['pivot_rate']