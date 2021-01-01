from pm.config import cfg
from pm.control.indi import IndiAPI
from pm.control.casting import str2int, fstr2float


class IndiStockAcnt(IndiAPI):
    def req(self, manip):
        self.manip = manip
        return self.request(
            name='SABA200QB',
            datas={
                0: cfg.ACNT_NO,
                1: '01',
                2: cfg.ACNT_PW,
            },
        )


    def receive(self, req_id:int=None):
        self.OK = True
        ret = self.rec_multi_data({
            '종목명':1,
            '결제일잔고수량':2,
            '현재가':5,
        })
        ret['결제일잔고수량'] = ret['결제일잔고수량'].apply(str2int)
        ret['현재가'] = ret['현재가'].apply(fstr2float)
        self.manip.set_stock_acnt(ret)