import time
from datetime import datetime as dt
from datetime import timedelta as td
import pandas as pd
import numpy as np

from pm.config import cfg
from pm.log import dt2log, log, log_err, log_order, log_bid, log_ask, log_bid_fail, log_ask_fail, log_backup, log_save
from pm.control import Controller
from pm.control.indi.kr_market import IndiKRMarket
from pm.control.indi.kr_info import IndiKRInfo
from pm.control.casting import fstr2int, to_win_path, str2int
from pm.control.view import pbar_cntr, tb_cntr


class KoCntr(Controller, IndiAPI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    @staticmethod
    def from_df(df):
        return KoCntr(df.values, columns=df.columns, index=df.index)


    @staticmethod
    def read_csv(*args, **kwargs):
        df = pd.read_csv(*args, **kwargs)
        return KoCntr.from_df(df)


    def run(
        self, start_time:dt=None, end_time:dt=None,
        pbar=None, iter_tb=None, trans_tb=None,
    ):
        log('RUN_KOR_CONTROLLER')
        if start_time is None:
            start_time=dt.now()
        if end_time is None:
            end_time=start_time+td(minutes=1)

        self.login()
        self.ok = True

        while dt.now() < start_time:
            log('WAIT UNTIL OPEN MARCKET')
            time.sleep(60)

        while dt.now() < end_time:
            if not self.ok:
                continue
            if pbar is not None:
                pbar_cntr.timer(pbar, start_time, end_time)
            if iter_tb is not None:
                tb_cntr.plus(iter_tb, 1)
            self.__total_acnt()


    def __total_acnt(self):
        self.ok = False
        return self.request(
            name='SABA655Q1',
            datas={
                0: cfg.ACNT_NO,
                1: '01',
                2: cfg.ACNT_PW,
            },
        )


    def rec_total_acnt(self):
        ret = self.rec_single_data({
            '순자산평가금액': 0,
            '주식평가금액': 3,
            '외화자산평가금액': 13,
            '현금증거금합계': 18,
            '인출가능금액합계':19,
        })
        for col in ret.columns:
            ret[col] = ret[col].apply(str2int)

        krw = total_acnt[['현금증거금합계', '인출가능금액합계']].sum().sum()
        krw_idx = self[self['name']=='KRW'].index[0]
        self.loc[krw_idx, 'current_val'] = krw

        self.us_total = total_acnt['외화자산평가금액'].sum()
        self.us_stock = self[self['cat0']=='US'].sum().sum()
        usd_idx = self[self['name']=='USD'].index[0]
        self.loc[usd_idx, 'current_val'] = self.us_total-self.us_stock

        log('INDI_TOTAL_ACNT')
        self.__stock_acnt()


    def __stock_acnt(self):
        return self.request(
            name='SABA200QB',
            datas={
                0: cfg.ACNT_NO,
                1: '01',
                2: cfg.ACNT_PW,
            },
        )


    def rec_stock_acnt(self):
        ret = self.rec_multi_data({
            '종목코드':0,
            '종목명':1,
            '결제일잔고수량':2,
            '현재가':5,
        })
        ret['결제일잔고수량'] = ret['결제일잔고수량'].apply(str2int)
        ret['현재가'] = ret['현재가'].apply(fstr2float)
        self.set_stock_acnt(ret)
        log('INDI_STOCK_ACNT')
        self.calculate()
        self['position'] = self.apply(self.adjust_pos, axis=1)
        self['pivot_rate'] = self.apply(self.adjust_threshold, axis=1)
        self['virtual_amt'] -= self.apply(self.order, axis=1)
        self.save()
        self.ok = True


    def calculate(self):
        self['current_total'] = self['current_amt'] * self['current_val']
        self['virtual_total'] = self.apply(self.calc_virtual_total, axis=1)
        self['pivot_val'] = self.apply(self.calc_pivot_val, axis=1)

        total = self['current_total'].sum()
        self['target_total'] = self['target_rate'] * total
        self['target_diff'] = self['target_total'] - self['current_total']
        self['virtual_diff'] = self['virtual_total'] + self['target_diff']
        log('CALCULATE')


    def bid(self, ticker:str, amt:int, cprice:int, bf_amt, trans_tb):
        if self.usd < cprice*2:
            return log_bid_fail(ticker, self.usd, cprice)

        log_bid(ticker, self.usd, amt, cprice, bf_amt)
        tb_cntr.plus(trans_tb, amt)


    def ask(self, ticker:str, amt:int, cprice:int, bf_amt:int, trans_tb):
        if bf_amt < amt:
            return log_ask_fail(ticker, self.usd, amt, bf_amt)

        log_ask(ticker, self.usd, amt, cprice, bf_amt)
        tb_cntr.plus(trans_tb, amt)