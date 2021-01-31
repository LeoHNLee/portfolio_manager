from pandas import DataFrame
from PyQt5.QAxContainer import *

from pm.config import cfg


class IndiAPI(object):
    def __init__(self):
        self.indi = QAxWidget("GIEXPERTCONTROL.GiExpertControlCtrl.1")
        self.indi.ReceiveData.connect(self.receive)
        self.indi.ReceiveSysMsg.connect(self.recieve_sys_msg)

        self.req_ids = {}
        self.rec_funcs = {
            "SABA655Q1": self.rec_total_acnt,
            "SABA200QB": self.rec_stock_acnt,
            "SABA101U1": self.rec_order,
        }

    def login(
        self,
        id: str = cfg.SH_ID,
        pw: str = cfg.SH_PW,
        cert_pw: str = cfg.CERT_PW,
        path: str = cfg.PATH_INDI,
    ):
        return self.indi.StartIndi(id, pw, cert_pw, path)

    def quit(self):
        return self.indi.CloseIndi()

    def set_query_name(self, name: str) -> bool:
        return self.indi.dynamicCall("SetQueryName(QString)", name)

    def set_single_data(self, index: int, data: str) -> bool:
        return self.indi.dynamicCall("SetSingleData(int, QString)", index, data)

    def request_data(self, name) -> int:
        """
        :output:
        :   -request id
        :       -0: fail
        :       -others: request id
        """
        req_id = self.indi.dynamicCall("RequestData()")
        self.req_ids[req_id] = name
        return req_id

    def get_single_data(self, index: int):
        return self.indi.dynamicCall("GetSingleData(int)", index)

    def get_multi_row_count(self):
        return self.indi.dynamicCall("GetMultiRowCount()")

    def get_multi_data(self, row, index):
        return self.indi.dynamicCall("GetMultiData(int, int)", row, index)

    def request(self, name: str, datas):
        self.set_query_name(name)
        for index, data in datas.items():
            self.set_single_data(index, data)
        return self.request_data(name)

    def receive(self, req_id: int = None):
        name = self.req_ids[req_id]
        return self.rec_funcs[name](req_id)

    def rec_total_acnt(self, *args, **kwargs):
        raise NotImplementedError()

    def rec_stock_acnt(self, *args, **kwargs):
        raise NotImplementedError()

    def rec_order(self, *args, **kwargs):
        raise NotImplementedError()

    def rec_single_data(self, indices):
        ret = DataFrame(columns=list(indices.keys()), index=[0])
        for col, idx in indices.items():
            ret[col][0] = self.get_single_data(idx)
        return ret

    def rec_multi_data(self, indices):
        ret = DataFrame(columns=list(indices.keys()))
        n_cnt = self.get_multi_row_count()
        for i in range(n_cnt):
            row = {}
            for col, idx in indices.items():
                row[col] = self.get_multi_data(i, idx)
            ret = ret.append(row, ignore_index=True)
        return ret

    def recieve_sys_msg(self, msg_id: int):
        if msg_id == 10:
            log("QuitIndi")
        elif msg_id == 11:
            log("START_INDI")
        else:
            log(f"REC_MSG:{msg_id}")
