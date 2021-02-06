import hmac
import json
import re
import time
from base64 import b64decode, b64encode
from hashlib import sha512
from json.decoder import JSONDecodeError
from typing import Optional

import pandas as pd
import requests

from pm.config import cfg
from pm.control import Controller
from pm.log import log_order, log_request, log_response


class Gopax(Controller):
    API_KEY = cfg.GOPAX_KEY
    SECRET = cfg.GOPAX_SECRET
    HOST = cfg.GOPAX_HOST
    REQ_MAP = {
        "GET": requests.get,
        "POST": requests.post,
        "DELETE": requests.delete,
    }
    REQ_AUTH = [
        re.compile(f"^{term}[-/a-zA-Z]*$")
        for term in (
            "/balances",
            "/orders",
            "/trades",
            "/deposit-withdrawal-status",
            "/crypto-deposit-addresses",
            "/crypto-withdrawal-addresses",
        )
    ]

    @staticmethod
    def from_df(df):
        return Gopax(df.values, columns=df.columns, index=df.index)

    @staticmethod
    def read_csv(*args, **kwargs):
        df = pd.read_csv(*args, **kwargs)
        return Gopax.from_df(df)

    def request(
        self,
        method: str,
        path: str,
        body: Optional[dict] = None,
        recv_window: Optional[int] = None,
    ):
        caller = self.REQ_MAP.get(method)
        if caller is None:
            raise ValueError(f"method <{method}> is not proper")
        if self.need_auth(path):
            headers = self.create_header(method, path, body, recv_window)
        else:
            headers = {}
        log_request(method, self.HOST + path, headers, body)
        resp = caller(url=self.HOST + path, headers=headers, json=body)
        if resp.status_code != 200 or resp.json().get("errorMessage") is not None:
            pass
        log_response(
            resp.status_code, method, self.HOST + path, resp.headers, resp.text
        )
        return resp

    def need_auth(self, path: str):
        for compiler in self.REQ_AUTH:
            if compiler.match(path):
                return True
        return False

    def create_ts(self):
        return str(int(time.time() * 1000))

    def create_header(
        self,
        method: str,
        path: str,
        body: Optional[dict] = None,
        recv_window: Optional[int] = None,
    ):
        if recv_window is None:
            recv_window = ""
        if body is None:
            body = ""
        else:
            body = json.dumps(body)
        timestamp = self.create_ts()
        msg = f"t{timestamp}{method}{path}{recv_window}{body}"
        msg = msg.encode("utf-8")
        raw_secret = b64decode(self.SECRET)
        raw_signature = hmac.new(raw_secret, msg, sha512).digest()
        signature = b64encode(raw_signature)
        headers = {
            "api-key": self.API_KEY,
            "timestamp": timestamp,
            "signature": signature,
        }
        if recv_window:
            headers["receive-window"] = str(recv_window)
        return headers

    def calc_current_val(self, row):
        if row["cat0"] != "GOPAX":
            return row["current_val"]
        ticker = row["name"]
        if ticker == "KRW":
            return 1
        resp = self.request("GET", f"/trading-pairs/{ticker}-KRW/ticker")
        try:
            resp_body = resp.json()
        except JSONDecodeError:
            return row["current_val"]
        return resp_body["price"]

    def calc_current_amt(self, row):
        if row["cat0"] != "GOPAX":
            return row["current_amt"]
        ticker = row["name"]
        resp = self.request("GET", f"/balances/{ticker}")
        try:
            resp_body = resp.json()
        except JSONDecodeError:
            return 0
        amt = resp_body["avail"] + resp_body["pendingWithdrawal"] + resp_body["hold"]
        return amt

    def calc_pivot_val(self, row):
        if row["cat0"] != "GOPAX":
            return row["pivot_val"]
        return max(10000, row["current_total"] * 0.01)

    def calculate(self):
        self["current_val"] = self.apply(self.calc_current_val, axis=1)
        self["current_amt"] = self.apply(self.calc_current_amt, axis=1)
        self["current_total"] = self["current_val"] * self["current_amt"]
        self["virtual_total"] = self.apply(self.calc_virtual_total, axis=1)
        self["pivot_val"] = self.apply(self.calc_pivot_val, axis=1)
        self["target_rate"] = self.apply(self.calc_target_rate, axis=1)
        total = self["current_total"].sum()
        self["target_total"] = self["target_rate"] * total
        self["target_diff"] = self["target_total"] - self["current_total"]
        self["virtual_diff"] = self["virtual_total"] + self["target_diff"]
        self["virtual_amt"] -= self.apply(self.order, axis=1)
        try:
            self.save()
        except PermissionError:
            pass

    def order(self, row) -> int:
        ticker = row["name"]
        cat = row["cat0"]
        if cat != "GOPAX" or ticker == "KRW":
            return 0

        pos = row["position"]
        pivot = row["pivot_val"]
        price = row["current_val"]
        t_diff = row["target_diff"]
        t_amt = abs(t_diff / price)
        v_diff = row["virtual_diff"]
        v_amt = abs(v_diff / price)

        if pos == "neutral":
            if t_diff < -pivot:
                self.ask(ticker, abs(t_amt))
            elif t_diff > pivot:
                self.bid(ticker, abs(t_diff))

        elif pos == "buy":
            if v_diff < -pivot:
                log_order(
                    "VIRTUAL_ASK", ticker, -1, exec_amt=v_amt, pivot=pivot, diff=v_diff
                )
                return v_amt
            elif v_diff > pivot:
                self.bid(ticker, abs(v_diff))

        elif pos in ("sell", "out"):
            if v_diff < -pivot:
                self.ask(ticker, abs(v_amt))
            elif v_diff > pivot:
                log_order(
                    "VIRTUAL_BID", ticker, -1, exec_amt=v_amt, pivot=pivot, diff=v_diff
                )
                return v_amt

        elif pos == "in":
            self.bid(ticker, 10000)
        return 0

    def bid(self, ticker: str, amt: int):
        self.request(
            "POST",
            "/orders",
            {
                # "clientOrderId": "test4321",   # 선택 | 클라이언트 오더 ID로 최대 20자이고 [a-zA-Z0-9_-] 문자 사용 가능
                "tradingPairName": f"{ticker}-KRW",  # 필수 | 오더북
                "side": "buy",  # 필수 | buy(구매), sell(판매)
                "type": "market",  # 필수 | limit(지정가), market(시장가)
                # "price": 11000000,             # 필수 (지정가에 한함) | 주문 가격
                # "stopPrice": 12000000,         # 선택 (값이 있으면 예약가 주문으로 처리됨) | 감시 가격
                "amount": amt,  # 필수 | 주문 수량
                "protection": "yes",  # 선택 (디폴트 no) | 최초 체결가 기준 ±10% 초과되는 주문 취소 여부로 yes/no 중 택일
                # "timeInForce": "gtc"           # 선택 (지정가에 한하며 디폴트는 gtc) | 지정가 주문 유형으로 gtc/po/ioc/fok 중 택일
            },
        )

    def ask(self, ticker: str, amt: int):
        self.request(
            "POST",
            "/orders",
            {
                # "clientOrderId": "test4321",   # 선택 | 클라이언트 오더 ID로 최대 20자이고 [a-zA-Z0-9_-] 문자 사용 가능
                "tradingPairName": f"{ticker}-KRW",  # 필수 | 오더북
                "side": "sell",  # 필수 | buy(구매), sell(판매)
                "type": "market",  # 필수 | limit(지정가), market(시장가)
                # "price": 11000000,             # 필수 (지정가에 한함) | 주문 가격
                # "stopPrice": 12000000,         # 선택 (값이 있으면 예약가 주문으로 처리됨) | 감시 가격
                "amount": amt,  # 필수 | 주문 수량
                "protection": "yes",  # 선택 (디폴트 no) | 최초 체결가 기준 ±10% 초과되는 주문 취소 여부로 yes/no 중 택일
                # "timeInForce": "gtc"           # 선택 (지정가에 한하며 디폴트는 gtc) | 지정가 주문 유형으로 gtc/po/ioc/fok 중 택일
            },
        )
