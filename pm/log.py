from datetime import datetime as dt
import locale
locale.setlocale(locale.LC_MONETARY, 'en_US')

import logging

from pm.config import cfg


def dt2log(x):
    return x.strftime('%Y-%m-%d_%H%M%S')


now = dt2log(dt.now())
log_formatter = logging.Formatter('[%(levelname)s][%(asctime)s]%(message)s')
file_handler = logging.FileHandler(filename=f'{cfg.PATH_LOG}{now}.log')
file_handler.setFormatter(log_formatter)
file_handler.setLevel(cfg.LOGGING_LEVEL)

logger = logging.getLogger()
logger.addHandler(file_handler)


def log(type, msg=None):
    ret = f'[{type}]'
    if msg is not None:
        ret += msg
    logger.warning(ret)
    print(ret)


def log_err(type, msg):
    logger.error(f'[{type}][ErrorMsg:{msg}]')
    print(ret)


def log_usd(type, usd, msg=None):
    usd = locale.currency(usd, symbol=False, grouping=True)
    ret = f'[USD:{usd}]'
    if msg:
        ret += msg
    log(type, ret)


def log_order(type, ticker, usd, exec_amt=None, exec_price=None, bf_amt=None, pivot=None, diff=None):
    msg = f'[Ticker:{ticker}][ExecAmt:{exec_amt}][ExecPrice:{exec_price}][BeforeAmt:{bf_amt}][Pivot:{pivot}][Diff:{diff}]'
    log_usd(type, usd, msg)


def log_bid(ticker, usd, exec_amt, exec_price, bf_amt):
    log_order(
        type='BID',
        ticker=ticker,
        usd=usd,
        exec_amt=exec_amt,
        exec_price=exec_price,
        bf_amt=bf_amt,
    )


def log_ask(ticker, usd, exec_amt, exec_price, bf_amt):
    log_order(
        type='ASK',
        ticker=ticker,
        usd=usd,
        exec_amt=exec_amt,
        exec_price=exec_price,
        bf_amt=bf_amt,
    )


def log_bid_fail(ticker, usd, exec_price):
    log_order(
        type='BID_FAIL',
        ticker=ticker,
        usd=usd,
        exec_price=exec_price,
    )


def log_ask_fail(ticker, usd, exec_amt, bf_amt):
    log_order(
        type='ASK_FAIL',
        ticker=ticker,
        usd=usd,
        exec_amt=exec_amt,
        bf_amt=bf_amt,
    )


def log_backup(path):
    log('BACKUP', f'[FilePath:{path}]')


def log_save(path):
    log('SAVE', f'[FilePath:{path}]')