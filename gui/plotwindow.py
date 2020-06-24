import datetime
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal
from ui_plotwindow import Ui_PlotWindow
import pandas as pd
import numpy as np


class PlotWorker(QtCore.QObject):
    def __init__(self, plot_window):
        super(PlotWorker, self).__init__()
        self.plot_window = plot_window
        self.work_thread = QThread()
        self.work_thread.start()
        self.moveToThread(self.work_thread)

    def run_update(self):
        self.plot_window.plot()

    def run_configure_axes(self):
        self.plot_window.configure_axes()


class PlotWindow(Ui_PlotWindow, QtWidgets.QMainWindow):
    update_signal = pyqtSignal()
    reconfigure_plot_signal = pyqtSignal()

    def __init__(self, loader, ylabel='Signal Level'):
        super(PlotWindow, self).__init__()
        self.loader = loader
        self.setupUi(self)

        self.canvas = self.plotwidget.canvas
        self.figure = self.canvas.figure
        self.axes = None
        self.ylabel = ylabel
        self.plot_worker = PlotWorker(self)

        self.data_fields = self.loader.get_header()[2:]
        self.n_data_fields = len(self.data_fields)

        self.autoscale = None
        self.outlier_reject = None
        self.yscale = None
        self.ymin = None
        self.ymax = None
        self.refresh_time = 30
        self.stop_datetime = None
        self.start_datetime = None
        self.history_days = None
        self.history_hours = None
        self.history_minutes = None
        self.history_delta = None
        self.outlier_reject_level = 2
        self.plot_mode = 'singleplot'

        self.data = pd.DataFrame()
        self.paused = False
        self.pause_pushButton.clicked.connect(self.pause_resume_clicked)
        self.settings_pushButton.clicked.connect(self.update_settings)
        self.tracking = True
        self.updating = False
        self.refresh_timer = QtCore.QTimer(self)
        self.refresh_timer.timeout.connect(self.update)
        self.update_signal.connect(self.plot_worker.run_update)
        self.update_pushButton.clicked.connect(self.update)
        self.reconfigure_plot_signal.connect(self.plot_worker.run_configure_axes)

        self.reconfigure_plot_signal.emit()
        self.update_settings()
        self.update()
        self.show()
        self.refresh_timer.start(self.refresh_time)

    def configure_axes(self):
        self.figure.clear()
        axes = []

        if self.plot_mode == 'singleplot':
            axes = self.configure_singleplot_axes()
        elif self.plot_mode == 'multiplot':
            axes = self.configure_multiplot_axes()
        self.axes = axes

    def configure_singleplot_axes(self):
        ax = self.figure.add_subplot(1, 1, 1)
        axes = [ax]
        return axes

    def configure_multiplot_axes(self):
        ax = self.figure.add_subplot(self.n_data_fields, 1, 1)
        axes = [ax]
        if self.n_data_fields > 1:
            for n in range(2, self.n_data_fields + 1):
                ax = self.figure.add_subplot(self.n_data_fields, 1, n, sharex=axes[0])
                axes.append(ax)
        return axes

    def plot(self):
        self.updating = True
        self.load()
        if self.plot_mode == 'singleplot':
            self.single_plot()
        elif self.plot_mode == 'multiplot':
            self.multi_plot()
        self.updating = False

    def single_plot(self):
        plot_data = self.data[self.data_fields]
        plot_data = self.clip_data(plot_data)
        ax = self.axes[0]
        ax.clear()
        try:
            plot_data.plot(ax=ax, style='.')
        except TypeError:
            print('No Data to plot')
        self.axis_scalings()
        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        self.canvas.draw()

    def multi_plot(self):
        for n, field in enumerate(self.data_fields):
            plot_data = self.data[field]
            plot_data = self.clip_data(plot_data)
            ax = self.axes[n]
            ax.clear()
            try:
                plot_data.plot(ax=ax, style='.')
            except TypeError:
                print('No Data to plot')
            self.axis_scalings()
            self.canvas.draw()

    def clip_data(self, data):
        time_mask = np.logical_and(self.start_datetime < data.index,
                                   data.index < self.stop_datetime)
        clipped_data = data[time_mask]
        if self.outlier_reject:
            clipped_data_std = np.std(clipped_data)
            clipped_data_mean = np.mean(clipped_data)
            clipped_zscore = (data - clipped_data_mean) / clipped_data_std
            clipped_data = clipped_data[np.abs(clipped_zscore) < self.outlier_reject_level]
        return clipped_data

    def load(self):
        if self.tracking:
            self.stop_datetime = datetime.datetime.now()
            self.start_datetime = self.stop_datetime - self.history_delta
            self.data = self.loader.refresh_data(self.start_datetime)
        else:
            self.data = self.loader.grab_dates(self.start_datetime.date(), self.stop_datetime.date())

    def axis_scalings(self):
        for ax in self.axes:
            if not self.autoscale:
                ax.set_ylim(self.ymin, self.ymax)
            ax.set_yscale(self.yscale)
            ax.set_ylabel(self.ylabel)
            ax.set_xlabel('Time')
            ax.set_xlim(self.start_datetime, self.stop_datetime)

    def update(self):
        """
        The PlotWindow thread initiates the update process by first checking
        if the update process is already occurring. If so it aborts, otherwise it continues.
        The mechanism avoids generating a backlog of update requests in the plotting thread
        if there are delays in that thread.
        """
        if self.updating:
            curr_time = datetime.datetime.now()
            time_str = curr_time.strftime('%H:%M:%S')
            print(f'{time_str} Plot is currently updating. Cannot update until previous update is complete.')
            return
        self.update_signal.emit()

    def update_settings(self):
        self.pause()
        self.update_yaxis_settings()
        self.update_refresh_settings()
        if self.xscale_tabWidget.currentIndex() == 0:
            self.set_xrange_history_mode()
        elif self.xscale_tabWidget.currentIndex() == 1:
            self.turn_off_tracking()
            self.set_xrange_range_mode()
        if self.single_plot_radioButton.isChecked():
            self.plot_mode = 'singleplot'
        elif self.multi_plot_radioButton.isChecked():
            self.plot_mode = 'multiplot'
        self.reconfigure_plot_signal.emit()
        self.update()
        self.resume()

    def update_yaxis_settings(self):
        self.autoscale = self.autoscale_checkBox.isChecked()
        self.outlier_reject = self.outlier_checkBox.isChecked()
        try:
            self.outlier_reject_level = round(abs(float(self.outlier_reject_level_lineEdit.text())), 2)
            self.outlier_reject_level_lineEdit.setText(f'{self.outlier_reject_level:.2f}')
        except ValueError:
            print('invalid input for outlier reject level, input must be real number')
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

    def update_refresh_settings(self):
        try:
            self.refresh_time = int(float(self.refresh_lineEdit.text())*1e3)
            if not self.paused:
                self.refresh_timer.stop()
                self.refresh_timer.start(self.refresh_time)
        except ValueError:
            print('invalid input for refresh time, input must be real number')
        self.refresh_lineEdit.setText(f'{self.refresh_time*1e-3:.3f}')

    def set_xrange_history_mode(self):
        history_stopdate_text = self.history_stopdate_lineEdit.text()
        if history_stopdate_text.lower() == 'now':
            self.stop_datetime = datetime.datetime.now()
            self.turn_on_tracking()
        else:
            try:
                self.stop_datetime = datetime.datetime.strptime(history_stopdate_text, '%y/%m/%d %H:%M:%S')
                self.turn_off_tracking()
            except ValueError:
                print('invalid input for stop date, input must be formatted as YY/MM/DD HH:MM:SS')
        try:
            self.history_days = int(self.days_lineEdit.text())
            self.history_hours = int(self.hours_lineEdit.text())
            self.history_minutes = int(self.minutes_lineEdit.text())
        except ValueError:
            print('invalid input for plot history, all inputs must be integers')
        self.days_lineEdit.setText(str(self.history_days))
        self.hours_lineEdit.setText(str(self.history_hours))
        self.minutes_lineEdit.setText(str(self.history_minutes))
        self.history_delta = datetime.timedelta(days=self.history_days,
                                                hours=self.history_hours,
                                                minutes=self.history_minutes)
        self.start_datetime = self.stop_datetime - self.history_delta

    def set_xrange_range_mode(self):
        startdate_text = self.range_startdate_lineEdit.text()
        stopdate_text = self.range_stopdate_lineEdit.text()
        try:
            self.start_datetime = datetime.datetime.strptime(startdate_text, '%y/%m/%d %H:%M:%S')
            self.stop_datetime = datetime.datetime.strptime(stopdate_text, '%y/%m/%d %H:%M:%S')
        except ValueError:
            print('invalid input for start or stop date, input must be formatted as YY/MM/DD HH:MM:SS')

    def turn_on_tracking(self):
        if not self.tracking:
            self.resume()
            self.pause_pushButton.setEnabled(True)
            self.tracking = True

    def turn_off_tracking(self):
        if self.tracking:
            self.pause()
            self.pause_pushButton.setEnabled(False)
            self.pause_pushButton.setText('Tracking Disabled')
            self.tracking = False

    def pause_resume_clicked(self):
        if not self.paused:
            self.pause()
        else:
            self.resume()

    def pause(self):
        self.refresh_timer.stop()
        self.pause_pushButton.setText('Resume')
        self.paused = True

    def resume(self):
        self.refresh_timer.start(self.refresh_time)
        self.pause_pushButton.setText('Pause')
        self.paused = False
