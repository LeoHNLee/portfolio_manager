from pm.config import cfg
from pm.control.indi import IndiAPI
from pm.control.casting import str2int, fstr2float


class IndiKRInfo(IndiAPI):
    def req(self, manip=None, pb=None, backup=False):
        self.pb = pb
        self.manip = manip
        self.backup = backup
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
        if self.manip is not None:
            self.manip.set_total_acnt(ret)
        if self.pb is not None:
            new_val = self.pb.value() + 50
            self.pb.setValue(new_val)
        self.__req_stock__()


    def rec_stock_acnt(self):
        ret = self.rec_multi_data({
            '종목명':1,
            '결제일잔고수량':2,
            '현재가':5,
        })
        ret['결제일잔고수량'] = ret['결제일잔고수량'].apply(str2int)
        ret['현재가'] = ret['현재가'].apply(fstr2float)
        if self.manip is not None:
            self.manip.set_stock_acnt(ret)
        if self.backup:
            self.manip.backup()
        if self.pb is not None:
            new_val = self.pb.value() + 50
            self.pb.setValue(new_val)