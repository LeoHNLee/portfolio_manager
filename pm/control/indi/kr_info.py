from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from pm.config import cfg
from pm.log import log
from pm.control.indi import IndiAPI
from pm.control.casting import str2int, fstr2float
from pm.control.view import pbar_cntr


class IndiKRInfo(IndiAPI):
    def req(self, origin=None, pbar=None, status_tb=None):
        self.pbar = pbar
        self.origin = origin
        self.status_tb = status_tb
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
        if self.origin is not None:
            self.origin.set_total_acnt(ret)
        if self.pbar is not None:
            pbar_cntr.plus(self.pbar, 50)
        log('INDI_TOTAL_ACNT')
        self.__req_stock__()


    def rec_stock_acnt(self):
        ret = self.rec_multi_data({
            '종목명':1,
            '결제일잔고수량':2,
            '현재가':5,
        })
        ret['결제일잔고수량'] = ret['결제일잔고수량'].apply(str2int)
        ret['현재가'] = ret['현재가'].apply(fstr2float)
        if self.origin is not None:
            self.origin.set_stock_acnt(ret)
            self.origin.save()
        if self.pbar is not None:
            pbar_cntr.plus(self.pbar, 50)
        if self.status_tb is not None:
            self.status_tb.setTextColor(QColor(0, 255, 0, 255))
            self.status_tb.setPlainText('Indi Info Updated!!')
            self.status_tb.setAlignment(Qt.AlignCenter)
        log('INDI_STOCK_ACNT')