import pandas as pd
import numpy as np


def current_amt(name:str, tmp_df:pd.DataFrame):
    if name in ('KRW', 'USD'):
        return 1
    ret = tmp_df[tmp_df['종목번호']==name]['주문가능']
    if ret.shape[0] == 0:
        return 0
    return ret.values[0]


def current_val(row, tmp_df:pd.DataFrame):
    if row['name'] in ('KRW', 'USD'):
        return row['current_val']
    ret = tmp_df[tmp_df['종목번호']==row['name']]['현재가']
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

    if row['position'] == 'out':
        return row['virtual_amt'] * row['virtual_val']
    elif row['position'] == 'sell':
        return row['virtual_amt'] * row['current_val']
    elif row['position'] == 'buy':
        return -1 * row['virtual_amt'] * row['current_val']
    else:
        return 0


def calc_current(origin_df:pd.DataFrame, tmp_df:pd.DataFrame, usd:int):
    # input usd
    origin_df['current_amt'] = origin_df['name'].apply(lambda x: current_amt(x, tmp_df))
    origin_df['current_val'] = origin_df.apply(lambda x: current_val(x, tmp_df))
    origin_df['current_total'] = origin_df.apply(current_total, axis=1)
    origin_df['virtual_total'] = origin_df.apply(virtual_total, axis=1)
    origin_df['pivot_val'] = origin_df['pivot_rate'] * origin_df['current_val']

    total = origin['current_total'].sum()
    origin_df['target_total'] = origin_df['target_rate'] * total
    origin_df['target_diff'] = origin_df['target_total'] - origin_df['current_total']
    origin_df['virtual_diff'] = origin_df['virtual_total'] + origin_df['target_diff']
    return origin_df