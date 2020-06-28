import datetime
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal
from ui_plotwindow import Ui_PlotWindow
import pandas as pd
import numpy as np
from pathlib import Path


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

    def save(self):
        self.plot_window.save_plot()


class PlotWindow(Ui_PlotWindow, QtWidgets.QMainWindow):
    update_signal = pyqtSignal()
    reconfigure_plot_signal = pyqtSignal()

    def __init__(self, loader, ylabel='Signal Level', units_label='(a.u.)', save_path=None, conv_func=(lambda x: x),
                 plot_mode='singleplot', yscale='linear', save_freq=int(10e3)):
        super(PlotWindow, self).__init__()
        self.setupUi(self)

        self.loader = loader
        self.ylabel = ylabel
        self.units_label = units_label
        self.save_path = save_path
        if self.save_path is None:
            self.save_path = self.loader.log_drive
        self.conv_func = conv_func
        self.plot_mode = plot_mode
        self.yscale = yscale
        self.save_freq = save_freq

        self.canvas = self.plotwidget.canvas
        self.figure = self.canvas.figure
        self.axes = None
        self.plot_worker = PlotWorker(self)

        self.data_fields = self.loader.get_header()[2:]
        self.n_data_fields = len(self.data_fields)
        if self.n_data_fields == 1:
            self.multi_plot_radioButton.setEnabled(False)
        self.data = pd.DataFrame()

        if self.yscale == 'linear':
            self.lin_radioButton.setChecked(True)
        elif self.yscale == 'log':
            self.log_radioButton.setChecked(True)
        if self.plot_mode == 'singleplot':
            self.single_plot_radioButton.setChecked(True)
        elif self.plot_mode == 'multiplot':
            self.multi_plot_radioButton.setChecked(True)

        self.autoscale = None
        self.outlier_reject = None
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

        self.save_timer = QtCore.QTimer(self)
        self.save_timer.timeout.connect(self.plot_worker.save)
        self.save_timer.start(self.save_freq)

        self.reconfigure_plot_signal.emit()
        self.update_settings()
        self.update()
        self.setWindowTitle(f'{self.loader.file_prefix} Plotter')
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
        self.figure.set_tight_layout(True)
        self.canvas.draw()
        self.updating = False

    def single_plot(self):
        plot_data = self.data[self.data_fields]
        plot_data = self.clip_data(plot_data)
        plot_data = plot_data.apply(self.conv_func)
        ax = self.axes[0]
        ax.clear()
        try:
            plot_data.plot(ax=ax, style='.')
        except TypeError:
            print('No Data to plot')
        self.axis_scalings()
        ax.set_ylabel(f'{self.ylabel} {self.units_label}')
        ax.set_xlabel('Time')
        ax.legend(loc='lower left')

    def multi_plot(self):
        for n, field in enumerate(self.data_fields):
            plot_data = self.data[field]
            plot_data = self.clip_data(plot_data)
            plot_data = plot_data.apply(self.conv_func)
            ax = self.axes[n]
            ax.clear()
            try:
                plot_data.plot(ax=ax, style='.')
            except TypeError:
                print('No Data to plot')
            self.axis_scalings()
            ax.set_ylabel(f'{field} {self.units_label}')
            ax.set_xlabel('Time')

    def clip_data(self, data):
        time_mask = np.logical_and(self.start_datetime < data.index,
                                   data.index < self.stop_datetime)
        clipped_data = data[time_mask]
        if self.outlier_reject:
            clipped_data_std = np.std(clipped_data)
            clipped_data_mean = np.mean(clipped_data)
            clipped_zscore = (clipped_data - clipped_data_mean) / clipped_data_std
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
            ax.set_xlim(self.start_datetime, self.stop_datetime)

    def update(self):
        """
        The PlotWindow thread initiates the update process by first checking
        if the update process is already occurring. If so it aborts, otherwise it continues.
        The mechanism avoids generating a backlog of update requests in the working thread
        if there are delays in that thread.
        """
        if not self.updating:
            self.update_signal.emit()
        elif self.updating:
            curr_time = datetime.datetime.now()
            time_str = curr_time.strftime('%H:%M:%S')
            print(f'{time_str} - {self.loader.file_prefix} plotter - Plot is currently updating. '
                  f'Cannot update until previous update is complete.')
            return

    def update_settings(self):
        self.pause()
        self.update_yaxis_settings()
        self.update_refresh_settings()
        if self.xscale_tabWidget.currentIndex() == 0:
            self.set_xrange_history_mode()
        elif self.xscale_tabWidget.currentIndex() == 1:
            self.set_xrange_range_mode()
        if self.single_plot_radioButton.isChecked():
            self.plot_mode = 'singleplot'
        elif self.multi_plot_radioButton.isChecked():
            self.plot_mode = 'multiplot'
        self.reconfigure_plot_signal.emit()
        self.update()
        self.resume()

    def update_yaxis_settings(self):
        self.outlier_reject = self.outlier_checkBox.isChecked()
        try:
            self.outlier_reject_level = round(abs(float(self.outlier_reject_level_lineEdit.text())), 2)
        except ValueError:
            print('invalid input for outlier reject level, input must be real number')
        self.outlier_reject_level_lineEdit.setText(f'{self.outlier_reject_level:.2f}')

        self.autoscale = self.autoscale_checkBox.isChecked()
        try:
            self.ymin = float(self.ymin_lineEdit.text())
            self.ymax = float(self.ymax_lineEdit.text())
        except ValueError:
            print('invalid input for y limits, input must be real number')
        self.ymin_lineEdit.setText(f'{self.ymin:.2f}')
        self.ymax_lineEdit.setText(f'{self.ymax:.2f}')
        if self.lin_radioButton.isChecked():
            self.yscale = 'linear'
        elif self.log_radioButton.isChecked():
            self.yscale = 'log'

    def update_refresh_settings(self):
        try:
            self.refresh_time = int(float(self.refresh_lineEdit.text())*1e3)
            if not self.paused:
                self.refresh_timer.stop()
                self.refresh_timer.start(self.refresh_time)
        except ValueError:
            print('invalid input for refresh time, input must be real number')
        self.refresh_lineEdit.setText(f'{self.refresh_time*1e-3:.1f}')

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
        self.days_lineEdit.setText(f'{self.history_days}')
        self.hours_lineEdit.setText(f'{self.history_hours}')
        self.minutes_lineEdit.setText(f'{self.history_minutes}')
        self.history_delta = datetime.timedelta(days=self.history_days,
                                                hours=self.history_hours,
                                                minutes=self.history_minutes)
        self.start_datetime = self.stop_datetime - self.history_delta

    def set_xrange_range_mode(self):
        self.turn_off_tracking()
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
        if self.tracking:
            self.refresh_timer.stop()
            self.save_timer.stop()
            self.pause_pushButton.setText('Resume')
            self.paused = True

    def resume(self):
        if self.tracking:
            self.refresh_timer.start(self.refresh_time)
            self.save_timer.start()
            self.pause_pushButton.setText('Pause')
            self.paused = False

    def save_plot(self):
        save_file = Path(self.save_path, f'{self.loader.file_prefix}.png')
        try:
            self.figure.savefig(save_file)
        except OSError:
            print(f'Warning, OSError while attempting to save figure to {save_file}')


