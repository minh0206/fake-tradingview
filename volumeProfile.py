import logging
from PyQt5 import QtWidgets, QtCore

from utils import logger


class VolumeProfile(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent, QtCore.Qt.Window)
        self.ui = Ui_VolumeProfile()
        self.ui.setupUi(self)

        self.ui.table.setColumnCount(4)
        self.ui.table.setHorizontalHeaderLabels(["Start date", "End date", "Alpha", ""])
        self.ui.table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch
        )

        self.ui.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        self.ui.btnAdd.clicked.connect(self.btnAddClicked)
        self.ui.btnDelete.clicked.connect(self.btnDeleteAllClicked)

        self.setNum(list(map(str, range(5, 35, 5))))

        self.volumeProfile = parent.visualizer.volumeProfile
        self.updateDate()

    def updateDate(self):
        indexDt = self.volumeProfile.getDate()

        self.ui.cbStart.clear()
        self.ui.cbStart.addItems(indexDt)
        self.ui.cbStart.setCurrentIndex(len(indexDt) - 1)

        self.ui.cbEnd.clear()
        self.ui.cbEnd.addItems(indexDt)
        self.ui.cbEnd.setCurrentIndex(len(indexDt) - 1)

    def setNum(self, num):
        self.ui.cbNum.clear()
        self.ui.cbNum.addItems(num)

    def deleteAll(self):
        self.ui.table.clearContents()
        self.ui.table.setRowCount(0)

        self.volumeProfile.removeAll()

    @QtCore.pyqtSlot()
    def btnAddClicked(self):
        start = self.ui.cbStart.currentIndex()
        end = self.ui.cbEnd.currentIndex()
        num = int(self.ui.cbNum.currentText())
        result = self.volumeProfile.addData(start, end, num)

        if result:
            row = self.ui.table.rowCount()
            self.ui.table.insertRow(row)

            slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            slider.setMinimum(25)
            slider.setMaximum(255)
            slider.setValue(127)
            slider.valueChanged.connect(self.sliderHandle)

            btn = QtWidgets.QPushButton("Delete")
            btn.clicked.connect(self.btnDeleteHandle)

            self.ui.table.setItem(
                row, 0, QtWidgets.QTableWidgetItem(self.ui.cbStart.currentText()),
            )
            self.ui.table.setItem(
                row, 1, QtWidgets.QTableWidgetItem(self.ui.cbEnd.currentText()),
            )
            self.ui.table.setCellWidget(row, 2, slider)
            self.ui.table.setCellWidget(row, 3, btn)

        else:
            QtWidgets.QMessageBox.critical(
                self, "Date error", "Invalid or duplicate date"
            )

    @QtCore.pyqtSlot()
    def btnDeleteHandle(self):
        button = self.sender()
        index = self.ui.table.indexAt(button.pos())
        if index.isValid():
            row = index.row()
            self.ui.table.removeRow(row)
            self.volumeProfile.removeData(row)

    @QtCore.pyqtSlot(int)
    def sliderHandle(self, value):
        slider = self.sender()
        index = self.ui.table.indexAt(slider.pos())
        if index.isValid():
            self.volumeProfile.setAlpha(index.row(), value)

    @QtCore.pyqtSlot()
    def btnDeleteAllClicked(self):
        self.deleteAll()


class Ui_VolumeProfile(object):
    def setupUi(self, VolumeProfile):
        VolumeProfile.setObjectName("VolumeProfile")
        VolumeProfile.resize(600, 300)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(VolumeProfile)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.splitter = QtWidgets.QSplitter(VolumeProfile)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.formLayoutWidget = QtWidgets.QWidget(self.splitter)
        self.formLayoutWidget.setObjectName("formLayoutWidget")
        self.formLayout = QtWidgets.QFormLayout(self.formLayoutWidget)
        self.formLayout.setContentsMargins(0, 0, 0, 0)
        self.formLayout.setObjectName("formLayout")
        self.startDateLabel = QtWidgets.QLabel(self.formLayoutWidget)
        self.startDateLabel.setObjectName("startDateLabel")
        self.formLayout.setWidget(
            0, QtWidgets.QFormLayout.LabelRole, self.startDateLabel
        )
        self.cbStart = QtWidgets.QComboBox(self.formLayoutWidget)
        self.cbStart.setObjectName("cb_start")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.cbStart)
        self.endDateLabel = QtWidgets.QLabel(self.formLayoutWidget)
        self.endDateLabel.setObjectName("endDateLabel")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.endDateLabel)
        self.cbEnd = QtWidgets.QComboBox(self.formLayoutWidget)
        self.cbEnd.setObjectName("cb_end")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.cbEnd)
        self.numOfBinsLabel = QtWidgets.QLabel(self.formLayoutWidget)
        self.numOfBinsLabel.setObjectName("numOfBinsLabel")
        self.formLayout.setWidget(
            2, QtWidgets.QFormLayout.LabelRole, self.numOfBinsLabel
        )
        self.cbNum = QtWidgets.QComboBox(self.formLayoutWidget)
        self.cbNum.setObjectName("cb_num")
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.cbNum)
        self.verticalLayoutWidget = QtWidgets.QWidget(self.splitter)
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.btnAdd = QtWidgets.QPushButton(self.verticalLayoutWidget)
        self.btnAdd.setObjectName("btn_add")
        self.verticalLayout.addWidget(self.btnAdd)
        self.btnDelete = QtWidgets.QPushButton(self.verticalLayoutWidget)
        self.btnDelete.setObjectName("btn_delete")
        self.verticalLayout.addWidget(self.btnDelete)
        self.verticalLayout_2.addWidget(self.splitter)
        self.table = QtWidgets.QTableWidget(VolumeProfile)
        self.table.setObjectName("table")
        self.verticalLayout_2.addWidget(self.table)
        self.startDateLabel.setBuddy(self.cbStart)
        self.endDateLabel.setBuddy(self.cbEnd)
        self.numOfBinsLabel.setBuddy(self.cbNum)

        self.retranslateUi(VolumeProfile)
        QtCore.QMetaObject.connectSlotsByName(VolumeProfile)

    def retranslateUi(self, VolumeProfile):
        _translate = QtCore.QCoreApplication.translate
        VolumeProfile.setWindowTitle(_translate("VolumeProfile", "Volume profile"))
        self.startDateLabel.setText(_translate("VolumeProfile", "Start date"))
        self.endDateLabel.setText(_translate("VolumeProfile", "End date"))
        self.numOfBinsLabel.setText(_translate("VolumeProfile", "Num of bins"))
        self.btnAdd.setText(_translate("VolumeProfile", "Add"))
        self.btnDelete.setText(_translate("VolumeProfile", "Delete all"))
