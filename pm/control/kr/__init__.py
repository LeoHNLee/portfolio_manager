import time
from datetime import datetime as dt
from datetime import timedelta as td

import numpy as np
import pandas as pd

from pm.config import cfg
from pm.control import Controller
from pm.control.casting import str2int
from pm.log import log, log_ask_kr, log_ask_kr_fail, log_bid_kr, log_bid_kr_fail


class KRCntr(Controller):
    @staticmethod
    def from_df(df):
        return KRCntr(df.values, columns=df.columns, index=df.index)

    @staticmethod
    def read_csv(*args, **kwargs):
        df = pd.read_csv(*args, **kwargs)
        return KRCntr.from_df(df)

    def calculate(self):
        self["current_total"] = self["current_amt"] * self["current_val"]
        self["virtual_total"] = self.apply(self.calc_virtual_total, axis=1)
        self["pivot_val"] = self.apply(self.calc_pivot_val, axis=1)

        total = self["current_total"].sum()
        self["target_total"] = self["target_rate"] * total
        self["target_diff"] = self["target_total"] - self["current_total"]
        self["virtual_diff"] = self["virtual_total"] + self["target_diff"]
        self["position"] = self.apply(self.adjust_pos, axis=1)
        self["pivot_rate"] = self.apply(self.adjust_threshold, axis=1)
        log("CALCULATE")
