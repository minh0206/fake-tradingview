import datetime
import logging
import time

import numpy as np
import pyqtgraph as pg
from pyqtgraph import QtCore, QtGui

from candlestickItem import CandlestickItem
from logger import logger
from volumeProfileItem import VolumeProfileItem


class Visualizer(pg.PlotWidget):
    onPlot = QtCore.pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent, axisItems={"bottom": pg.DateAxisItem()})

        self.db = parent.db

        self.totalBars = 500
        self.plotting = False

        ohlc = self.db.ohlc(self.totalBars, fetch_live=True)

        # Candlestick init
        self.candlestick = CandlestickItem()
        self.candlestick.setOHLC(ohlc)
        self.addItem(self.candlestick)

        # Volume profile init
        self.volumeProfile = VolumeProfileItem()
        self.addItem(self.volumeProfile)

        # PlotItem init
        self.setMouseEnabled(x=True, y=False)
        self.enableAutoRange(x=False, y=True)
        self.setAutoVisible(x=False, y=True)
        self.showAxis("right")
        self.hideAxis("left")
        self.showGrid(True, True, 0.2)
        self.scene().sigMouseMoved.connect(self.candlestick.onMouseMoved)

        self.onPlot.connect(self.updatePlotStatus)

    def plot(self, index=None, interval=None, fetch=0, live=False, resetLim=False):
        worker = self.Worker(self.plot_thread, index, interval, fetch, live, resetLim)
        QtCore.QThreadPool.globalInstance().start(worker)
        # self.plot_thread(index, interval, fetch, live, reset_lim)

    def plot_thread(
        self, index=None, interval=None, fetch=0, live=False, resetLim=False
    ):
        if resetLim:
            if interval[-1] == "S":
                self.totalBars = 10000
            elif interval[-1] == "T":
                self.totalBars = 100
            elif interval[-1] == "H":
                self.totalBars = 50

        if fetch:
            self.totalBars += fetch

        start = time.time()
        ohlc = self.db.ohlc(self.totalBars, live, index, interval)
        logger.debug(
            "OHLC | Time: {:.3} | Len: {} | Queue: {}".format(
                time.time() - start, len(ohlc), self.db.ohlc_q.qsize()
            )
        )

        if len(ohlc):
            self.candlestick.setOHLC(ohlc)
            self.candlestick.dataBounds(1)

        if resetLim:
            self.enableAutoRange()

        self.onPlot.emit()

    def updatePlotStatus(self):
        self.plotting = False

    class Worker(QtCore.QRunnable):
        def __init__(self, fn, *args, **kwargs):
            super().__init__()
            self.fn = fn
            self.args = args
            self.kwargs = kwargs

        @QtCore.pyqtSlot()
        def run(self):
            self.fn(*self.args, **self.kwargs)

