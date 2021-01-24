import time
from datetime import datetime as dt
from _ctypes import COMError

from PyQt5 import uic
from PyQt5.QtCore import Qt, QDateTime, QTime
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QMainWindow, QMessageBox

from pm.config import cfg
from pm.log import log, log_err
from pm.control.casting import qtdt2dt, to_win_path
from pm.control.indi.kr_info import IndiKRInfo
from pm.control.indi.kr_market import IndiKRMarket
from pm.control.shi import SHI
from pm.control.kr import KRCntr


form_class = uic.loadUiType('pm/templates/main.ui')[0]


class PMWindow(QMainWindow, form_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.USReady_pb.clicked.connect(self.us_ready)
        self.USPopup_pb.clicked.connect(self.us_popup)
        self.USStart_pb.clicked.connect(self.us_start)
        start_dt = QDateTime.currentDateTime()
        start_dt.setTime(QTime(23, 30))
        end_dt = QDateTime.currentDateTime()
        end_dt.setTime(QTime(6, 0))
        self.USStartTime_dt.setDateTime(start_dt)
        self.USEndTime_dt.setDateTime(end_dt)

        self.KRReady_pb.clicked.connect(self.kr_ready)
        self.KRStart_pb.clicked.connect(self.kr_start)
        start_dt = QDateTime.currentDateTime()
        start_dt.setTime(QTime(9, 0))
        end_dt = QDateTime.currentDateTime()
        end_dt.setTime(QTime(15, 20))
        self.KRStartTime_dt.setDateTime(start_dt)
        self.KREndTime_dt.setDateTime(end_dt)

        self.indi_info_updated = False
        self.origin_file_loaded = False


    def us_ready(self):
        self.api_origin_load()
        if self.Backup_cb.isChecked():
            self.origin.backup()
        self.indi_kr_info = IndiKRInfo()
        self.indi_kr_info.login(self)


    def us_popup(self):
        try:
            SHI.popup()
        except (LookupError, COMError) as e:
            QMessageBox.warning(
                self, 
                'Warning!', 
                'Not Open the SHI!',
            )


    def us_start(self):
        log('PRESS_US_START')
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

        if self.Backup_cb.isChecked():
            self.origin.backup()

        start_time = qtdt2dt(self.USStartTime_dt)
        end_time = qtdt2dt(self.USEndTime_dt)
        time.sleep(1)
        try:
            self.origin.run(
                start_time,
                end_time,
            )
        except (LookupError, COMError) as e:
            log_err('LookupError', e)
            QMessageBox.warning(
                self, 
                'Error!', 
                f'''LookupError!
                >>>{e}<<<''',
            )
        log('US_END')


    def kr_ready(self):
        self.origin_load_kr()
        if self.Backup_cb.isChecked():
            self.origin.backup()
        self.indi_kr_market = IndiKRMarket()
        self.indi_kr_market.login()


    def kr_start(self):
        start_time = qtdt2dt(self.KRStartTime_dt)
        end_time = qtdt2dt(self.KREndTime_dt)
        if start_time is None:
            start_time=dt.now()
        if end_time is None:
            end_time=start_time+td(minutes=1)
        time.sleep(1)
        if (
            dt.now() < start_time
            or dt.now() > end_time
        ):
            log('WAIT UNTIL OPEN MARKET')
            return
        self.indi_kr_market.req(self.origin)


    def api_shi_quit(self):
        try:
            SHI.quit()
        except (LookupError, COMError) as e:
            QMessageBox.warning(
                self, 
                'Warning!', 
                'Not Open the SHI!',
            )


    def api_origin_load(self, _=None, root_path=cfg.PATH_ROOT, dir_path=cfg.PATH_DATA, fn='origin.csv'):
        file_path = to_win_path(root_path, dir_path, fn)
        self.origin = SHI.read_csv(file_path, encoding='cp949')
        self.origin_file_loaded = True
        log('ORIGIN_LOAD')
        
        
    def origin_load_kr(self, root_path=cfg.PATH_ROOT, dir_path=cfg.PATH_DATA, fn='origin.csv'):
        file_path = to_win_path(root_path, dir_path, fn)
        self.origin = KRCntr.read_csv(file_path, encoding='cp949')
        self.origin_file_loaded = True
        log('ORIGIN_LOAD')