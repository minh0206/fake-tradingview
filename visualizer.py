import datetime
import logging
import time

import numpy as np
import pyqtgraph as pg
from pyqtgraph import QtCore, QtGui
from pyqtgraph.dockarea import *

from candlestickItem import CandlestickItem
from utils import Worker, logger
from volumeProfileItem import VolumeProfileItem


class Visualizer(DockArea):
    def __init__(self, parent):
        super().__init__()
        self.db = parent.db

        # Candlestick init
        self.candlestick = CandlestickItem(self.db)
        self.volumeProfile = VolumeProfileItem(self.db)
        self.volumeProfile.onUpdate.connect(self.candlestick.update)

        self.candlestickWidget = pg.PlotWidget(
            self, axisItems={"bottom": pg.DateAxisItem()}
        )
        self.candlestickWidget.addItem(self.candlestick)
        self.candlestickWidget.addItem(self.volumeProfile)
        self.candlestickWidget.setMouseEnabled(x=True, y=False)
        self.candlestickWidget.enableAutoRange(x=False, y=True)
        self.candlestickWidget.setAutoVisible(x=False, y=True)
        self.candlestickWidget.showAxis("right")
        self.candlestickWidget.hideAxis("left")
        self.candlestickWidget.showGrid(True, True, 0.2)
        self.candlestickWidget.scene().sigMouseMoved.connect(
            self.candlestick.onMouseMoved
        )

        # Add dock
        self.d = Dock("OHLC", widget=self.candlestickWidget)
        self.addDock(self.d)

    def setIndex(self, index):
        # worker = Worker(self.candlestick.setIndex, index)
        # QtCore.QThreadPool.globalInstance().start(worker)
        self.candlestick.setIndex(index)

    def setInterval(self, interval):
        # worker = Worker(self.candlestick.setInterval, interval)
        # QtCore.QThreadPool.globalInstance().start(worker)
        self.candlestick.setInterval(interval)

