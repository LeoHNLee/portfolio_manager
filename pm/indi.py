from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QAxContainer import *
from PyQt5.QtWidgets import QMainWindow

from pm.config import cfg
from pm.control.manipulator import Manipulator


class Indi(QMainWindow):
    def __init__(self):
        super().__init__()
        self.indi = QAxWidget('GIEXPERTCONTROL.GiExpertControlCtrl.1')
        self.indi.ReceiveData.connect(self.receive)
        self.indi.ReceiveSysMsg.connect(self.recieve_sys_msg)

        self.req_ids = {}
        self.rec_funcs = {
            'SABA655Q1': self.rec_total_acnt,
        }


    def set_query_name(self, name:str) -> bool:
        return self.indi.dynamicCall("SetQueryName(QString)", name)


    def set_single_data(self, index:int, data:str) -> bool:
        return self.indi.dynamicCall('SetSingleData(int, QString)', index, data)


    def request_data(self) -> int:
        '''
        :output:
        :   -request id
        :       -0: fail
        :       -others: request id
        '''
        return self.indi.dynamicCall("RequestData()")
    
    
    def get_single_data(self, index:int):
        return self.indi.dynamicCall('GetSingleData(int)', index)


    def receive(self, req_id:int):
        name = self.req_ids[req_id]
        # del self.req_ids[req_id]
        return self.rec_funcs[name]()


    def request(self, name:str, datas):
        self.set_query_name(name)
        for data in datas:
            self.set_single_data(*data)
        req_id = self.request_data()
        self.req_ids[req_id] = name
        return req_id


    def req_total_acnt(self):
        return self.request(
            name='SABA655Q1',
            datas = [
                [0, cfg.ACNT_NO],
                [1, '01'],
                [2, cfg.ACNT_PW],
            ],
        )


    def rec_total_acnt(self):
        indices = {
            '순자산평가금액': 0,
            '주식평가금액': 3,
            '외화자산평가금액': 13,
            '현금증거금합계': 18,
            '인출가능금액합계':19,
        }
        ret = Manipulator(
            columns=list(indices.keys()),
            index=[0],
        )
        for col, idx in indices.items():
            ret[col][0] = self.get_single_data(idx)
        return ret


    def recieve_sys_msg(self, msg_id):
        print("System Message Received = ", msg_id)


# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     IndiWindow = IndiWindow()
#     IndiWindow.show()
#     app.exec_()

