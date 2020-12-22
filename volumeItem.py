from barGraphItem import barGraphItem

from datetime import datetime, timezone
from time import time

import numpy as np
import pyqtgraph as pg
from pyqtgraph import QtCore, QtGui

from utils import Worker, logger


class volumeItem(barGraphItem):
    sigXRangeChanged = QtCore.pyqtSignal()
    sigResized = QtCore.pyqtSignal()
    onUpdate = QtCore.pyqtSignal()

    def __init__(self, parent):
        super().__init__()
        self.db = parent.db
        self.candlestick = parent.candlestick
        self.step = None
        self.anchor = None
        self.limit = 500
        self.plotting = False

    def updateBars(self):
        vb = self.getViewBox()
        if vb is None:
            self.plotting = False
            return  # no ViewBox yet

        start = self.candlestick.data[0][0]
        stop = self.candlestick.data[-1][0]
        ds = self.candlestick.ds
        data = self.db.getVolume(start, stop)

        if ds == 1:
            if np.isnan(data).any():
                visible = np.nan_to_num(data, nan=0)
            else:
                visible = data
        else:
            chunk = data[: (len(data) // ds) * ds]
            visible = np.zeros((len(chunk) // ds, 3))

            # Reshape timestamp
            visible[:, 0] = chunk[: (len(chunk) // ds) * ds : ds, 0]

            # Reshape buy
            buy = chunk[: (len(chunk) // ds) * ds, 1].reshape(len(chunk) // ds, ds)
            if np.isnan(buy).any():
                buy = np.nan_to_num(buy, nan=0)
            visible[:, 1] = buy.sum(axis=1)

            # Reshape sell
            sell = chunk[: (len(chunk) // ds) * ds, 2].reshape(len(chunk) // ds, ds)
            if np.isnan(sell).any():
                sell = np.nan_to_num(sell, nan=0)
            visible[:, 2] = sell.sum(axis=1)

        self.setData(visible)  # update the plot
        self.resetTransform()
        self.plotting = False

    def viewRangeChanged(self):
        # self.updateBars()
        if not self.plotting:
            self.plotting = True
            worker = Worker(self.updateBars)
            QtCore.QThreadPool.globalInstance().start(worker)
            self.sigXRangeChanged.emit()
            self.sigResized.emit()
