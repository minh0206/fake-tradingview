import datetime
import glob
import gzip
import logging
import multiprocessing
import os
import shutil
from math import ceil, floor
from multiprocessing import Process, Queue
from time import sleep, time

import bitmex
import numpy as np
import pandas as pd
import requests
from bitmex_websocket import BitMEXWebsocket
from ciso8601 import parse_datetime
from dateutil.tz import tzlocal

from utils import logger


class Database(object):
    def __init__(self, index, interval):
        self.symbols = ["XBTUSD", "ETHUSD"]

        self.df = pd.DataFrame()
        self.live_df = pd.DataFrame()
        self.ohlc_df = pd.DataFrame()
        self.live_ohlc_df = pd.DataFrame()

        self.index = index
        self.interval = interval

        self.ohlc_q = Queue(20)
        self.live_ohlc_q = Queue(10)

        self.ohlc_info_q = Queue(1)
        self.live_info_q = Queue(1)

        if not os.path.exists("data"):
            os.mkdir("data")

        self.updateHistoricalData()
        self.updateLiveData()

    def getDateFormat(self):
        if self.interval.find("S") != -1:
            dtFormat = "%d %b '%y  %H:%M:%S"
        elif self.interval.find("T") != -1 or self.interval.find("H") != -1:
            dtFormat = "%d %b '%y  %H:%M"
        else:
            dtFormat = "%d %b '%y"

        return dtFormat

    def getDate(self):
        dtFormat = self.getDateFormat()
        fn = lambda dt: dt.strftime(dtFormat)
        date = list(map(fn, self.ohlc_df.index.tz_convert(tzlocal())))

        return date

    def downloadData(self, date):
        url = "https://s3-eu-west-1.amazonaws.com/public.bitmex.com/data/trade/{}.csv.gz".format(
            date
        )
        fileName = url.split("/")[-1]

        with requests.get(url, stream=True) as r:
            if r.ok:
                with open(os.path.join("data", fileName), "wb") as f:
                    shutil.copyfileobj(r.raw, f)

    def updateHistoricalData(self):
        self.ohlc_info_q.put([self.symbols[self.index], self.interval])
        Process(
            target=self._update, args=(self.ohlc_info_q, self.ohlc_q), daemon=True,
        ).start()
        self.df, self.ohlc_df = self.ohlc_q.get()

    def _update(self, ohlc_info_q, ohlc_q):
        self.updateHistoricalDataProcess()
        self.readDataProcess(ohlc_info_q, ohlc_q)

    def readDataProcess(self, ohlc_info_q, ohlc_q):
        logger.debug("Start reading data")
        while True:
            try:
                symbol, interval = ohlc_info_q.get_nowait()
            except Exception:
                pass
            else:
                if symbol != None or interval != None:
                    files = sorted(glob.glob("data/*"), reverse=True)
                    logger.debug("--- Start {} {} ---".format(symbol, interval))
                    while not ohlc_q.empty():
                        ohlc_q.get()

            if not ohlc_q.full():
                file = files.pop(0)
                csv = pd.read_csv(file, compression="gzip")

                df = csv.query("symbol == '{}'".format(symbol))[
                    ["timestamp", "symbol", "side", "size", "price"]
                ]

                parser = lambda dt: parse_datetime(dt.replace("D", "T") + "+00:00")
                df.timestamp = pd.DatetimeIndex(df.timestamp.apply(parser))
                df = df.set_index("timestamp")
                ohlc = df.price.resample(interval).ohlc()

                ohlc_q.put([csv, ohlc])

    def updateHistoricalDataProcess(self):
        logger.debug("Start update history process")
        file_name = os.listdir("data")

        if file_name:
            start_dt = parse_datetime(file_name[-1][:-7])
        else:
            start_dt = datetime.datetime(2019, 12, 31)

        end_dt = datetime.datetime.now()

        for n in range(1, int((end_dt.date() - start_dt.date()).days)):
            date = start_dt + datetime.timedelta(n)
            logger.debug("Downloading {}".format(date.date()))
            self.downloadData(date.strftime("%Y%m%d"))

        logger.debug("Done update history process")

    def updateLiveData(self):
        self.live_info_q.put([self.symbols[self.index], self.interval])
        Process(
            target=self.updateLiveDataProcess,
            args=(self.live_info_q, self.live_ohlc_q),
            daemon=True,
        ).start()
        self.live_df, self.live_ohlc_df = self.live_ohlc_q.get()

    def updateLiveDataProcess(self, live_info_q, live_ohlc_q):
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

            logger.debug(
                "{} | {} {} {:.19} | Live queue {}".format(
                    s,
                    symbol,
                    interval,
                    str(last_dt.astimezone()),
                    self.live_ohlc_q.qsize(),
                )
            )

            i += 1
            if i % 5 == 0:
                df.to_csv(file_name)

    def getData(self, startTs=None, endTs=None, fetchLive=False):
        if startTs is not None:
            startDt = datetime.datetime.fromtimestamp(
                int(startTs), tz=datetime.timezone.utc
            )
            endDt = datetime.datetime.fromtimestamp(
                int(endTs), tz=datetime.timezone.utc
            )

            while self.ohlc_df.index[0] > startDt:
                df, ohlc_df = self.ohlc_q.get()
                logger.debug("OHLC | Queue: {}".format(self.ohlc_q.qsize()))
                self.df = pd.concat([df, self.df])
                self.ohlc_df = pd.concat([ohlc_df, self.ohlc_df])

            if fetchLive:
                self.live_df, self.live_ohlc_df = self.live_ohlc_q.get()

            ohlcIdx = self.ohlc_df.index
            mask = (ohlcIdx >= startDt) & (ohlcIdx <= endDt)
            ohlc = self.ohlc_df[mask]

            liveOhlcIdx = self.live_ohlc_df.index
            liveMask = (liveOhlcIdx >= startDt) & (liveOhlcIdx <= endDt)
            liveOhlc = self.live_ohlc_df[liveMask]

            data = pd.concat([ohlc, liveOhlc])
            data.index = data.index.astype("int64") // 1e09
            return self.ohlc_df.index[0].timestamp(), data.reset_index().to_numpy()

        else:
            data = pd.concat([self.ohlc_df, self.live_ohlc_df])
            data.index = data.index.astype("int64") // 1e09
            return data.reset_index().to_numpy()

    def setIndex(self, index):
        if index != self.index:
            self.index = index
        self.invalidateData()

    def setInterval(self, interval):
        if interval != self.interval:
            self.interval = interval
        self.invalidateData()

    def invalidateData(self):
        self.ohlc_info_q.put([self.symbols[self.index], self.interval])
        self.live_info_q.put([self.symbols[self.index], self.interval])

        self.df = pd.DataFrame()
        self.ohlc_df = pd.DataFrame()
        self.live_df = pd.DataFrame()
        self.live_ohlc_df = pd.DataFrame()

        while True:
            live_df, live_ohlc_df = self.live_ohlc_q.get()
            freq = live_ohlc_df.index.freq
            if (
                all(live_df["symbol"] == self.symbols[self.index])
                and self.interval == str(freq.n) + freq.name
            ):
                self.live_df = pd.concat([live_df, self.live_df])
                self.live_ohlc_df = pd.concat([live_ohlc_df, self.live_ohlc_df])
                break

        while True:
            df, ohlc_df = self.ohlc_q.get()
            freq = ohlc_df.index.freq
            if (
                all(df["symbol"] == self.symbols[self.index])
                and self.interval == str(freq.n) + freq.name
            ):
                self.df = pd.concat([df, self.df])
                self.ohlc_df = pd.concat([ohlc_df, self.ohlc_df])
                break

    def volumeOnPrice(self, startDt, endDt, num):
        live_df, _ = self.live_ohlc_q.get()

        df = self.df[self.df["symbol"] == self.symbols[self.index]]
        df = pd.concat([df, live_df])
        df = df[((df.index >= startDt) & (df.index <= endDt))]

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
    # db.updateHistoricalDataProcess()
    # start = datetime.datetime(2020, 11, 27, tzinfo=datetime.timezone.utc)
    # end = datetime.datetime(2020, 12, 3, tzinfo=datetime.timezone.utc)
    # db.getData(start, end)
    # db.setIndex(1)

    while True:
        pass
    #     sleep(5)
    #     print(db.df.info(memory_usage="deep"))

