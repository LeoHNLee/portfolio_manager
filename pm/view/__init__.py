import sys
from datetime import datetime as dt

from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow

from pm.control.casting import dt2str
from pm.control.indi.kr_info import IndiKRInfo


form_class = uic.loadUiType('pm/templates/main.ui')[0]


class PMWindow(QMainWindow, form_class):
    def __init__(self, manip=None):
        super().__init__()
        self.setupUi(self)
        self.USIndiGet_btn.clicked.connect(self.us_indi_get)
        self.USCntrStart_btn.clicked.connect(self.us_cntr_start)

        self.manip = manip
        self.indi_kr_info = IndiKRInfo()

        # self.WTUSA_tb.setPlanText(dt2str(dt.now()))


    def us_indi_get(self):
        self.USIndiGet_pb.setValue(0)
        self.indi_kr_info.req(
            manip=self.manip,
            pb=self.USIndiGet_pb,
            backup=self.USIndiGetBackup_cb.isChecked(),
        )


    def us_cntr_start(self):
        self.USCntrIter_tb.setPlainText('123')