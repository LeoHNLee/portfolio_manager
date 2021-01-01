from datetime import datetime as dt


def dt2str(x:dt) -> str:
    return dt.strftime('%Y%m%d%H%M%S')


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