# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_plottermanagerwindow.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtWidgets
from loader import Loader
from plotwindow import PlotWindow
from pathlib import Path


class PlotterManagerWindow(QtWidgets.QMainWindow):
    def __init__(self, plotters):
        super(PlotterManagerWindow, self).__init__()
        self.num_plotters = len(plotters)
        if not isinstance(plotters, list):
            plotters = [plotters]
        self.plotters = plotters

        self.setObjectName("PlotterManagerWindow")
        self.resize(400, 300)
        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName("verticalLayout")

        self.checkboxes = []
        for n in range(self.num_plotters):
            self.checkboxes.append(QtWidgets.QCheckBox(self.centralwidget))
            self.checkboxes[n].setChecked(True)
            self.checkboxes[n].setText(f'plotter #{n:d}: {self.plotters[n].loader.file_prefix}')
            self.checkboxes[n].setObjectName(f"plotter_checkbox_{n:d}")
            self.verticalLayout.addWidget(self.checkboxes[n])
            self.checkboxes[n].stateChanged.connect(lambda state, num=n: self.checkbox_changed(num))

        self.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(self)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 26))
        self.menubar.setObjectName("menubar")
        self.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(self)
        self.statusbar.setObjectName("statusbar")
        self.setStatusBar(self.statusbar)

        self.retranslateui()
        QtCore.QMetaObject.connectSlotsByName(self)

    def retranslateui(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("PlotterManagerWindow", "MainWindow"))

    def checkbox_changed(self, plotter_num):
        if self.checkboxes[plotter_num].isChecked():
            self.plotters[plotter_num].show()
        else:
            self.plotters[plotter_num].close()
        self.activateWindow()


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    keithley_logger_temp_path = Path('C:/', 'Users', 'Justin', 'Desktop', 'Working', 'Code', 'Keithley Logger Work')
    log_drive = Path(keithley_logger_temp_path, 'Log Drive', 'Fake Data')
    file_prefix = 'Fake Data'
    iongauge_data_loader = Loader(log_drive, file_prefix, quiet=True)
    plotter = PlotWindow(iongauge_data_loader)
    ui = PlotterManagerWindow([plotter])
    ui.show()
    sys.exit(app.exec_())
