from pm.config import cfg

import uiautomation as ui
import pandas as pd
from datetime import datetime as dt


def get_acnt(acnt, name:str) -> pd.DataFrame:
    path = cfg.PATH_ACNT+name+'.csv{Enter}'
    acnt.SetFocus()
    acnt.RightClick()
    ui.MenuItemControl(searchDepth=3, Name='엑셀로 내보내기').Click()
    ui.MenuItemControl(searchDepth=4, Name='CSV').Click()
    ui.EditControl(searchDepth=6, Name='파일 이름(N):').SendKeys(path)
    return pd.read_csv(path, encoding='cp949')


acnt = ui.PaneControl(searchDepth=5, ClassName='GXWND', AutomationId='3779')
now = dt(2020, 12, 28, 6)
df = get_csv(acnt, dt.now().strftime('%Y%m%d%H%M%S'))