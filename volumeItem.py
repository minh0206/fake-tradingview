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

    def __init__(self, db):
        super().__init__()
        self.db = db
        # self.step = None
        # self.anchor = None
        # self.data = None
        # self.path = None
        # self.limit = 500
        # self.plotting = False

        self.autoRangeEnabled = True

        self._boundingRect = None
        self._boundsCache = [None, None]

    def updateBars(self, refresh=False):
        vb = self.getViewBox()
        if vb is None:
            self.plotting = False
            return  # no ViewBox yet
        else:
            xRange = vb.viewRange()[0]
            if xRange[1] - xRange[0] == 1:
                self.plotting = False
                return

        start, stop = xRange
        data = self.db.getDf(start, stop, refresh)

        try:
            step = data[1][0] - data[0][0]
        except IndexError:
            ds = 1
        else:
            ds = int((stop - start) / (step * self.limit)) + 1
            # logger.debug([ds, len(data)])

        if ds == 1:
            # Small enough to display with no intervention.
            visible = data
        else:
            # Here convert data into a down-sampled array suitable for visualizing.
            # Cut off to fix bar jitter
            chunk = data[: (len(data) // ds) * ds]
            anchor = (data[0][0] - self.anchor) / step
            offset = int(anchor % ds)
            if offset:
                chunk = chunk[ds - offset : -offset]
            visible = np.zeros((len(chunk) // ds, 5))

            # Reshape timestamp
            visible[:, 0] = chunk[: (len(chunk) // ds) * ds : ds, 0]

            # Reshape open
            _open = chunk[: (len(chunk) // ds) * ds, 1].reshape(len(chunk) // ds, ds)
            if np.isnan(_open).any():
                visible[:, 1] = self.filterNan(_open, first=True)
            else:
                visible[:, 1] = chunk[: (len(chunk) // ds) * ds : ds, 1]

            # Reshape high
            high = chunk[: (len(chunk) // ds) * ds, 2].reshape(len(chunk) // ds, ds)
            if np.isnan(high).any():
                high = np.nan_to_num(high, nan=-np.inf)
            visible[:, 2] = high.max(axis=1)

            # Reshape low
            low = chunk[: (len(chunk) // ds) * ds, 3].reshape(len(chunk) // ds, ds)
            if np.isnan(low).any():
                low = np.nan_to_num(low, nan=np.inf)
            visible[:, 3] = low.min(axis=1)

            # Reshape close
            close = chunk[: (len(chunk) // ds) * ds, 4].reshape(len(chunk) // ds, ds)
            if np.isnan(close).any():
                visible[:, 4] = self.filterNan(close, first=False)
            else:
                visible[:, 4] = chunk[: (len(chunk) // ds) * ds : ds, 4]

        self.setData(visible)  # update the plot
        self.resetTransform()
        self.plotting = False

    def viewRangeChanged(self):
        if not self.plotting:
            self.plotting = True
            worker = Worker(self.updateBars)
            QtCore.QThreadPool.globalInstance().start(worker)
            self.sigXRangeChanged.emit()
            self.sigResized.emit()

    def filterNan(self, inputArray, first):
        outputArray = []
        for array in inputArray:
            if np.isnan(array).all():
                outputArray.append(np.nan)
            else:
                if first:
                    outputArray.append(array[~np.isnan(array)][0])
                else:
                    outputArray.append(array[~np.isnan(array)][-1])

        return outputArray
