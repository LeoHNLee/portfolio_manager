import pandas as pd
import numpy as np


def current_amt(name:str, tmp_df:pd.DataFrame):
    ret = tmp_df[tmp_df['종목번호']==name]['주문가능']
    if ret.shape[0] == 0:
        return 0
    return ret.values[0]


def current_val(name:str, tmp_df:pd.DataFrame):
    ret = tmp_df[tmp_df['종목번호']==name]['현재가']
    if ret.shape[0] == 0:
        return 0
    return ret.values[0]


def current_total(row):
    if np.isnan(row['current_amt']):
        return 0
    return row['current_amt'] * row['current_val']


def virtual_total(row):
    if np.isnan(row['virtual_amt']):
        return 0
    return row['virtual_amt'] * row['current_val']


def calc_row(origin_df:pd.DataFrame, tmp_df:pd.DataFrame):
    origin_df['current_amt'] = origin_df['name'].apply(lambda x: current_amt(x, tmp_df))
    origin_df['current_val'] = origin_df['name'].apply(lambda x: current_val(x, tmp_df))
    origin_df['current_total'] = origin_df.apply(current_total, axis=1)
    origin_df['virtual_total'] = origin_df.apply(virtual_total, axis=1)
    return origin_df


def calc_total(origin_df:pd.DataFrame):
    # calc target_val
    # calc diff_val
    # calc trans_val
    pass