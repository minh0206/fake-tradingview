import logging
import sys
import time

import numpy as np
from PyQt5 import QtCore, QtWidgets

from database import Database
from utils import logger
from visualizer import Visualizer
from volumeProfile import VolumeProfile


class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.db = Database(0, "5T")

        self.visualizer = Visualizer(self)
        self.ui.verticalLayout.addWidget(self.visualizer)

        self.volumeProfile = VolumeProfile(self)

        self.previousIndex = 7
        self.ui.cbInterval.setCurrentIndex(7)

        # self.console = pyqtgraph.console.ConsoleWidget(
        #     namespace={"vs": self.visualizer}
        # )
        # self.console.show()

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.updatePlot)

        self.ui.actionVolumeProfile.triggered.connect(self.actionVolumeProfile)
        self.ui.cbSymbol.currentIndexChanged.connect(self.cbSymbolSelect)
        self.ui.cbInterval.activated.connect(self.cbIntervalSelect)
        self.ui.cbRefresh.activated.connect(self.cbRefreshSelect)

    @QtCore.pyqtSlot()
    def actionVolumeProfile(self):
        self.volumeProfile.show()

    @QtCore.pyqtSlot(int)
    def cbSymbolSelect(self, i):
        self.visualizer.updatePlot(index=i)
        self.volumeProfile.deleteAll()

    @QtCore.pyqtSlot(int)
    def cbIntervalSelect(self, i):
        text = self.ui.cbInterval.currentText()

        if text == "-----":
            self.ui.cbInterval.setCurrentIndex(self.previousIndex)
        elif i != self.previousIndex:
            self.previousIndex = i
            if text[-1] == "s":
                text = text.replace("s", "S")
            elif text[-1] == "m":
                text = text.replace("m", "T")
            elif text[-1] == "h":
                text = text.replace("h", "H")
            self.visualizer.updatePlot(interval=text)

        self.ui.centralwidget.setFocus()

    @QtCore.pyqtSlot(int)
    def cbRefreshSelect(self, i):
        if i == 0:
            self.timer.stop()
            self.visualizer.updatePlot(live=True)
            self.ui.statusbar.showMessage("Refresh", 1500)
        else:
            text = self.ui.cbRefresh.currentText()
            t = int(text.replace("s", "")) * 1000
            self.timer.start(t)
            self.ui.statusbar.showMessage("Refresh every " + text, 1500)

    @QtCore.pyqtSlot()
    def updatePlot(self):
        self.visualizer.updatePlot(live=True)


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 600)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.cbSymbol = QtWidgets.QComboBox(self.centralwidget)
        self.cbSymbol.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.cbSymbol.setObjectName("cb_symbol")
        self.cbSymbol.addItem("")
        self.cbSymbol.addItem("")
        self.horizontalLayout.addWidget(self.cbSymbol)
        self.cbInterval = QtWidgets.QComboBox(self.centralwidget)
        self.cbInterval.setEditable(True)
        self.cbInterval.setInsertPolicy(QtWidgets.QComboBox.InsertAtBottom)
        self.cbInterval.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.cbInterval.setObjectName("cb_interval")
        self.cbInterval.addItem("")
        self.cbInterval.addItem("")
        self.cbInterval.addItem("")
        self.cbInterval.addItem("")
        self.cbInterval.addItem("")
        self.cbInterval.addItem("")
        self.cbInterval.addItem("")
        self.cbInterval.addItem("")
        self.cbInterval.addItem("")
        self.cbInterval.addItem("")
        self.cbInterval.addItem("")
        self.cbInterval.addItem("")
        self.cbInterval.addItem("")
        self.cbInterval.addItem("")
        self.cbInterval.addItem("")
        self.cbInterval.addItem("")
        self.cbInterval.addItem("")
        self.cbInterval.addItem("")
        self.cbInterval.addItem("")
        self.cbInterval.addItem("")
        self.cbInterval.addItem("")
        self.horizontalLayout.addWidget(self.cbInterval)
        self.cbRefresh = QtWidgets.QComboBox(self.centralwidget)
        self.cbRefresh.setObjectName("cb_refresh")
        self.cbRefresh.addItem("")
        self.cbRefresh.addItem("")
        self.cbRefresh.addItem("")
        self.cbRefresh.addItem("")
        self.cbRefresh.addItem("")
        self.horizontalLayout.addWidget(self.cbRefresh)
        spacerItem = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.horizontalLayout.addItem(spacerItem)
        self.verticalLayout.addLayout(self.horizontalLayout)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 26))
        self.menubar.setObjectName("menubar")
        self.menuTools = QtWidgets.QMenu(self.menubar)
        self.menuTools.setObjectName("menuTools")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionVolumeProfile = QtWidgets.QAction(MainWindow)
        self.actionVolumeProfile.setObjectName("actionVolume_profile")
        self.menuTools.addAction(self.actionVolumeProfile)
        self.menubar.addAction(self.menuTools.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Fake TradingView"))
        self.cbSymbol.setItemText(0, _translate("MainWindow", "XBTUSD"))
        self.cbSymbol.setItemText(1, _translate("MainWindow", "ETHUSD"))
        self.cbInterval.setItemText(0, _translate("MainWindow", "1s"))
        self.cbInterval.setItemText(1, _translate("MainWindow", "5s"))
        self.cbInterval.setItemText(2, _translate("MainWindow", "15s"))
        self.cbInterval.setItemText(3, _translate("MainWindow", "30s"))
        self.cbInterval.setItemText(4, _translate("MainWindow", "-----"))
        self.cbInterval.setItemText(5, _translate("MainWindow", "1m"))
        self.cbInterval.setItemText(6, _translate("MainWindow", "3m"))
        self.cbInterval.setItemText(7, _translate("MainWindow", "5m"))
        self.cbInterval.setItemText(8, _translate("MainWindow", "15m"))
        self.cbInterval.setItemText(9, _translate("MainWindow", "30m"))
        self.cbInterval.setItemText(10, _translate("MainWindow", "45m"))
        self.cbInterval.setItemText(11, _translate("MainWindow", "-----"))
        self.cbInterval.setItemText(12, _translate("MainWindow", "1h"))
        self.cbInterval.setItemText(13, _translate("MainWindow", "2h"))
        self.cbInterval.setItemText(14, _translate("MainWindow", "3h"))
        self.cbInterval.setItemText(15, _translate("MainWindow", "4h"))
        self.cbInterval.setItemText(16, _translate("MainWindow", "-----"))
        self.cbInterval.setItemText(17, _translate("MainWindow", "1D"))
        self.cbInterval.setItemText(18, _translate("MainWindow", "1W"))
        self.cbInterval.setItemText(19, _translate("MainWindow", "1M"))
        self.cbInterval.setItemText(20, _translate("MainWindow", "-----"))
        self.cbRefresh.setItemText(0, _translate("MainWindow", "Refresh"))
        self.cbRefresh.setItemText(1, _translate("MainWindow", "5s"))
        self.cbRefresh.setItemText(2, _translate("MainWindow", "10s"))
        self.cbRefresh.setItemText(3, _translate("MainWindow", "15s"))
        self.cbRefresh.setItemText(4, _translate("MainWindow", "20s"))
        self.menuTools.setTitle(_translate("MainWindow", "Tools"))
        self.actionVolumeProfile.setText(_translate("MainWindow", "Volume profile"))


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
