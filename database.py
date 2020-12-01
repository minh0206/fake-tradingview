import datetime
import glob
import gzip
import logging
import multiprocessing
import os
import shutil
import tempfile
from math import ceil, floor
from multiprocessing import Process, Queue
from time import sleep, time

import bitmex
import numpy as np
import pandas as pd
import requests
from bitmex_websocket import BitMEXWebsocket
from ciso8601 import parse_datetime

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)
fh = logging.StreamHandler()
fh_formatter = logging.Formatter(
    "%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s"
)
fh.setFormatter(fh_formatter)
logger.addHandler(fh)


class Database(object):
    def __init__(self, index, interval):
        self.symbols = ["XBTUSD", "ETHUSD"]

        self.df = pd.DataFrame()
        self.live_df = pd.DataFrame()
        self.ohlc_df = pd.DataFrame()
        self.live_ohlc_df = pd.DataFrame()

        self.index = index
        self.ohlc_idx = None
        self.interval = interval

        self.last_ohlc_dt = datetime.datetime.now(datetime.timezone.utc)

        self.ohlc_q = Queue(10)
        self.live_ohlc_q = Queue(5)

        self.ohlc_info_q = Queue(1)
        self.live_info_q = Queue(1)

        if not os.path.exists("data"):
            os.mkdir("data")

        self.update_historical_data()
        self.update_live_data()

    def download_data(self, date, temp_dir):
        url = "https://s3-eu-west-1.amazonaws.com/public.bitmex.com/data/trade/{}.csv.gz".format(
            date
        )

        file_name_gz = url.split("/")[-1]
        file_name = file_name_gz[:-3]

        with requests.head(url) as r:
            if not r.ok:
                return

        with requests.get(url, stream=True) as r:
            with open(os.path.join(temp_dir, file_name_gz), "wb") as f:
                shutil.copyfileobj(r.raw, f)

            with gzip.open(os.path.join(temp_dir, file_name_gz), "rb") as f_in:
                with open(os.path.join(temp_dir, file_name), "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

        csv = pd.read_csv(os.path.join(temp_dir, file_name))
        query = "symbol in {}".format(self.symbols)
        df = csv.query(query)[["timestamp", "symbol", "side", "size", "price"]]

        parser = lambda dt: dt.replace("D", "T")[:-6] + "000+00:00"
        df.timestamp = df.timestamp.apply(parser)
        df.to_csv("data/" + file_name, index=False)

    def update_historical_data(self):
        self.ohlc_info_q.put([self.symbols[self.index], self.interval])

        Process(
            target=self._update, args=(self.ohlc_info_q, self.ohlc_q), daemon=True,
        ).start()

    def _update(self, ohlc_info_q, ohlc_q):
        self.update_historical_data_process()
        self.ohlc_process(ohlc_info_q, ohlc_q)

    def ohlc_process(self, ohlc_info_q, ohlc_q):
        logger.info("Start OHLC process")
        while True:
            try:
                symbol, interval = ohlc_info_q.get_nowait()
            except Exception:
                pass
            else:
                if symbol != None or interval != None:
                    files = sorted(glob.glob("data/*"), reverse=True)
                    logger.debug("---Start {} {}".format(symbol, interval))
                    while not ohlc_q.empty():
                        ohlc_q.get()

            if not ohlc_q.full():
                file = files.pop(0)
                csv = pd.read_csv(
                    file, index_col=0, parse_dates=True, date_parser=parse_datetime,
                ).query("symbol == '{}'".format(symbol))
                ohlc = csv.price.resample(interval).ohlc()
                ohlc_q.put([csv, ohlc])
                # logger.debug("Done reading")

    def update_historical_data_process(self):
        logger.info("Start update history process")
        file_name = os.listdir("data")

        if file_name:
            start_dt = parse_datetime(file_name[-1][:-4])
        else:
            start_dt = datetime.datetime(2020, 11, 1)

        end_dt = datetime.datetime.now()

        with tempfile.TemporaryDirectory(dir=os.getcwd()) as temp_dir:
            for n in range(1, int((end_dt.date() - start_dt.date()).days)):
                date = start_dt + datetime.timedelta(n)
                logger.debug("Downloading {}".format(date))
                self.download_data(date.strftime("%Y%m%d"), temp_dir)

        logger.info("Done update history process")

    def update_live_data(self):
        self.live_info_q.put([self.symbols[self.index], self.interval])

        Process(
            target=self.update_live_data_process,
            args=(self.live_info_q, self.live_ohlc_q),
            daemon=True,
        ).start()

    def update_live_data_process(self, live_info_q, live_ohlc_q):
        client = bitmex.bitmex(test=False)
        live = False

        while True:
            try:
                symbol, interval = live_info_q.get_nowait()
            except Exception:
                pass
            else:
                if symbol != None:
                    i = 0
                    df = pd.DataFrame()
                    ws = BitMEXWebsocket(
                        endpoint="https://www.bitmex.com/api/v1", symbol=symbol,
                    )

                    last_dt = datetime.datetime.now(datetime.timezone.utc).replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    url = "https://s3-eu-west-1.amazonaws.com/public.bitmex.com/data/trade/{}.csv.gz".format(
                        (last_dt - datetime.timedelta(1)).strftime("%Y%m%d")
                    )
                    with requests.head(url) as r:
                        if not r.ok:
                            last_dt = last_dt - datetime.timedelta(1)

                    file_name = "temp_" + symbol + ".csv"
                    if os.path.exists(file_name):
                        try:
                            temp_df = pd.read_csv(
                                file_name, index_col=0, parse_dates=True
                            )
                        except Exception:
                            pass
                        else:
                            temp_dt = temp_df.index[-1].to_pydatetime()
                            if temp_dt > last_dt:
                                last_dt = temp_dt
                                df = temp_df

            if live:
                s = "Live"
                result = ws.recent_trades()
            else:
                s = "Updating"
                sleep(2)
                result = client.Trade.Trade_get(
                    symbol=symbol, startTime=last_dt, count=1000
                ).result()[0]

            temp_df = pd.DataFrame.from_records(
                result,
                index="timestamp",
                columns=["timestamp", "symbol", "side", "size", "price", "trdMatchID"],
            )
            temp_df.index = pd.to_datetime(temp_df.index, utc=True)

            df = pd.concat([df, temp_df])
            df = df[~df.trdMatchID.duplicated(keep="first")]

            if live_ohlc_q.full():
                live_ohlc_q.get()

            live_ohlc_q.put(
                [df.drop("trdMatchID", axis=1), df.price.resample(interval).ohlc()]
            )

            last_dt = temp_df.index[-1].to_pydatetime()
            live_dt = parse_datetime(ws.recent_trades()[-1]["timestamp"])
            if last_dt > live_dt:
                live = True

            logger.info(
                "{} | {} {} {} | Live queue {}".format(
                    s, symbol, interval, last_dt.astimezone(), self.live_ohlc_q.qsize()
                )
            )

            i += 1
            if i % 5 == 0:
                df.to_csv(file_name)

    def ohlc(self, total_bars, fetch_live=False, index=None, interval=None):
        if (interval is not None) or (index is not None):
            if index != self.index and index is not None:
                self.index = index
            if interval != self.interval and interval is not None:
                self.interval = interval

            self.df = pd.DataFrame()
            self.ohlc_df = pd.DataFrame()

            self.ohlc_info_q.put([self.symbols[self.index], self.interval])
            self.live_info_q.put([self.symbols[self.index], self.interval])

            while True:
                try:
                    self.live_df, self.live_ohlc_df = self.live_ohlc_q.get_nowait()
                except Exception:
                    self.live_df = pd.DataFrame()
                    self.live_ohlc_df = pd.DataFrame()
                    break
                else:
                    freq = self.live_ohlc_df.index.freq
                    if (
                        all(self.live_df["symbol"] == self.symbols[self.index])
                        and self.interval == str(freq.n) + freq.name
                    ):
                        break

        while len(self.ohlc_df) < total_bars:
            df, ohlc_df = self.ohlc_q.get()
            freq = ohlc_df.index.freq
            if (
                all(df["symbol"] == self.symbols[self.index])
                and self.interval == str(freq.n) + freq.name
            ):
                self.df = pd.concat([df, self.df])
                self.ohlc_df = pd.concat([ohlc_df, self.ohlc_df])

        if fetch_live:
            self.live_df, self.live_ohlc_df = self.live_ohlc_q.get()

        ohlc = pd.concat([self.ohlc_df[-total_bars:], self.live_ohlc_df])
        self.ohlc_idx = ohlc.index

        return ohlc

    def volume_on_price(self, start_dt, end_dt, num):
        live_df, _ = self.live_ohlc_q.get()

        df = self.df[self.df["symbol"] == self.symbols[self.index]]
        df = pd.concat([df, live_df])
        df = df[((df.index >= start_dt) & (df.index <= end_dt))]

        price_min = df.price.min()
        price_max = df.price.max()

        buy = df[df["side"] == "Buy"]
        sell = df[df["side"] == "Sell"]

        bins, step = np.linspace(price_min, price_max, num + 1, retstep=True)

        buy_bins = pd.cut(buy["price"], bins, include_lowest=True)
        sell_bins = pd.cut(sell["price"], bins, include_lowest=True)

        buy = buy.groupby(buy_bins)["price"].agg("sum")
        sell = sell.groupby(sell_bins)["price"].agg("sum")

        return (
            pd.concat([buy, sell], axis=1, keys=["buy", "sell"]),
            (price_min, price_max),
            step,
        )


if __name__ == "__main__":
    db = Database(0, "1H")

    while True:
        pass
    #     sleep(5)
    #     print(db.df.info(memory_usage="deep"))

