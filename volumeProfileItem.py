import numpy as np
import pandas as pd
import pyqtgraph as pg

from pyqtgraph import QtCore, QtGui
from sklearn.preprocessing import minmax_scale

from logger import logger


class VolumeProfileItem(pg.GraphicsObject):
    def __init__(self):
        super().__init__()
        self.vpData = []
        self.picture = QtGui.QPicture()
        self.textItems = []

    def setAlpha(self, index, value):
        self.vpData[index][4] = value
        self.updateVolumeProfile()

    def updateVolumeProfile(self):
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)

        for x, y, df, step, alpha in self.vpData:
            p.setPen(pg.mkPen(100, 100, 100, alpha))
            p.setBrush(pg.mkBrush(100, 100, 100, alpha))
            p.drawRect(QtCore.QRectF(x[0], y[1], x[1] - x[0], y[0] - y[1]))

            x_length = x[1] - x[0]
            x_pos = minmax_scale(df.to_numpy(), (0.1 * x_length, x_length / 2))

            for interval, width in zip(df.index, x_pos):
                p.setBrush(pg.mkBrush(255, 0, 0, alpha))
                p.drawRect(QtCore.QRectF(x[0], interval.left, width[0], step))

                p.setBrush(pg.mkBrush(0, 255, 0, alpha))
                p.drawRect(
                    QtCore.QRectF(x[0] + width[0], interval.left, width[1], step)
                )

        p.end()
        self.update()

    def addText(self, data):
        formatter = lambda x: str(round(x / 1e06, 2)) + "M"

        x, y, df, _, _ = data

        total = df.sum(axis=0)
        item = pg.TextItem(
            "Total: " + formatter(total[0]) + " X " + formatter(total[1])
        )
        item.setPos(x[0], y[0])
        item.setParentItem(self)

        items = [item]
        for interval, volume in zip(df.index, df.to_numpy()):
            item = pg.TextItem(
                formatter(volume[0]) + " X " + formatter(volume[1]), anchor=(0, 0.5),
            )
            item.setPos(x[0], interval.mid)
            item.setParentItem(self)
            items.append(item)

        self.textItems.append(items)

    def addVolumeProfile(self, data):
        if data[0] not in [x[0] for x in self.vpData]:
            self.vpData.append(data)
            self.updateVolumeProfile()
            self.addText(data)
            return "pass"
        else:
            return "dup"

    def removeVolumeProfile(self, index):
        for i in self.textItems[index]:
            self.scene().removeItem(i)
        self.textItems.pop(index)

        self.vpData.pop(index)
        self.updateVolumeProfile()

    def removeAllVolumeProfile(self):
        for _ in range(len(self.vpData)):
            for i in self.textItems[0]:
                i.scene().removeItem(i)
            self.textItems.pop(0)
            self.vpData.pop(0)

        self.updateVolumeProfile()

    def paint(self, p, *args):
        self.picture.play(p)

    def boundingRect(self):
        return QtCore.QRectF(self.picture.boundingRect())

    def dataBounds(self, ax, frac=1.0, orthoRange=None):
        return (None, None)

