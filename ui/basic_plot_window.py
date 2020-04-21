# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'basic_plot_window.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_PlotWindow(object):
    def setupUi(self, PlotWindow):
        PlotWindow.setObjectName("PlotWindow")
        PlotWindow.resize(800, 600)
        self.centralwidget = QtWidgets.QWidget(PlotWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.figurewidget = PlotWidget(self.centralwidget)
        self.figurewidget.setMinimumSize(QtCore.QSize(0, 100))
        self.figurewidget.setObjectName("figurewidget")
        self.verticalLayout_2.addWidget(self.figurewidget)
        PlotWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(PlotWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 26))
        self.menubar.setObjectName("menubar")
        PlotWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(PlotWindow)
        self.statusbar.setObjectName("statusbar")
        PlotWindow.setStatusBar(self.statusbar)

        self.retranslateUi(PlotWindow)
        QtCore.QMetaObject.connectSlotsByName(PlotWindow)

    def retranslateUi(self, PlotWindow):
        _translate = QtCore.QCoreApplication.translate
        PlotWindow.setWindowTitle(_translate("PlotWindow", "MainWindow"))
from plotwidget import PlotWidget


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    PlotWindow = QtWidgets.QMainWindow()
    ui = Ui_PlotWindow()
    ui.setupUi(PlotWindow)
    PlotWindow.show()
    sys.exit(app.exec_())
