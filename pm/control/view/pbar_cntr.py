from datetime import datetime as dt


def plus(pbar, pct):
    new_val = pbar.value() + pct
    pbar.setValue(new_val)


def timer(pbar, start_date, end_date):
    now = dt.now()
    son = now - start_date
    mother = end_date - start_date
    new_val = int(son/mother*100)
    pbar.setValue(new_val)