import os
import time
from datetime import datetime as dt

from _ctypes import COMError
from PyQt5 import uic
from PyQt5.QtCore import QDateTime, Qt, QTime
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QMainWindow, QMessageBox

from pm.config import cfg
from pm.control.casting import qtdt2dt, to_win_path
from pm.control.indi.kr_info import IndiKRInfo
from pm.control.shi import SHI
from pm.control.gopax import Gopax

form_class = uic.loadUiType("pm/templates/main.ui")[0]


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

        self.indi_info_updated = False
        self.origin_file_loaded = False

        self.GopaxReady_pb.clicked.connect(self.gopax_ready)
        self.GopaxStart_pb.clicked.connect(self.gopax_start)


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
                "Warning!",
                "Not Open the SHI!",
            )
        else:
            try:
                report = self.origin.init()
            except ValueError as e:
                QMessageBox.warning(
                    self,
                    "Alert!",
                    e,
                )
            else:
                log_init(report)

    def us_start(self):
        log('PRESS_US_START')
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
            log_err("LookupError", e)
            QMessageBox.warning(
                self,
                "Error!",
                f"""LookupError!
                >>>{e}<<<""",
            )
        log("US_END")


    def gopax_ready(self, _=None, root_path=cfg.PATH_ROOT, dir_path=cfg.PATH_DATA, fn='origin.csv'):
        file_path = to_win_path(root_path, dir_path, fn)
        self.origin = Gopax.read_csv(file_path, encoding='cp949')
        if self.Backup_cb.isChecked():
            self.origin.backup()


    def gopax_start(self):
        log("Start_Gopax")
        while True:
            self.origin.calculate()
            time.sleep(60)
        log("End_Gopax")

    def api_shi_quit(self):
        try:
            SHI.quit()
        except (LookupError, COMError) as e:
            QMessageBox.warning(
                self,
                "Warning!",
                "Not Open the SHI!",
            )

    def api_origin_load(
        self, _=None, root_path=cfg.PATH_ROOT, dir_path=cfg.PATH_DATA, fn="origin.csv"
    ):
        file_path = to_win_path(root_path, dir_path, fn)
        self.origin = SHI.read_csv(file_path, encoding="cp949")
        self.origin_file_loaded = True
        log('ORIGIN_LOAD')


    def origin_load_kr(self, root_path=cfg.PATH_ROOT, dir_path=cfg.PATH_DATA, fn='origin.csv'):
        file_path = to_win_path(root_path, dir_path, fn)
        self.origin = KRCntr.read_csv(file_path, encoding="cp949")
        self.origin_file_loaded = True
        log("ORIGIN_LOAD")
