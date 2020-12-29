import uiautomation as ui
import pandas as pd
from datetime import datetime as dt

from pm.config import cfg
from pm.control.calculator import Calculator
from pm.control.casting import dt2str


class Manipulator(Calculator):
    def get_stock(
        path:str=cfg.PATH_DATA,
        fn:str='origin.csv',
        backup:bool=True
    ) -> Manipulator:
        calc = Manipulator.read_csv(path, encoding='utf-8')
        if backup:
            calc.to_csv(f'{path}backup/{dt2str(dt.now())}.csv')
        return calc


    def get_flow(
        acnt, 
        set_krw, 
        path:str=cfg.PATH_DATA, 
        fn:str='tmp.csv'
    ) -> Manipulator:
        file_path = path+fn
        acnt.SetFocus()
        set_krw.Click()
        acnt.RightClick()
        ui.MenuItemControl(searchDepth=3, Name='엑셀로 내보내기').Click()
        ui.MenuItemControl(searchDepth=4, Name='CSV').Click()
        ui.EditControl(searchDepth=6, Name='파일 이름(N):').SendKeys(file_path+'{Enter}')
        return Manipulator.read_csv(file_path, encoding='cp949')


    def bid_ask(self):
        self['virtual_amt'] -= self.apply(self.__bid_ask__, axis=1)


    def bid_ask_row(self, row) -> int:
        pos = row['position']
        diff = row['virtual_diff']
        pivot = row['pivot_val']
        cprice = row['currrent_val']

        if pos == 'neutral':
            if diff < -pivot:
                self.bid(diff, cprice)
            elif diff > pivot:
                self.ask(diff, cprice)

        elif pos == 'buy':
            if diff < -pivot:
                return self.bid_ask_amt(diff, cprice)
            elif diff > pivot:
                self.ask(diff, cprice)

        elif pos in ('sell', 'out'):
            if diff < -pivot:
                self.bid(diff, cprice)
            elif diff > pivot:
                return self.bid_ask_amt(diff, cprice)

        return 0


    def bid(self, diff:float, cprice:int):
        self.__bid_ask_amt__(diff, cprice)


    def ask(self, diff:float, cprice:int):
        self.__bid_ask_amt__(diff, cprice)


    def bid_ask_amt(self, diff:float, cprice:int) -> int:
        diff = abs(diff)
        if diff < cprice:
            return 1
        else:
            return diff // cprice