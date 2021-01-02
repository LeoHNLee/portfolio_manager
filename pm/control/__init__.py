import pandas as pd
import numpy as np

from pm.log import log_usd


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


    def calc_current_amt_indi(self, row, stock_acnt):
        if row['cat0'] == 'CASH':
            return 1
        elif row['cat0'] == 'US':
            return row['current_amt']
        ret = stock_acnt[stock_acnt['종목명']==row['name']]['결제일잔고수량']
        if ret.shape[0] == 0:
            return 0
        return ret.values[0]


    def calc_current_val_indi(self, row, stock_acnt):
        if row['cat0'] != 'KR':
            return row['current_val']
        ret = stock_acnt[stock_acnt['종목명']==row['name']]['현재가']
        if ret.shape[0] == 0:
            return 0
        return ret.values[0]


    def set_total_acnt(self, total_acnt):
        krw = total_acnt[['현금증거금합계', '인출가능금액합계']].sum().sum()
        krw_idx = self[self['name']=='KRW'].index[0]
        self.loc[krw_idx, 'current_val'] = krw
        self.us_total = total_acnt['외화자산평가금액'].sum()


    def set_stock_acnt(self, stock_acnt):
        self['current_amt'] = self.apply(lambda x: self.calc_current_amt_indi(x, stock_acnt), axis=1)
        self['current_val'] = self.apply(lambda x: self.calc_current_val_indi(x, stock_acnt), axis=1)


    def calculate(self, tmp_df:pd.DataFrame):
        self['current_amt'] = self.apply(lambda x: self.calc_current_amt(x, tmp_df), axis=1)
        self['current_val'] = self.apply(lambda x: self.calc_current_val(x, tmp_df), axis=1)
        self['current_total'] = self.apply(self.calc_current_total, axis=1)
        self['virtual_total'] = self.apply(self.calc_virtual_total, axis=1)
        self['pivot_val'] = self['pivot_rate'] * self['current_val']

        if self.usd >= 0:
            pass
        elif self.us_total >= 0:
            us_stock_total = self[self['cat0']=='US']['current_total'].sum()
            self.usd = self.us_total - us_stock_total
        else:
            pass
        usd_idx = self[self['name']=='USD'].index[0]
        self.loc[usd_idx, 'current_val'] = self.usd
        total = self['current_total'].sum()
        self['target_total'] = self['target_rate'] * total
        self['target_diff'] = self['target_total'] - self['current_total']
        self['virtual_diff'] = self['virtual_total'] + self['target_diff']
        log_usd('CALCULATE', self.usd)


    def calc_current_amt(self, row, tmp_df:pd.DataFrame):
        if row['cat0'] != 'US':
            return row['current_amt']
        ret = tmp_df[tmp_df['종목번호']==row['name']]['주문가능']
        if ret.shape[0] == 0:
            return 0
        return ret.values[0]


    def calc_current_val(self, row, tmp_df:pd.DataFrame):
        if row['cat0'] != 'US':
            return row['current_val']
        ret = tmp_df[tmp_df['종목번호']==row['name']]['현재가']
        if ret.shape[0] == 0:
            return 0
        return ret.values[0]


    def calc_current_total(self, row):
        return row['current_amt'] * row['current_val']


    def calc_virtual_total(self, row):
        if row['position'] == 'out':
            return row['virtual_amt'] * row['virtual_val']
        elif row['position'] == 'sell':
            return row['virtual_amt'] * row['current_val']
        elif row['position'] == 'buy':
            return -1 * row['virtual_amt'] * row['current_val']
        else:
            return np.nan