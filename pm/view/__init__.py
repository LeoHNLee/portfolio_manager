from datetime import datetime as dt

from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QMainWindow, QMessageBox

from pm.control.casting import dt2str
from pm.control.indi.kr_info import IndiKRInfo
from pm.control.shi import SHI


form_class = uic.loadUiType('pm/templates/main.ui')[0]


class PMWindow(QMainWindow, form_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.USIndiGet_pb.clicked.connect(self.us_indi_get)
        self.USOriginFileLoad_pb.clicked.connect(self.us_origin_file_load)
        self.USCntrStart_pb.clicked.connect(self.us_cntr_start)

        self.indi_kr_info = IndiKRInfo()

        self.indi_info_updated = False
        self.origin_file_loaded = False


    def us_indi_get(self):
        if not self.origin_file_loaded:
            QMessageBox.warning(
                self, 
                'Warning!', 
                'Not Yet Loaded the Original File!',
            )
            return

        self.USIndiGet_pbar.setValue(0)
        self.indi_kr_info.req(
            origin=self.origin,
            pbar=self.USIndiGet_pbar,
            backup=self.USIndiGetBackup_cb.isChecked(),
            status_tb=self.USCntrIndiStatus_tb,
        )


    def us_origin_file_load(self):
        dir = self.USOriginDir_tb.toPlainText()
        fn = self.USOriginFile_tb.toPlainText()
        self.origin = SHI.read_csv(f'{dir}{fn}')
        self.USCntrOriginStatus_tb.setTextColor(QColor(0, 255, 0, 255))
        self.USCntrOriginStatus_tb.setPlainText('Origin File Loaded!!')
        self.USCntrOriginStatus_tb.setAlignment(Qt.AlignCenter)


    def us_cntr_start(self):
        self.USCntrIter_tb.setPlainText('123')