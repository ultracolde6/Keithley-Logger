import datetime
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
from ui_plotwindow import Ui_PlotWindow
import pandas as pd
import numpy as np


class PlotWorker(QtCore.QObject):
    def __init__(self, plotwindow):
        super(PlotWorker, self).__init__()
        self.plotwindow = plotwindow
        self.work_thread = QThread()
        self.work_thread.start()
        self.moveToThread(self.work_thread)

    def worker_update(self):
        self.plotwindow.updating = True
        self.plotwindow.update()
        self.plotwindow.updating = False


class PlotObject(QtCore.QObject):
    def __init__(self, plot_window, mode='multiplot'):
        super(PlotObject, self).__init__()
        self.plot_window = plot_window
        self.data_fields = self.plot_window.loader.get_header()[2:]
        self.n_data_fields = len(self.data_fields)
        self.mode = mode

        self.canvas = self.plot_window.canvas
        self.figure = self.plot_window.figure
        self.axes = self.configure_axes()

        self.plot_thread = QThread()
        self.plot_thread.start()
        self.moveToThread(self.plot_thread)

    def configure_axes(self):
        axes = []
        if self.mode == 'singleplot':
            axes = self.configure_singleplot_axes()
        elif self.mode == 'multiplot':
            axes = self.configure_multiplot_axes()
        return axes

    def configure_multiplot_axes(self):
        ax = self.figure.add_subplot(self.n_data_fields, 1, 1)
        axes = [ax]
        if self.n_data_fields > 1:
            for n in range(2, self.n_data_fields+1):
                ax = self.figure.add_subplot(self.n_data_fields, 1, n, sharex=axes[0])
                axes.append(ax)
        return axes

    def configure_singleplot_axes(self):
        ax = self.figure.add_subplot(1, 1, 1)
        axes = [ax]
        return axes

    def single_plot(self):
        plot_data = self.plot_window.data[self.data_fields]
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
            plot_data = self.plot_window.data[field]
            plot_data = self.clip_data(plot_data)
            ax = self.axes[n]
            ax.clear()
            try:
                plot_data.plot(ax=ax, style='.')
            except TypeError:
                print('No Data to plot')
            self.axis_scalings()
            # box = ax.get_position()
            # ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
            # ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
            self.canvas.draw()

    def clip_data(self, data):
        time_mask = np.logical_and(self.plot_window.start_datetime < data.index,
                                   data.index < self.plot_window.stop_datetime)
        clipped_data = data[time_mask]
        if self.plot_window.outlier_reject:
            clipped_data_std = np.std(clipped_data)
            clipped_data_mean = np.mean(clipped_data)
            clipped_zscore = (data - clipped_data_mean) / clipped_data_std
            clipped_data = clipped_data[np.abs(clipped_zscore) < self.plot_window.outlier_reject_level]
        return clipped_data

    def plot(self):
        self.plot_window.updating = True
        self.load()
        if self.mode == 'singleplot':
            self.single_plot()
        elif self.mode == 'multiplot':
            self.multi_plot()
        self.plot_window.updating = False
        return

    def load(self):
        if self.plot_window.tracking:
            self.plot_window.stop_datetime = datetime.datetime.now()
            self.plot_window.start_datetime = self.plot_window.stop_datetime - self.plot_window.history_delta
            self.plot_window.data = self.plot_window.loader.refresh_data(self.plot_window.start_datetime)
        else:
            self.plot_window.data = self.plot_window.loader.grab_dates(self.plot_window.start_datetime.date(),
                                                                       self.plot_window.stop_datetime.date())

    def axis_scalings(self):
        for ax in self.axes:
            if not self.plot_window.autoscale:
                ax.set_ylim(self.plot_window.ymin, self.plot_window.ymax)
            ax.set_yscale(self.plot_window.yscale)
            ax.set_ylabel(self.plot_window.ylabel)
            ax.set_xlabel('Time')
            ax.set_xlim(self.plot_window.start_datetime, self.plot_window.stop_datetime)


