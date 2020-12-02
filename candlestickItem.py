import datetime

import numpy as np
import pyqtgraph as pg
from pyqtgraph import QtCore, QtGui

from utils import Worker, logger


class CandlestickItem(pg.GraphicsObject):
    onPlot = QtCore.pyqtSignal()

    def __init__(self, db):
        super().__init__()
        # Candlestick
        self.db = db
        self.ohlc = None
        self.data = None
        self.anchor = None
        self.step = None
        self.path = None
        self.limit = 500
        self.totalBars = 500
        self.plotting = False
        self._boundingRect = None
        self._boundsCache = [None, None]

        # Data init
        ohlc = self.db.ohlc(self.totalBars, fetch_live=True)
        self.setOHLC(ohlc)

        # Crosshair init
        self.vLine = pg.InfiniteLine(angle=90)
        self.vLine.setParentItem(self)
        self.hLine = pg.InfiniteLine(angle=0)
        self.hLine.setParentItem(self)

        # Text init
        self.vTxt = pg.TextItem(fill=(255, 255, 255, 50))
        self.vTxt.setParentItem(self)
        self.hTxt = pg.TextItem(fill=(255, 255, 255, 50))
        self.hTxt.setParentItem(self)

        # Connect signal
        self.onPlot.connect(self.updatePlotStatus)

    def plot(self, index=None, interval=None, fetch=0, live=False, resetLim=False):
        worker = Worker(self.plot_thread, index, interval, fetch, live, resetLim)
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

        # start = time.time()
        ohlc = self.db.ohlc(self.totalBars, live, index, interval)
        # logger.debug(
        #     "OHLC | Time: {:.3} | Len: {} | Queue: {}".format(
        #         time.time() - start, len(ohlc), self.db.ohlc_q.qsize()
        #     )
        # )

        if len(ohlc):
            self.setOHLC(ohlc)
            self.dataBounds(1)

        if resetLim:
            self.enableAutoRange()

        self.onPlot.emit()

    def updatePlotStatus(self):
        self.plotting = False

    def setOHLC(self, ohlc):
        ohlc.index = ohlc.index.astype("int64") // 1e09

        self.anchor = ohlc.index[0]
        self.step = ohlc.index[1] - ohlc.index[0]

        self.ohlc = ohlc.dropna().reset_index().to_numpy()
        self.updateOHLC()

    def updateOHLC(self):
        if self.ohlc is None:
            self.setData([])
            return

        vb = self.getViewBox()
        if vb is None:
            return  # no ViewBox yet
        else:
            xRange = vb.viewRange()[0]
            if xRange == [0, 1]:
                return
            else:
                dist = self.anchor - xRange[0]
                if not self.plotting and dist > 0:
                    numBars = int(dist / self.step)
                    self.plotting = True
                    self.plot(fetch=numBars)

        start = max(0, int(xRange[0]) - 1)
        stop = int(min(self.ohlc[-1][0], xRange[1] + 2))
        ds = int((stop - start) / (self.limit * self.step)) + 1

        timestamp = self.ohlc[:, 0]
        if ds == 1:
            # Small enough to display with no intervention.
            visible = self.ohlc[(timestamp > start) * (timestamp < stop)]
        else:
            # Here convert data into a down-sampled array suitable for visualizing.
            # Must do this piecewise to limit memory usage.
            chunk = self.ohlc[(timestamp > start) * (timestamp < stop)]

            # Cut off to fix bar jitter
            anchor = (chunk[0][0] - self.anchor) / self.step
            offset = int(anchor % ds)
            if offset:
                chunk = chunk[ds - offset : -offset]
            visible = np.zeros((len(chunk) // ds, 5))

            # Reshape timestamp
            visible[:, 0] = chunk[: (len(chunk) // ds) * ds : ds, 0]

            # Reshape open
            visible[:, 1] = chunk[: (len(chunk) // ds) * ds : ds, 1]

            # Reshape high
            high = (
                chunk[: (len(chunk) // ds) * ds, 2]
                .reshape(len(chunk) // ds, ds)
                .max(axis=1)
            )
            visible[:, 2] = high

            # Reshape low
            low = (
                chunk[: (len(chunk) // ds) * ds, 3]
                .reshape(len(chunk) // ds, ds)
                .min(axis=1)
            )
            visible[:, 3] = low

            # Reshape close
            visible[:, 4] = chunk[1 : (len(chunk) // ds) * ds : ds, 4]

        self.setData(visible)  # update the plot
        self.resetTransform()

    def setData(self, data):
        self.data = data

        self.invalidateBounds()
        self.prepareGeometryChange()
        self.informViewBoundsChanged()

        self.path = None
        self.update()

    def paint(self, p, *args):
        redBars, greenBars = self.getPath()

        p.setPen(pg.mkPen("g"))
        p.setBrush(pg.mkBrush("g"))
        p.drawPath(greenBars)

        p.setPen(pg.mkPen("r"))
        p.setBrush(pg.mkBrush("r"))
        p.drawPath(redBars)

    def getPath(self):
        if self.path is None:
            if self.data is None or len(self.data) == 0:
                self.path = [QtGui.QPainterPath(), QtGui.QPainterPath()]
            else:
                redBars = QtGui.QPainterPath()
                greenBars = QtGui.QPainterPath()

                w = (self.data[1][0] - self.data[0][0]) / 3.0
                for t, o, h, l, c in self.data:
                    if o > c:
                        redBars.moveTo(QtCore.QPointF(t, l))
                        redBars.lineTo(QtCore.QPointF(t, h))
                        redBars.addRect(QtCore.QRectF(t - w, o, w * 2, c - o))
                    else:
                        greenBars.moveTo(QtCore.QPointF(t, l))
                        greenBars.lineTo(QtCore.QPointF(t, h))
                        greenBars.addRect(QtCore.QRectF(t - w, o, w * 2, c - o))

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

        x = self.ohlc[:, 0]
        y = self.ohlc[:, 2:4]

        if x is None or len(x) == 0:
            return (None, None)

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

    def viewRangeChanged(self):
        # worker = Worker(self.updateOHLC)
        # QtCore.QThreadPool.globalInstance().start(worker)
        self.updateOHLC()

    def onMouseMoved(self, pos):
        mouse_point = self.getViewBox().mapSceneToView(pos)
        index = int(mouse_point.x())
        xlim, ylim = self.getViewBox().viewRange()
        x = round((index - self.anchor) / self.step)
        timestamp = self.anchor + x * self.step
        dt = datetime.datetime.fromtimestamp(timestamp)

        self.vLine.setPos(timestamp)
        self.hLine.setPos(mouse_point.y())

        self.vTxt.setText(dt.strftime("%d %b '%y  %H:%M:%S"))
        self.hTxt.setText("{:.2f}".format(mouse_point.y()))

        self.vTxt.setPos(timestamp, ylim[0] + 0.05 * (ylim[1] - ylim[0]))
        self.hTxt.setPos(xlim[1] - 0.05 * (xlim[1] - xlim[0]), mouse_point.y())

        dist = self.anchor - xlim[0]
        numBars = int(dist / self.step)
        if not self.plotting and numBars > 0:
            self.plotting = True
            self.plot(fetch=numBars)
