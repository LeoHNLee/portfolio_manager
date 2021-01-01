import sys
from PyQt5.QtWidgets import QApplication

from pm.view import PMWindow


if __name__ == '__main__':
    app = QApplication(sys.argv)
    pm_window = PMWindow()
    pm_window.show()
    app.exec_()