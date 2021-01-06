import time
from datetime import datetime as dt

from PyQt5 import uic
from PyQt5.QtCore import Qt, QDateTime, QTime
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QMainWindow, QMessageBox

from pm.config import cfg
from pm.log import log
from pm.control.casting import dt2str, qtdt2dt, to_win_path
from pm.control.indi.kr_info import IndiKRInfo
from pm.control.shi import SHI


form_class = uic.loadUiType('pm/templates/main.ui')[0]


class PMWindow(QMainWindow, form_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.APIIndi_cb.stateChanged.connect(self.api_status_indi)

        self.APISHIOpen_pb.clicked.connect(self.api_shi_open)
        self.APISHIPopup_pb.clicked.connect(self.api_shi_popup)
        self.APISHIQuit_pb.clicked.connect(self.api_shi_quit)

        self.APIOriginLoad_pb.clicked.connect(self.api_origin_load)
        self.APIOriginGet_pb.clicked.connect(self.api_origin_get)

        self.USStart_pb.clicked.connect(self.us_cntr_start)
        start_dt = QDateTime.currentDateTime()
        start_dt.setTime(QTime(23, 30))
        end_dt = QDateTime.currentDateTime()
        end_dt.setTime(QTime(6, 0))
        self.USStartTime_dt.setDateTime(start_dt)
        self.USEndTime_dt.setDateTime(end_dt)

        self.indi_info_updated = False
        self.origin_file_loaded = False
        self.indi_kr_info = IndiKRInfo()


    def api_status_indi(self):
        if self.APIIndi_cb.isChecked():
            ok = self.indi_kr_info.login()
            if not ok:
                QMessageBox.warning(
                    self, 
                    'Warning!', 
                    'Failed Open and Login SH Indi!',
                )
        else:
            ok = self.indi_kr_info.quit()
            if not ok:
                QMessageBox.warning(
                    self, 
                    'Warning!', 
                    'Failed Close SH Indi!',
                )


    def api_shi_open(self):
        SHI.open()
        log('SHI_OPEN')


    def api_shi_popup(self):
        try:
            SHI.popup()
        except LookupError as e:
            QMessageBox.warning(
                self, 
                'Warning!', 
                'Not Open the SHI!',
            )
        log('SHI_POPUP')


    def api_shi_quit(self):
        try:
            SHI.quit()
        except LookupError as e:
            QMessageBox.warning(
                self, 
                'Warning!', 
                'Not Open the SHI!',
            )
        log('SHI_QUIT')


    def api_origin_load(self, _, root_path=cfg.PATH_ROOT, dir_path=cfg.PATH_DATA, fn='origin.csv'):
        file_path = to_win_path(root_path, dir_path, fn)
        self.origin = SHI.read_csv(file_path, encoding='cp949')
        self.origin_file_loaded = True
        log('ORIGIN_LOAD')


    def api_origin_get(self):
        if not self.origin_file_loaded:
            QMessageBox.warning(
                self, 
                'Warning!', 
                'Not Yet Loaded the Original File!',
            )
            return

        if self.APIBackup_cb.isChecked():
            self.origin.backup()
        self.indi_kr_info.req(
            origin=self.origin,
            status_cb=self.APIIndi_cb,
        )
        self.indi_info_updated = True
        self.origin.save()
        log('ORIGIN_GET')


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

        if self.APIBackup_cb.isChecked():
            self.origin.backup()

        start_time = qtdt2dt(self.USStartTime_dt)
        end_time = qtdt2dt(self.USEndTime_dt)
        time.sleep(1)
        self.origin.run(
            start_time,
            end_time,
            pbar=self.US_pbar,
            iter_tb=self.USIter_tb,
            trans_tb=self.USTrans_tb,
        )