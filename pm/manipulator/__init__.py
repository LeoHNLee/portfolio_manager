from pm.config import cfg
from pm.calculator import Calculator
from pm.control.casting import dt2str

import uiautomation as ui
import pandas as pd
from datetime import datetime as dt


def get_static(
    path:str=cfg.PATH_DATA,
    fn:str='origin.csv',
    backup:bool=True
) -> Calculator:
    calc = Calculator.read_csv(path, encoding='utf-8')
    if backup:
        calc.to_csv(f'{path}backup/{dt2str(dt.now())}.csv')
    return calc


def get_current(
    acnt, 
    set_krw, 
    path:str=cfg.PATH_DATA, 
    fn:str='tmp.csv'
) -> Calculator:
    file_path = path+fn
    acnt.SetFocus()
    set_krw.Click()
    acnt.RightClick()
    ui.MenuItemControl(searchDepth=3, Name='엑셀로 내보내기').Click()
    ui.MenuItemControl(searchDepth=4, Name='CSV').Click()
    ui.EditControl(searchDepth=6, Name='파일 이름(N):').SendKeys(file_path+'{Enter}')
    return Calculator.read_csv(file_path, encoding='cp949')


acnt = ui.PaneControl(searchDepth=5, ClassName='GXWND', AutomationId='3779')
set_krw = ui.ButtonControl(searchDepth=5, Name='원화기준')