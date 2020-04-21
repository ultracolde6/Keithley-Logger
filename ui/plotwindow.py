import sys
import time
import numpy as np
import pandas as pd
import datetime
from PyQt5 import QtCore, QtGui, QtWidgets
from ui_plotwindow import Ui_PlotWindow
from matplotlib.backends.backend_qt5agg import (FigureCanvasQTAgg, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure


class PlotWindow(Ui_PlotWindow, QtWidgets.QMainWindow):
    def __init__(self, loader):
        super(PlotWindow, self).__init__()
        self.loader = loader
        self.data = self.loader.data
        self.setupUi(self)
        self.canvas = self.plotwidget.canvas
        self.figure = self.canvas.figure
        self.ax = self.figure.add_subplot(111)
        self.update_button.clicked.connect(self.update)
        self.paused = False
        self.pause_button.clicked.connect(self.pause)
        self.settings_button.clicked.connect(self.update_settings)
        self.tracking = True

        self.ref_timer = QtCore.QTimer(self)
        self.ref_timer.timeout.connect(self.update)

        self.update_settings()
        self.ref_timer.start(self.refresh_time)

        self.sim_timer = QtCore.QTimer(self)
        self.sim_timer.timeout.connect(self.simulated_change)
        # self.sim_timer.start(100)

        self.update()

    def update_settings(self):
        self.autoscale = self.autoscale_checkBox.isChecked()
        self.outlier_reject = self.outlier_checkBox.isChecked()
        if self.lin_radioButton.isChecked():
            self.yscale = 'linear'
        elif self.log_radioButton.isChecked():
            self.yscale = 'log'
        try:
            self.ymin = float(self.ymin_lineEdit.text())
            self.ymax = float(self.ymax_lineEdit.text())
        except ValueError:
            print('invalid input for y limits, input must be real number')
            self.ymin_lineEdit.setText(str(self.ymin))
            self.ymax_lineEdit.setText(str(self.ymax))
        try:
            self.refresh_time = float(self.refresh_lineEdit.text())*1e3
            if not self.paused:
                self.ref_timer.stop()
                self.ref_timer.start(self.refresh_time)
        except ValueError:
                print('invalid input for refresh time, input must be real number')
        history_stopdate_text = self.history_stopdate_lineEdit.text()
        if history_stopdate_text.lower()=='now':
            self.x_stopdate = datetime.datetime.now()
            self.tracking = True
        else:
            try:
                self.x_stopdate = datetime.datetime.strptime(history_stopdate_text, '%y/%m/%d %H:%M:%S')
            except ValueError:
                print('invalid input for stop date, input must be formatted as YY/MM/DD HH:MM:SS')
        try:
            self.history_days = int(self.days_lineEdit.text())
            self.days_lineEdit.setText(str(self.history_days))
            self.history_hours = int(self.hours_lineEdit.text())
            self.hours_lineEdit.setText(str(self.history_hours))
            self.history_minutes = int(self.minutes_lineEdit.text())
            self.minutes_lineEdit.setText(str(self.history_minutes))
        except ValueError:
            print('invalid input for plot history, all inputs must be real integers')
        self.history_delta = datetime.timedelta(days=self.history_days,
                                           hours=self.history_hours,
                                           minutes=self.history_minutes)
        self.x_startdate = self.x_stopdate - self.history_delta

    def update(self):
        if self.tracking:
            self.x_stopdate = datetime.datetime.now()
            self.x_startdate = self.x_stopdate - self.history_delta
        self.loader.refresh_data(self.x_startdate)
        self.data = self.loader.data
        if self.data is None:
            print('No data to plot')
            return
        self.ax.clear()
        try:
            self.data.plot(ax=self.ax)
            self.axis_scalings()
            box = self.ax.get_position()
            self.ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
            self.ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
            self.canvas.draw()
        except TypeError:
            print('No Data to plot')

    # def plot(self):
    #     if self.data is None:
    #         print('No data to plot')
    #         return
    #     self.get_state()
    #     self.ax.clear()
    #     self.data.plot(ax=self.ax)
    #     self.axis_scalings()
    #     box = self.ax.get_position()
    #     self.ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
    #     self.ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    #     self.canvas.draw()

    def pause(self):
        if not self.paused:
            self.ref_timer.stop()
            self.pause_button.setText('Resume')
            self.paused = True
        else:
            self.ref_timer.start(self.refresh_time)
            self.paused = False

            self.pause_button.setText('Pause')

    def axis_scalings(self):
        if not self.autoscale:
            self.ax.set_ylim(self.ymin, self.ymax)
        self.ax.set_yscale(self.yscale)
        self.ax.set_xlim(self.x_startdate, self.x_stopdate)

    def simulated_change(self):
        self.minutes_lineEdit.setText(str(int(self.minutes_lineEdit.text())+1))


def grab_data(start_datetime, stop_datetime):
    file_name = 'Bake 2 2019-12-28.csv'
    datetime_format = '%Y-%m-%d %H:%M:%S'
    data = pd.DataFrame(columns=['time', 'vals'])
    read_columns = ['date', 'time', 'T1', 'T2', 'T3', 'T4', 'T5', 'T6']
    data = pd.read_csv(file_name,
                       header=None,
                       names=read_columns,
                       parse_dates={'timestamp': ['date', 'time']},
                       index_col='timestamp')
    data.index = pd.to_datetime(data.index, format=datetime_format)
    time_mask = np.logical_and(np.array(start_datetime < data.index), np.array(data.index < stop_datetime))
    data = data.loc[time_mask]
    return data


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    # MainWindow = QtWidgets.QMainWindow()
    p = PlotWindow()
    p.show()
    t_start = datetime.datetime(year=2019, month=12, day=28, hour=6, minute=30, second=5)
    t_stop = datetime.datetime(year=2019, month=12, day=28, hour=10, minute=30, second=5)
    data = grab_data(t_start, t_stop)
    p.data = data
    p.plot()
    sys.exit(app.exec_())

# if __name__ == "__main__":
#     import sys
#
#     app = QtWidgets.QApplication(sys.argv)
#     PlotWindow = QtWidgets.QMainWindow()
#     ui = Ui_PlotWindow()
#     ui.setupUi(PlotWindow)
#     PlotWindow.show()
#     sys.exit(app.exec_())