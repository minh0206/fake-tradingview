import numpy as np
import pandas as pd
import pyqtgraph as pg

from pyqtgraph import QtCore, QtGui
from sklearn.preprocessing import minmax_scale

from logger import logger


class VolumeProfileItem(pg.GraphicsObject):
    def __init__(self):
        super().__init__()
        self.data = []
        self.picture = QtGui.QPicture()
        self.textItems = []
        self.formatter = (
            lambda x: str(round(x / 1e06, 2)) + "M"
            if x >= 1e06
            else str(round(x / 1e03, 2)) + "K"
        )

    def setAlpha(self, index, value):
        self.data[index][4] = value
        self.updateBar()
        # for i in self.text_items[index]:
        #     i.setColor(pg.mkColor(200, 200, 200, value))

    def updateBar(self):
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)

        for x, y, df, step, alpha in self.data:
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
        x, y, df, _, _ = data

        total = df.sum(axis=0)
        item = pg.TextItem(
            "Total: " + self.formatter(total[0]) + " X " + self.formatter(total[1])
        )
        item.setPos(x[0], y[0])
        item.setParentItem(self)

        items = [item]
        for interval, volume in zip(df.index, df.to_numpy()):
            item = pg.TextItem(
                self.formatter(volume[0]) + " X " + self.formatter(volume[1]),
                anchor=(0, 0.5),
            )
            item.setPos(x[0], interval.mid)
            item.setParentItem(self)
            items.append(item)

        self.textItems.append(items)

    def addData(self, data):
        if data[0] not in [x[0] for x in self.data]:
            self.data.append(data)
            self.updateBar()
            self.addText(data)
            return "pass"
        else:
            return "dup"

    def removeData(self, index):
        for i in self.textItems[index]:
            self.scene().removeItem(i)
        self.textItems.pop(index)

        self.data.pop(index)
        self.updateBar()

    def removeAll(self):
        for _ in range(len(self.data)):
            for i in self.textItems[0]:
                i.scene().removeItem(i)
            self.textItems.pop(0)
            self.data.pop(0)

        self.updateBar()

    def paint(self, p, *args):
        self.picture.play(p)

    def boundingRect(self):
        return QtCore.QRectF(self.picture.boundingRect())

    def dataBounds(self, ax, frac=1.0, orthoRange=None):
        return (None, None)

