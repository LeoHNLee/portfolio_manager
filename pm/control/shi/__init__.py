import time
import subprocess
from datetime import datetime as dt
from datetime import timedelta as td
import uiautomation as ui
from uiautomation import uiautomation as ui_ui
from _ctypes import COMError
import pandas as pd

from pm.config import cfg
from pm.log import log, log_usd, log_err, log_bid, log_ask, log_bid_fail, log_ask_fail
from pm.control import Controller
from pm.control.casting import fstr2int, to_win_path


class SHI(Controller):
    @staticmethod
    def from_df(df):
        return SHI(df.values, columns=df.columns, index=df.index)


    @staticmethod
    def read_csv(*args, **kwargs):
        df = pd.read_csv(*args, **kwargs)
        return SHI.from_df(df)


    @staticmethod
    def open(path:str=cfg.PATH_SHI):
        subprocess.Popen(path)
        log('SHI_OPEN')


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
        log('SHI_POPUP')


    @staticmethod
    def quit():
        quit = ui.ButtonControl(searchDepth=4, AutomationId='1358')
        quit.SetFocus()
        quit.Click()
        ok = ui.ButtonControl(searchDepth=4, Name='신한아이 종료', AutomationId='3787')
        ok.SetFocus()
        ok.Click()
        log('SHI_QUIT')


    def run(
        self, start_time:dt=None, end_time:dt=None,
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
            ok = self.calculate(tmp_df=tmp_df)
            if not ok:
                continue
            self['position'] = self.apply(self.adjust_pos, axis=1)
            self['pivot_rate'] = self.apply(self.adjust_threshold, axis=1)
            self['virtual_amt'] -= self.apply(self.order, axis=1)
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
        ui.ButtonControl(searchDepth=5, Name='원화기준').Click()
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


    def calculate(self, tmp_df:pd.DataFrame):
        self['current_amt'] = self.apply(lambda x: self.calc_current_amt(x, tmp_df), axis=1)
        self['current_val'] = self.apply(lambda x: self.calc_current_val(x, tmp_df), axis=1)
        self['current_total'] = self['current_amt'] * self['current_val']
        self['virtual_total'] = self.apply(self.calc_virtual_total, axis=1)
        self['pivot_val'] = self.apply(self.calc_pivot_val, axis=1)

        if self.usd >= 0:
            pass
        elif self.us_total >= 0:
            us_stock_total = self[self['cat0']=='US']['current_total'].sum()
            self.usd = self.us_total - us_stock_total
        else:
            pass
        usd_idx = self[self['name']=='USD'].index[0]
        self.loc[usd_idx, 'current_val'] = self.usd
        self.loc[usd_idx, 'current_total'] = self.usd
        total = self['current_total'].sum()
        self['target_total'] = self['target_rate'] * total
        self['target_diff'] = self['target_total'] - self['current_total']
        self['virtual_diff'] = self['virtual_total'] + self['target_diff']
        log_usd('CALCULATE', self.usd)
        return True


    def bid(self, ticker:str, amt:int, cprice:int, bf_amt):
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


    def ask(self, ticker:str, amt:int, cprice:int, bf_amt:int):
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