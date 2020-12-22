from datetime import datetime, timezone
from time import time

import numpy as np
import pyqtgraph as pg
from pyqtgraph import QtCore, QtGui

from utils import logger


class barGraphItem(pg.GraphicsObject):
    def __init__(self):
        super().__init__()
        self.data = None
        self.path = None

        self.autoRangeEnabled = True
        self._boundingRect = None
        self._boundsCache = [None, None]

    def setData(self, data):
        self.data = data

        self.invalidateBounds()
        self.prepareGeometryChange()
        self.informViewBoundsChanged()

        self.path = None
        self.update()

    def paint(self, p, *args):
        redBars, greenBars = self.getPath()

        p.setPen(pg.mkPen("k"))
        p.setBrush(pg.mkBrush(0, 255, 0, 255))
        p.drawPath(greenBars)

        p.setBrush(pg.mkBrush(255, 0, 0, 255))
        p.drawPath(redBars)

    def getPath(self):
        if self.path is None:
            if self.data is None or len(self.data) < 2:
                self.path = [QtGui.QPainterPath(), QtGui.QPainterPath()]
            else:
                redBars = QtGui.QPainterPath()
                greenBars = QtGui.QPainterPath()

                step = self.data[1][0] - self.data[0][0]
                w = step / 3.0
                for t, buy, sell in self.data:
                    if buy + sell != 0:
                        redBars.addRect(QtCore.QRectF(t - w, 0, w * 2, sell))
                        greenBars.addRect(QtCore.QRectF(t - w, sell, w * 2, buy))

                self.path = [redBars, greenBars]

        return self.path

    def invalidateBounds(self):
        self._boundingRect = None
        self._boundsCache = [None, None]

    def boundingRect(self):
        if self._boundingRect is None:
            (xmn, xmx) = self.dataBounds(ax=0)
            (ymn, ymx) = self.dataBounds(ax=1)
            if xmn is None or ymn is None:
                return QtCore.QRectF()

            px = py = 0.0
            self._boundingRect = QtCore.QRectF(
                xmn - px, ymn - py, (2 * px) + xmx - xmn, (2 * py) + ymx - ymn
            )

        return self._boundingRect

    def dataBounds(self, ax, frac=1.0, orthoRange=None):
        cache = self._boundsCache[ax]
        if cache is not None and cache[0] == (frac, orthoRange):
            return cache[1]

        if self.data is None:
            return (None, None)

        zeros = np.zeros((len(self.data), 1))
        total = self.data[:, 1:2] + self.data[:, 2:3]
        x = self.data[:, 0]
        y = np.append(zeros, total, axis=1)

        if ax == 0:
            d = x
            d2 = y
        elif ax == 1:
            d = y
            d2 = x

        if orthoRange is not None:
            mask = (d2 >= orthoRange[0]) * (d2 <= orthoRange[1])
            d = d[mask]

        if len(d) == 0:
            return (None, None)

        b = (np.nanmin(d), np.nanmax(d))

        if any(np.isinf(b)):
            mask = np.isfinite(d)
            d = d[mask]
            if len(d) == 0:
                return (None, None)
            b = (d.min(), d.max())

        self._boundsCache[ax] = [(frac, orthoRange), b]
        return b

    def viewTransformChanged(self):
        self.invalidateBounds()
        self.prepareGeometryChange()


# if __name__ == "__main__":
#     import sys

#     data = np.array(
#         [  ## fields are (time, open, close, min, max).
#             [1.0, 10, 13],
#             [2.0, 13, 17],
#             [3.0, 17, 14],
#             [4.0, 14, 15],
#             [5.0, 15, 9],
#             [6.0, 9, 15],
#         ]
#     )

#     item = barGraphItem()
#     item.setData(data)
#     plt = pg.plot()
#     plt.addItem(item)
#     plt.setWindowTitle("pyqtgraph example: customGraphicsItem")
#     if sys.flags.interactive != 1 or not hasattr(QtCore, "PYQT_VERSION"):
#         pg.QtGui.QApplication.exec_()
