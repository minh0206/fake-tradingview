import datetime
import logging
import time
import numpy as np
import pyqtgraph as pg
from pyqtgraph import QtCore, QtGui
from pyqtgraph.dockarea import DockArea

from candlestickItem import CandlestickItem
from utils import Worker, logger
from volumeProfileItem import VolumeProfileItem
from volumeItem import volumeItem


class Visualizer:
    def __init__(self, parent):
        self.db = parent.db
        self.dockArea = DockArea(parent)
        self.mouseIndex = ""
        self.dateFormat = self.getDateFormat("T")

        # Text and crosshair
        self.hLines = {}
        self.hTexts = {}
        self.vLines = {}
        self.vText = None

        # Candlestick init
        self.candlestick = CandlestickItem(self.db)
        self.volumeProfile = VolumeProfileItem(self.db)
        self.volumeProfile.onUpdate.connect(self.candlestick.update)

        self.candlestickWidget = pg.PlotWidget(
            self.dockArea, axisItems={"bottom": pg.DateAxisItem()}
        )
        self.candlestickWidget.addItem(self.candlestick)
        self.candlestickWidget.addItem(self.volumeProfile)

        self.addPlot("ohlc", self.candlestickWidget, 2)

    def setIndex(self, index):
        worker = Worker(self.candlestick.setIndex, index)
        QtCore.QThreadPool.globalInstance().start(worker)
        self.volumeProfile.removeAll()

    def setInterval(self, interval):
        worker = Worker(self.candlestick.setInterval, interval)
        QtCore.QThreadPool.globalInstance().start(worker)
        self.dateFormat = self.getDateFormat(interval)

    def getDateFormat(self, interval):
        if interval.find("S") != -1:
            dtFormat = "%d %b '%y  %H:%M:%S"
        elif interval.find("T") != -1 or interval.find("H") != -1:
            dtFormat = "%d %b '%y  %H:%M"
        else:
            dtFormat = "%d %b '%y"

        return dtFormat

    def addPlot(self, name, plotWidget, stretch=1):
        if len(self.dockArea.docks):
            p = list(self.dockArea.docks.items())[-1][1].widgets[0].getPlotItem()
            p.getAxis("bottom").setStyle(showValues=False)
            plotWidget.setXLink(p)
            p.removeItem(self.vText)

        plotWidget.setMouseEnabled(x=True, y=False)
        plotWidget.enableAutoRange(x=False, y=True)
        plotWidget.setAutoVisible(x=False, y=True)
        plotWidget.showAxis("right")
        plotWidget.hideAxis("left")
        plotWidget.showGrid(True, True, 0.25)
        plotWidget.hideButtons()
        # plotWidget.setLimits(maxXRange=345600)
        plotWidget.scene().sigMouseMoved.connect(self.onMouseMoved)
        plotWidget.scene().sigMouseHover.connect(self.onMouseHover)

        dock = self.dockArea.addDock(
            name=name, autoOrientation=False, hideTitle=True, size=(1, stretch)
        )
        dock.addWidget(plotWidget)

        # Crosshair init
        hLine = pg.InfiniteLine(angle=0)
        plotWidget.addItem(hLine, ignoreBounds=True)

        vLine = pg.InfiniteLine(angle=90)
        vLine.setPen(pg.mkPen())
        plotWidget.addItem(vLine, ignoreBounds=True)

        # Text init
        self.vText = pg.TextItem(fill="k", anchor=(0, 1))
        plotWidget.addItem(self.vText, ignoreBounds=True)

        hText = pg.TextItem(fill="k", anchor=(1, 0.5))
        plotWidget.addItem(hText, ignoreBounds=True)

        self.hLines[name] = hLine
        self.hTexts[name] = hText
        self.vLines[name] = vLine

    def removePlot(self, name):
        self.dockArea.docks.get(name).close()
        self.dockArea.docks.pop(name).widgets[0].clear()

        self.hLines.pop(name)
        self.hTexts.pop(name)
        self.vLines.pop(name)

        p = list(self.dockArea.docks.items())[-1][1].widgets[0]
        p.getAxis("bottom").setStyle(showValues=True)

        self.vText = pg.TextItem(fill=(255, 255, 255, 50), anchor=(0, 1))
        p.addItem(self.vText, ignoreBounds=True)

    def toggleVolume(self, checked):
        if checked:
            volumeWidget = pg.PlotWidget(axisItems={"bottom": pg.DateAxisItem()})
            plotItem = volumeItem(self)
            volumeWidget.addItem(plotItem)
            self.addPlot("volume", volumeWidget)
        else:
            self.removePlot("volume")

    def onMouseMoved(self, pos):
        try:
            p = self.dockArea.docks.get(self.mouseIndex).widgets[0].getPlotItem()
            pLast = list(self.dockArea.docks.items())[-1][1].widgets[0].getPlotItem()
        except Exception:
            return

        xLim, _ = p.getViewBox().viewRange()
        _, yLim = pLast.getViewBox().viewRange()

        mousePoint = p.getViewBox().mapSceneToView(pos)
        index = int(mousePoint.x())
        x = round((index - self.candlestick.anchor) / self.candlestick.step)
        timestamp = self.candlestick.anchor + x * self.candlestick.step
        dt = datetime.datetime.fromtimestamp(timestamp)

        # Vertical line and text
        [vLine.setValue(timestamp) for vLine in self.vLines.values()]
        self.vText.setPos(timestamp, yLim[0])
        self.vText.setText(dt.strftime(self.dateFormat))

        # Horizontal line and text
        [hLine.setPen(pg.mkPen(None)) for hLine in self.hLines.values()]
        [hText.setPos(0, 0) for hText in self.hTexts.values()]
        if p.viewRect().contains(mousePoint):
            self.hLines[self.mouseIndex].setPen(pg.mkPen())
            self.hLines[self.mouseIndex].setValue(mousePoint.y())

            self.hTexts[self.mouseIndex].setColor(pg.mkColor(200, 200, 200))
            self.hTexts[self.mouseIndex].setText("{:,.2f}".format(mousePoint.y()))
            self.hTexts[self.mouseIndex].setPos(xLim[1], mousePoint.y())

    def onMouseHover(self, items):
        for name, dock in self.dockArea.docks.items():
            if dock.widgets[0].getPlotItem() in items:
                self.mouseIndex = name
                break

