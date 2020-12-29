import pandas as pd
import numpy as np


class CurrentDF(pd.DataFrame):
    @staticmethod
    def read_csv(*args, **kwargs):
        df = pd.read_csv(*args, **kwargs)
        return CurrentDF(df.values, columns=df.columns, index=df.index)


    def calculate(self, tmp_df:pd.DataFrame, usd:int=0, krw:int=0):
        # input usd, krw

        self['current_amt'] = self['name'].apply(lambda x: self.__calc_current_amt__(x, tmp_df))
        self['current_val'] = self.apply(lambda x: self.__calc_current_val__(x, tmp_df), axis=1)
        self['current_total'] = self.apply(self.__calc_current_total__, axis=1)
        self['virtual_total'] = self.apply(self.__calc_virtual_total__, axis=1)
        self['pivot_val'] = self['pivot_rate'] * self['current_val']

        total = self['current_total'].sum()
        self['target_total'] = self['target_rate'] * total
        self['target_diff'] = self['target_total'] - self['current_total']
        self['virtual_diff'] = self['virtual_total'] + self['target_diff']


    @staticmethod
    def __calc_current_amt__(name:str, tmp_df:pd.DataFrame):
        if name in ('KRW', 'USD'):
            return 1
        ret = tmp_df[tmp_df['종목번호']==name]['주문가능']
        if ret.shape[0] == 0:
            return 0
        return ret.values[0]


    @staticmethod
    def __calc_current_val__(row, tmp_df:pd.DataFrame):
        if row['name'] in ('KRW', 'USD'):
            return row['virtual_val']
        ret = tmp_df[tmp_df['종목번호']==row['name']]['현재가']
        if ret.shape[0] == 0:
            return 0
        return ret.values[0]


    @staticmethod
    def __calc_current_total__(row):
        if np.isnan(row['current_amt']):
            return 0
        return row['current_amt'] * row['current_val']


    @staticmethod
    def __calc_virtual_total__(row):
        if np.isnan(row['virtual_amt']):
            return 0

        if row['position'] == 'out':
            return row['virtual_amt'] * row['virtual_val']
        elif row['position'] == 'sell':
            return row['virtual_amt'] * row['current_val']
        elif row['position'] == 'buy':
            return -1 * row['virtual_amt'] * row['current_val']
        else:
            return 0