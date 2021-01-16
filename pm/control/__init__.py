import time
from datetime import datetime as dt
import pandas as pd
import numpy as np

from pm.config import cfg
from pm.log import dt2log, log_save, log_backup, log_order
from pm.control.casting import to_win_path


class Controller(pd.DataFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.usd = -1
        self.us_total = -1


    @staticmethod
    def from_df(df):
        return Controller(df.values, columns=df.columns, index=df.index)


    @staticmethod
    def read_csv(*args, **kwargs):
        df = pd.read_csv(*args, **kwargs)
        return self.from_df(df)


    def save(self, root_path=cfg.PATH_ROOT, dir_path=cfg.PATH_DATA, fn=cfg.PATH_ORIGIN):
        file_path = to_win_path(root_path, dir_path, fn)
        self.to_csv(file_path, index=False, encoding='cp949')
        log_save(file_path)


    def backup(self, root_path=cfg.PATH_ROOT, dir_path=cfg.PATH_DATA):
        file_path = to_win_path(root_path, dir_path, f'backup/{dt2log(dt.now())}.csv')
        self.to_csv(file_path, index=False, encoding='cp949')
        log_backup(file_path)


    def calc_current_amt_indi(self, row, stock_acnt):
        if row['cat0'] == 'CASH':
            return 1
        elif row['cat0'] == 'US':
            return row['current_amt']
        ret = stock_acnt[stock_acnt['종목코드']==row['name']]['결제일잔고수량']
        if ret.shape[0] == 0:
            return row['current_amt']
        return ret.values[0]


    def calc_current_val_indi(self, row, stock_acnt):
        if row['cat0'] != 'KR':
            return row['current_val']
        ret = stock_acnt[stock_acnt['종목코드']==row['name']]['현재가']
        if ret.shape[0] == 0:
            return row['current_val']
        return ret.values[0]


    def set_total_acnt(self, total_acnt):
        krw = total_acnt[['현금증거금합계', '인출가능금액합계', '예수금합계']].sum().sum()
        krw_idx = self[self['name']=='KRW'].index[0]
        self.loc[krw_idx, 'current_val'] = krw
        self.us_total = total_acnt['외화자산평가금액'].sum()
        self.us_stock = self[self['cat0']=='US']['current_total'].sum()
        usd_idx = self[self['name']=='USD'].index[0]
        self.loc[usd_idx, 'current_val'] = self.us_total-self.us_stock


    def set_stock_acnt(self, stock_acnt):
        self['current_amt'] = self.apply(lambda x: self.calc_current_amt_indi(x, stock_acnt), axis=1)
        self['current_val'] = self.apply(lambda x: self.calc_current_val_indi(x, stock_acnt), axis=1)


    def calculate(self, *args, **kwargs):
        raise NotImplementedError('calculate')


    def calc_current_amt(self, row, tmp_df:pd.DataFrame):
        if row['cat0'] != 'US':
            return row['current_amt']
        ret = tmp_df[tmp_df['종목번호']==row['name']]['주문가능']
        if ret.shape[0] == 0:
            return row['current_amt']
        return ret.values[0]


    def calc_current_val(self, row, tmp_df:pd.DataFrame):
        if row['cat0'] != 'US':
            return row['current_val']
        ret = tmp_df[tmp_df['종목번호']==row['name']]['현재가']
        if ret.shape[0] == 0:
            return row['current_amt']
        return ret.values[0]


    def calc_virtual_total(self, row):
        if row['position'] == 'out':
            return row['virtual_amt'] * row['virtual_val']
        elif row['position'] == 'sell':
            return row['virtual_amt'] * row['current_val']
        elif row['position'] == 'buy':
            return -1 * row['virtual_amt'] * row['current_val']
        else:
            return np.nan


    def calc_pivot_val(self, row):
        normal = row['pivot_rate'] * row['current_val']
        many = row['current_total'] * 0.015
        if (row['current_val'] * (2*row['pivot_rate']-1)) < many:
            return many
        else:
            return normal


    def order(self, row) -> int:
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
                self.ask(ticker, t_amt, cprice, bf_amt)
            elif t_diff > pivot:
                self.bid(ticker, t_amt, cprice, bf_amt)

        elif pos == 'buy':
            if v_diff < -pivot:
                log_order('VIRTUAL_ASK', ticker, self.usd, exec_amt=v_amt, pivot=pivot, diff=v_diff)
                return v_amt
            elif v_diff > pivot:
                self.bid(ticker, v_amt, cprice, bf_amt)

        elif pos in ('sell', 'out'):
            if v_diff < -pivot:
                self.ask(ticker, v_amt, cprice, bf_amt)
            elif v_diff > pivot:
                log_order('VIRTUAL_BID', ticker, self.usd, exec_amt=v_amt, pivot=pivot, diff=v_diff)
                return v_amt

        elif pos == 'in':
            self.bid(ticker, 1, 0, 0)

        return 0


    def bid(self, *args, **kwargs):
        raise NotImplementedError('bid')


    def ask(self, *args, **kwargs):
        raise NotImplementedError('ask')


    def order_amt(self, diff:float, cprice:int) -> int:
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