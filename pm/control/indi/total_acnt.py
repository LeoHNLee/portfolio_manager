from pm.config import cfg
from pm.control.indi import IndiAPI
from pm.control.casting import str2int


class IndiTotalAcnt(IndiAPI):
    def req(self, manip):
        self.manip = manip
        return self.request(
            name='SABA655Q1',
            datas={
                0: cfg.ACNT_NO,
                1: '01',
                2: cfg.ACNT_PW,
            },
        )


    def receive(self, req_id:int=None):
        self.OK = True
        ret = self.rec_single_data({
            '순자산평가금액': 0,
            '주식평가금액': 3,
            '외화자산평가금액': 13,
            '현금증거금합계': 18,
            '인출가능금액합계':19,
        })
        for col in ret.columns:
            ret[col] = ret[col].apply(str2int)

        self.manip.set_total_acnt(ret)