class PlotWindow(Ui_PlotWindow, QtWidgets.QMainWindow):
    update_signal = pyqtSignal()

    def __init__(self, loader, ylabel='Signal Level'):
        super(PlotWindow, self).__init__()
        self.loader = loader
        self.setupUi(self)

        self.canvas = self.plotwidget.canvas
        self.figure = self.canvas.figure
        # self.ax = None
        # self.set_axes()
        self.ylabel = ylabel
        self.plot_object = PlotObject(self)

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

        self.data = pd.DataFrame()
        self.paused = False
        self.pause_pushButton.clicked.connect(self.pause_resume_clicked)
        self.settings_pushButton.clicked.connect(self.update_settings)
        self.tracking = True
        self.updating = False
        self.refresh_timer = QtCore.QTimer(self)
        self.refresh_timer.timeout.connect(self.update)
        self.worker = PlotWorker(self)
        self.update_signal.connect(self.plot_object.plot)
        self.update_pushButton.clicked.connect(self.update)

        self.update_settings()
        self.update()
        self.show()
        self.refresh_timer.start(self.refresh_time)

    # def attempt_update(self):
    #     """
    #     The PlotWindow thread initiates the update process by first checking
    #     if the update process is already occurring. If so it aborts, otherwise it continues.
    #     The mechanism avoids generating a backlog of update requests in the plotting thread
    #     if there are delays in that thread.
    #     """
    #
    #     else:
    #         self.update()

    def update(self):
        if self.updating:
            curr_time = datetime.datetime.now()
            time_str = curr_time.strftime('%H:%M:%S')
            print(f'{time_str} Plot is currently updating. Cannot update until previous update is complete.')
            return
        if self.tracking:
            self.stop_datetime = datetime.datetime.now()
            self.start_datetime = self.stop_datetime - self.history_delta
            self.data = self.loader.refresh_data(self.start_datetime)
        else:
            self.data = self.loader.grab_dates(self.start_datetime.date(), self.stop_datetime.date())
        self.update_signal.emit()

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
                self.turn_off_tracking()
                self.stop_datetime = datetime.datetime.strptime(history_stopdate_text, '%y/%m/%d %H:%M:%S')
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

    def update_settings(self):
        self.update_yaxis_settings()
        self.update_refresh_settings()
        if self.xscale_tabWidget.currentIndex() == 0:
            self.set_xrange_history_mode()
        else:
            self.turn_off_tracking()
            self.set_xrange_range_mode()
        self.update()

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
        print('attempting to stop')
        self.refresh_timer.stop()
        print('stopped?')
        self.pause_pushButton.setText('Resume')
        self.paused = True

    def resume(self):
        self.refresh_timer.start(self.refresh_time)
        self.paused = False
        self.pause_pushButton.setText('Pause')


# class MagPlotWindow(PlotWindow):
#     def __init__(self, loader):
#         self.ax1 = None
#         self.ax2 = None
#         super(MagPlotWindow, self).__init__(loader)
#         self.autoscale_checkBox.setEnabled(False)
#         self.ymin_lineEdit.setEnabled(False)
#         self.ymax_lineEdit.setEnabled(False)
#
#     def set_axes(self):
#         self.ax1 = self.figure.add_subplot(211)
#         self.ax2 = self.figure.add_subplot(212, sharex=self.ax1)
#
#     def update(self):
#         if self.tracking:
#             self.stop_datetime = datetime.datetime.now()
#             self.start_datetime = self.stop_datetime - self.history_delta
#         self.loader.refresh_data(self.start_datetime)
#         data = self.loader.data
#         if data is None:
#             print('No data to plot')
#             return
#         self.ax1.clear()
#         self.ax2.clear()
#         try:
#             data.plot(ax=self.ax1)
#             (2*data).plot(ax=self.ax2)
#             self.axis_scalings()
#             for ax in [self.ax1, self.ax2]:
#                 box = ax.get_position()
#                 ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
#                 ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
#             self.canvas.draw()
#         except TypeError:
#             print('No Data to plot')
#
#     def axis_scalings(self):
#         for ax in [self.ax1, self.ax2]:
#             ax.set_yscale(self.yscale)
#             ax.set_xlim(self.start_datetime, self.stop_datetime)