class IonPumpPlotWindow(PlotWindow):
    def __init__(self, *args, **kwargs):
        super(IonPumpPlotWindow, self).__init__(*args, **kwargs)

    def configure_singleplot_axes(self):
        ax = self.figure.add_subplot(1, 1, 1)
        ax2 = ax.twinx()
        axes = [ax, ax2]
        return axes

    def single_plot(self):
        plot_data = self.data[self.data_fields]
        plot_data = self.clip_data(plot_data)
        plot_data = plot_data.apply(self.conv_func)
        ax = self.axes[0]
        ax.clear()
        try:
            plot_data.plot(ax=ax, style='.')
        except TypeError:
            print('No Data to plot')
        self.axis_scalings()
        ax.set_ylabel(f'{self.ylabel} {self.units_label}')
        ax.set_xlabel('Time')
        ax.legend(loc='lower left')

        ax2 = self.axes[1]
        ymin, ymax = ax.get_ylim()
        ax2.set_ylim(self.curr2press(ymin), self.curr2press(ymax))
        ax2.set_ylabel('Pressure (torr)')

    @staticmethod
    def curr2press(curr):
        # formula given in ion pump controller to convert current (expressed in nA) to pressure (in torr)
        return 0.066 * curr * 10 ** -9 * 5600 / 7000 / 70