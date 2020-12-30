import logging
import sys
import time

import numpy as np
import pyqtgraph.console
from PyQt5 import QtCore, QtWidgets

from database import Database
from uiMain import Ui_MainWindow
from utils import logger
from visualizer import Visualizer
from volumeProfile import VolumeProfile


class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Init
        self.db = Database(0, "5T")
        self.visualizer = Visualizer(self)
        self.ui.verticalLayout.addWidget(self.visualizer.dockArea)
        self.volumeProfile = VolumeProfile(self)
        self.console = pyqtgraph.console.ConsoleWidget(
            namespace={"vs": self.visualizer}
        )

        # Auto update
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.visualizer.candlestick.refresh)
        self.timer.start(2000)

        # Tool menu
        self.ui.actionVolumeProfile.triggered.connect(self.actionVolumeProfile)
        self.ui.actionConsole.triggered.connect(self.console.show)

        # Indicator menu
        self.ui.actionVolume.toggled.connect(
            lambda checked: self.visualizer.toggleVolume(checked)
        )

        # Toolbar
        self.previousIndex = 7
        self.ui.cbInterval.setCurrentIndex(7)
        self.ui.cbInterval.activated.connect(self.cbIntervalSelect)
        self.ui.cbSymbol.currentIndexChanged.connect(self.cbSymbolSelect)

    @QtCore.pyqtSlot()
    def actionVolumeProfile(self):
        self.volumeProfile.updateDate()
        self.volumeProfile.show()

    @QtCore.pyqtSlot(int)
    def cbSymbolSelect(self, i):
        self.visualizer.setIndex(i)
        self.volumeProfile.deleteAll()

    @QtCore.pyqtSlot(int)
    def cbIntervalSelect(self, i):
        text = self.ui.cbInterval.currentText()

        if text == "-----":
            self.ui.cbInterval.setCurrentIndex(self.previousIndex)
        elif i != self.previousIndex:
            self.previousIndex = i
            if text[-1] == "s":
                interval = text.replace("s", "S")
            elif text[-1] == "m":
                interval = text.replace("m", "T")
            elif text[-1] == "h":
                interval = text.replace("h", "H")
            else:
                interval = text

            self.visualizer.setInterval(interval)

        self.ui.centralwidget.setFocus()


if __name__ == "__main__":
    qapp = QtWidgets.QApplication.instance()
    if not qapp:
        qapp = QtWidgets.QApplication(sys.argv)

    app = ApplicationWindow()
    # app.showMaximized()
    app.show()
    app.activateWindow()
    app.raise_()
    qapp.exec_()
