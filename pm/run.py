import sys
from PyQt5.QtWidgets import QApplication

from pm.view import PMWindow
from pm.control.manipulator import Manipulator


if __name__ == '__main__':
    app = QApplication(sys.argv)
    origin = Manipulator.read_csv('data/origin.csv')
    pm_window = PMWindow(origin)
    pm_window.show()
    app.exec_()