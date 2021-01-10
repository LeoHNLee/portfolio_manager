import asyncio
from datetime import datetime as dt

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QMessageBox

from pm.config import cfg
from pm.log import log, log_err, log_order, log_bid_kr, log_bid_kr_fail, log_ask_kr, log_ask_kr_fail
from pm.control.indi import IndiAPI
from pm.control.casting import str2int, fstr2float


class IndiKRMarket(IndiAPI):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.ok = True
        self.trans = {}


    def login(self, origin, end_time, id:str=cfg.SH_ID, pw:str=cfg.SH_PW, cert_pw:str=cfg.CERT_PW, path:str=cfg.PATH_INDI):
        self.origin = origin
        self.end_time = end_time
        return self.indi.StartIndi(id, pw, cert_pw, path)


    def recieve_sys_msg(self, msg_id:int):
        if msg_id == 10:
            log('QUIT_INDI')
        elif msg_id == 11:
            log('START_INDI')
            asyncio.run(self.run())
        else:
            log(f'REC_MSG:{msg_id}')


    async def run(self):
        try:
            # while dt.now() < self.end_time:
                if self.ok:
                    await self.req()
                await asyncio.sleep(1)

        except Exception as e:
            log_err('AnyException', e)
            # QMessageBox.warning(
            #     self, 
            #     'Error!', 
            #     f'''AnyException!
            #     >>>{e}<<<''',
            # )
        log('KR_END')


    async def req(self):
        log('KR_REQ')
        self.ok = False
        return self.request(
            name='SABA655Q1',
            datas={
                0: cfg.ACNT_NO,
                1: '01',
                2: cfg.ACNT_PW,
            },
        )


    def rec_total_acnt(self, req_id=None):
        ret = self.rec_single_data({
            '순자산평가금액': 0,
            '주식평가금액': 3,
            '외화자산평가금액': 13,
            '현금증거금합계': 18,
            '인출가능금액합계':19,
        })
        for col in ret.columns:
            ret[col] = ret[col].apply(str2int)
        if self.origin is not None:
            self.origin.set_total_acnt(ret)
        log('INDI_TOTAL_ACNT')
        self.req_stock_acnt()


    def req_stock_acnt(self):
        return self.request(
            name='SABA200QB',
            datas={
                0: cfg.ACNT_NO,
                1: '01',
                2: cfg.ACNT_PW,
            },
        )

    def rec_stock_acnt(self, req_id=None):
        ret = self.rec_multi_data({
            '종목코드':0,
            '종목명':1,
            '결제일잔고수량':2,
            '현재가':5,
        })
        ret['결제일잔고수량'] = ret['결제일잔고수량'].apply(str2int)
        ret['현재가'] = ret['현재가'].apply(fstr2float)
        self.origin.set_stock_acnt(ret)
        log('INDI_STOCK_ACNT')

        self.origin.calculate()
        self.origin['virtual_amt'] -= self.origin.apply(self.order, axis=1)
        self.origin.save()


    def order(self, row):
        ticker = row['name']
        cat = row['cat0']
        pos = row['position']
        bf_amt = row['current_amt']
        t_diff = row['target_diff']
        v_diff = row['virtual_diff']
        pivot = row['pivot_val']
        cprice = row['current_val']
        v_amt = self.origin.order_amt(v_diff, cprice)
        t_amt = self.origin.order_amt(t_diff, cprice)

        if cat!='US':
            pass

        elif pos == 'neutral':
            if t_diff < -pivot:
                self.req_ask(ticker, t_amt, cprice)
            elif t_diff > pivot:
                self.req_bid(ticker, t_amt, cprice)

        elif pos == 'buy':
            if v_diff < -pivot:
                log_order('VIRTUAL_ASK', ticker, -1, exec_amt=v_amt, pivot=pivot, diff=v_diff)
                return v_amt
            elif v_diff > pivot:
                self.req_bid(ticker, v_amt, cprice)

        elif pos in ('sell', 'out'):
            if v_diff < -pivot:
                self.req_ask(ticker, v_amt, cprice)
            elif v_diff > pivot:
                log_order('VIRTUAL_BID', ticker, -1, exec_amt=v_amt, pivot=pivot, diff=v_diff)
                return v_amt

        elif pos == 'in':
            self.req_bid(ticker, 1, 0)
        return 0


    def req_bid(self, ticker:str, amt:int, cprice:int):
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
            'type':'bid',
            'ticker':ticker,
            'amt':amt,
            'cprice':cprice,
        }


    def req_ask(self, ticker:str, amt:int, cprice:int):
        req_id = self.request(
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
        self.trans[req_id] = {
            'type':'ask',
            'ticker':ticker,
            'amt':amt,
            'cprice':cprice,
        }


    def rec_order(self, req_id):
        ret = self.rec_single_data({
            'order_id':0, # 에러시 0
            'total_val':3,
            'cost':4,
            'tax':5, # 매도시 가계산제세금 | 매수 에러시 주문가능금액
        })
        inputs = self.trans[req_id]
        if inputs['type'] == 'bid':
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

        elif inputs['type'] == 'ask':
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