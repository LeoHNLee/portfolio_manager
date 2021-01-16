from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from pm.config import cfg
from pm.log import log
from pm.control.indi import IndiAPI
from pm.control.shi import SHI
from pm.control.casting import str2int, fstr2float


class IndiKRInfo(IndiAPI):
    def login(self, view, id:str=cfg.SH_ID, pw:str=cfg.SH_PW, cert_pw:str=cfg.CERT_PW, path:str=cfg.PATH_INDI):
        self.view = view
        return self.indi.StartIndi(id, pw, cert_pw, path)


    def recieve_sys_msg(self, msg_id:int):
        if msg_id == 10:
            log('QUIT_INDI')
            SHI.open()
        elif msg_id == 11:
            log('START_INDI')
            self.view.api_origin_get()
            self.quit()
        else:
            log(f'REC_MSG:{msg_id}')


    def req(self, origin=None):
        self.origin = origin
        return self.request(
            name='SABA655Q1',
            datas={
                0: cfg.ACNT_NO,
                1: '01',
                2: cfg.ACNT_PW,
            },
        )


    def __req_stock__(self):
        return self.request(
            name='SABA200QB',
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
            '예수금합계':17,
            '현금증거금합계': 18,
            '인출가능금액합계':19,
        })
        for col in ret.columns:
            ret[col] = ret[col].apply(str2int)
        self.origin.set_total_acnt(ret)
        self.origin.save()
        log('INDI_TOTAL_ACNT')
        # self.__req_stock__()


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
        self.origin.save()
        log('INDI_STOCK_ACNT')