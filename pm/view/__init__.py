import sys
from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow


form_class = uic.loadUiType('pm/templates/main.ui')[0]


class PMWindow(QMainWindow, form_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)