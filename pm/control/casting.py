from datetime import datetime as dt

from PyQt5.QtCore import QDateTime


def dt2str(x:dt) -> str:
    return x.strftime('%Y%m%d%H%M%S')


def fstr2int(x:str) -> int:
    if isinstance(x, str):
        x = x.replace(',', '')
    return int(x)


def fstr2float(x:str) -> float:
    if isinstance(x, str):
        x = x.replace(',', '')
    return float(x)


def str2int(x:str) -> int:
    return int(x)


def qtdt2dt(x):
    x = x.dateTime()
    x = QDateTime.toString(x)
    x = x.split()
    ret = dt.strptime(' '.join(x[-2:]), '%H:%M:%S %Y')
    ret = ret.replace(
        month=int(x[1]),
        day=int(x[2]),
    )
    return ret


def to_win_path(root_path=None, dir_path=None, fn=None):
    ret = ''
    if root_path is not None:
        ret += root_path
    if dir_path is not None:
        ret += dir_path
    if fn is not None:
        ret += fn
    return ret.replace('/', '\\')