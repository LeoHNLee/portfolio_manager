import asyncio
import time
from datetime import datetime as dt

from PyQt5 import uic
from PyQt5.QtCore import Qt, QDateTime, QTime
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QMainWindow, QMessageBox

from pm.log import log
from pm.control.casting import dt2str, qtdt2dt
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

        start_dt = QDateTime.currentDateTime()
        start_dt.setTime(QTime(23, 30))
        end_dt = QDateTime.currentDateTime()
        end_dt.setTime(QTime(6, 0))
        self.USCntrStartTime_dt.setDateTime(start_dt)
        self.USCntrEndTime_dt.setDateTime(end_dt)

        self.indi_info_updated = False
        self.origin_file_loaded = False
        self.indi_kr_info = IndiKRInfo()


    def us_indi_get(self):
        if not self.origin_file_loaded:
            QMessageBox.warning(
                self, 
                'Warning!', 
                'Not Yet Loaded the Original File!',
            )
            return

        self.USIndiGet_pbar.setValue(0)
        if self.USIndiGetBackup_cb.isChecked():
            self.origin.backup()
        self.indi_kr_info.req(
            origin=self.origin,
            pbar=self.USIndiGet_pbar,
            status_tb=self.USCntrIndiStatus_tb,
        )
        self.indi_info_updated = True


    def us_origin_file_load(self):
        dir_path = self.USOriginDir_tb.toPlainText()
        fn = self.USOriginFile_tb.toPlainText()
        self.origin = SHI.read_csv(f'{dir_path}{fn}', encoding='cp949')
        self.USCntrOriginStatus_tb.setTextColor(QColor(0, 255, 0, 255))
        self.USCntrOriginStatus_tb.setPlainText('Origin File Loaded!!')
        self.USCntrOriginStatus_tb.setAlignment(Qt.AlignCenter)
        self.origin_file_loaded = True


    def us_cntr_start(self):
        log('PRESS_US_CNTR_START')
        if not self.origin_file_loaded:
            QMessageBox.warning(
                self, 
                'Warning!', 
                'Not Yet Loaded the Original File!',
            )
            return

        if not self.indi_info_updated:
            QMessageBox.warning(
                self, 
                'Warning!', 
                'Not Yet Updated the Indi Info!',
            )
            return

        if self.USIndiGetBackup_cb.isChecked():
            self.origin.backup()

        start_time = qtdt2dt(self.USCntrStartTime_dt)
        end_time = qtdt2dt(self.USCntrEndTime_dt)
        time.sleep(1)
        self.origin.run(
            start_time,
            end_time,
            pbar=self.USCntr_pbar,
            iter_tb=self.USCntrIter_tb,
            trans_tb=self.USCntrTrans_tb,
        )