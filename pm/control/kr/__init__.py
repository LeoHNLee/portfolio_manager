import time
from datetime import datetime as dt
from datetime import timedelta as td
import pandas as pd
import numpy as np

from pm.config import cfg
from pm.log import dt2log, log, log_err, log_bid_kr, log_ask_kr, log_bid_kr_fail, log_ask_kr_fail, log_backup, log_save
from pm.control import Controller
from pm.control.indi import IndiAPI
from pm.control.casting import fstr2int, to_win_path, str2int


class KRCntr(Controller, IndiAPI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trans = {}


    @staticmethod
    def from_df(df):
        return KRCntr(df.values, columns=df.columns, index=df.index)


    @staticmethod
    def read_csv(*args, **kwargs):
        df = pd.read_csv(*args, **kwargs)
        return KRCntr.from_df(df)


    def run(
        self, start_time:dt=None, end_time:dt=None,
    ):
        log('RUN_KOR_CONTROLLER')
        if start_time is None:
            start_time=dt.now()
        if end_time is None:
            end_time=start_time+td(minutes=1)
        while dt.now() < start_time:
            log('WAIT UNTIL OPEN MARCKET')
            time.sleep(60)

        self.ok = True
        while dt.now() < end_time:
            if not self.ok:
                continue
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


    def bid(self, ticker:str, amt:int, cprice:int, bf_amt):
        if self.usd < cprice*2:
            return log_bid_fail(ticker, self.usd, cprice)

        req_id = self.request(
            name='SABA101U1',
            datas={
                0: cfg.ACNT_NO, # 계좌번호 11자리
                1: '01', # 상품구분
                2: cfg.ACNT_PW, # 계좌비밀번호
                6: '00', # 신용거래구구분
                7: '2', # 매도매수구분
                8: ticker, # 종목코드
                9: str(amt), # 주문수량
                10: str(cprice), # 주문가격
                11: '1', # 정규시간외구분코드
                12: 'X', # 호가유형코드
                13: 'IOC', # 주문조건코드
                14: '0', # 신용대출통합구분코드
                21: 'Y', # 결과메세지처리여부
            },
        )
        self.trans[req_id] = {
            'ticker':ticker,
            'amt':amt,
            'cprice':cprice,
        }


    def rec_bid(self, req_id):
        ret = self.rec_single_data({
            'order_id':0, # 에러시 0
            'total_val':3,
            'cost':4,
            'tax':5, # 매도시 가계산제세금 | 매수 에러시 주문가능금액
        })
        inputs = self.trans[req_id]
        if ret.loc[0, 'order_id'] == '0':
            log_bid_kr_fail(
                inputs['ticker'], inputs['amt'], inputs['cprice'],
                ret.loc[0, 'order_id'], ret.loc[0, 'total_val'], ret.loc[0, 'cost'],
            )
        else:
            log_bid_kr(
                inputs['ticker'], inputs['amt'], inputs['cprice'],
                ret.loc[0, 'order_id'], ret.loc[0, 'total_val'], ret.loc[0, 'cost'],
            )
        del self.trans[req_id]


    def ask(self, ticker:str, amt:int, cprice:int, bf_amt:int):
        if bf_amt < amt:
            return log_ask_fail(ticker, self.usd, amt, bf_amt)

        log_ask(ticker, self.usd, amt, cprice, bf_amt)
        return self.request(
            name='SABA101U1',
            datas={
                0: cfg.ACNT_NO, # 계좌번호 11자리
                1: '01', # 상품구분
                2: cfg.ACNT_PW, # 계좌비밀번호
                6: '00', # 신용거래구구분
                7: '1', # 매도매수구분
                8: ticker, # 종목코드
                9: str(amt), # 주문수량
                10: str(cprice), # 주문가격
                11: '1', # 정규시간외구분코드
                12: 'X', # 호가유형코드
                13: 'IOC', # 주문조건코드
                14: '0', # 신용대출통합구분코드
                21: 'Y', # 결과메세지처리여부
            },
        )


    def rec_ask(self, req_id):
        ret = self.rec_single_data({
            'order_id':0, # 에러시 0
            'total_val':3,
            'cost':4,
            'tax':5, # 매도시 가계산제세금 | 매수 에러시 주문가능금액
        })
        inputs = self.trans[req_id]
        if ret.loc[0, 'order_id'] == '0':
            log_ask_kr_fail(
                inputs['ticker'], inputs['amt'], inputs['cprice'],
                ret.loc[0, 'order_id'], ret.loc[0, 'total_val'], ret.loc[0, 'cost'], ret.loc[0, 'tax'],
            )
        else:
            log_ask_kr(
                inputs['ticker'], inputs['amt'], inputs['cprice'],
                ret.loc[0, 'order_id'], ret.loc[0, 'total_val'], ret.loc[0, 'cost'], ret.loc[0, 'tax'],
            )
        del self.trans[req_id]