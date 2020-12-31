from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QAxContainer import *
from PyQt5.QtWidgets import QMainWindow
from pandas import DataFrame

from pm.config import cfg


class IndiAPI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.indi = QAxWidget('GIEXPERTCONTROL.GiExpertControlCtrl.1')
        self.indi.ReceiveData.connect(self.receive)
        self.indi.ReceiveSysMsg.connect(self.recieve_sys_msg)


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


    def get_multi_row_count(self):
        return self.indi.dynamicCall('GetMultiRowCount()')


    def get_multi_data(self, row, index):
        return self.indi.dynamicCall('GetMultiData(int, int)', row, index)


    def request(self, name:str, datas):
        self.set_query_name(name)
        for index, data in datas.items():
            self.set_single_data(index, data)
        return self.request_data()


    def receive(self, req_id):
        raise NotImplementedError()


    def rec_single_data(self, indices):
        ret = DataFrame(
            columns=list(indices.keys()),
            index=[0]
        )
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


    def recieve_sys_msg(self, msg_id):
        print("System Message Received = ", msg_id)