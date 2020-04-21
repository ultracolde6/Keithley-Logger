from datetime import datetime, date, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from numpy.lib import recfunctions
import pandas as pd
from os import system, path
import warnings
import sys
import math

class LogDisplay:
    def __init__(self, directory, name, final_date=False, start_date=False, load_days=7,
                 plot_days=1, resample=60, columns='voltage',
                 x_label='Time', y_label='', title='', track=True):
        self.directory = directory
        self.name = name
        self.resample_period = resample
        self.columns = columns
        self.file_columns = ('date', 'time') + self.columns
        self.plot_days = plot_days
        self.load_days = load_days

        self.update = True
        self.looping = True
        self.data = None

        self.x_label = x_label
        self.y_label = y_label
        self.title = title
        self.track = track

        if not final_date:
            self.final_date = date.today()
        else:
            self.final_date = final_date
        if not start_date:
            self.start_date = self.final_date - timedelta(self.load_days)
        else:
            self.start_date = start_date

        self.last_date = self.start_date
        self.last_row = 0

    def refresh_plot(self):
        ax = plt.gca()

        if self.track:
            x1, x2 = ax.get_xlim()
            period = pd.Period(ordinal=int(x1), freq=ax.freq)
            x1 = period.to_timestamp().to_datetime()
            period = pd.Period(ordinal=int(x2), freq=ax.freq)
            x2 = period.to_timestamp().to_datetime()
            dx = x2 - x1

            y1, y2 = ax.get_ylim()
            dy = y2 - y1
            # are we viewing latest data? if so, we will want to follow it in the plot
            dataright = self.data.index[-1] <= x2 and \
                all([y1 <= self.data[column][-1] <= y2 for column in self.columns])

        self.final_date = date.today()
        self.load_data()
        plot_data = self.resample()

        if self.track:
            if dataright and plot_data.index[-1] >= x2:
                # expand right with data
                x2 = plot_data.index[-1] + dx / 8

            for column in self.columns:
                if dataright and plot_data[column][-1] < y1:
                    # expand down with data
                    y1 = plot_data[column][-1] - dy / 8
                elif dataright and plot_data[column][-1] > y2:
                    # expand up with data
                    y2 = plot_data[column][-1] + dy / 8

            ax.set_ylim([y1, y2])
            ax.set_ylim([0, 50])
            ax.set_xlim([x1, x2])

        # Update plot lines
        for index, column in enumerate(self.columns):
            try:
                self.lines[index].set_data(plot_data.index, plot_data[column])
            except (AttributeError, TypeError):
                print ("Expected Line2D object, got:")
                print self.lines[index]
        plt.draw()

    def load_data(self):
        cur_date = self.last_date
        while cur_date <= self.final_date:
            filename = "%s %s.csv" % (self.name, cur_date.strftime("%Y-%m-%d"))
            cur_file = path.realpath(path.join(self.directory, filename))
            if not path.isfile(cur_file):
                cur_date += timedelta(1)
                continue
            # If this is not the same log file we previously looked at, start at the first row
            if cur_date is not self.last_date:
                self.last_row = 0

            try:
                new_data = pd.read_csv(cur_file,
                                       header=None,
                                       names=self.file_columns,
                                       skiprows=self.last_row,
                                       parse_dates={'timestamp': ['date', 'time']},
                                       index_col='timestamp',
                                       skipinitialspace=True,
                                       error_bad_lines=False)
                new_rows = len(new_data.index)

                if new_rows > 0:
                    new_data = self.filter_data(new_data)
                    if self.data is None:
                        self.data = new_data
                    else:
                        self.data = self.data.append(new_data)

                    # Save date and row count for most recently loaded log file
                    self.last_row += new_rows
                    self.last_date = cur_date
            except Exception:
                print('Error reading .csv')
            cur_date += timedelta(1)

    def filter_data(self, new_data):
        if not new_data.index.is_all_dates:  # Filter bad dates from index
            # new_data.index = pd.to_datetime(new_data.index, coerce=True)
            new_data.index = pd.to_datetime(new_data.index, errors='coerce')
            new_data = new_data[pd.notnull(new_data.index)].copy()

        return new_data

    def resample(self, resample_period=None):
        if resample_period is None:
            resample_period = self.resample_period
        if not resample_period:
            return self.data
        return self.data.resample('{}s'.format(resample_period))

    def save_plot(self, stop=False, start=False, days=1, file=False, logplot=False, ylimbottom=None, ylimtop=None):
        stop_date = datetime.now()
        start_date = stop_date - timedelta(days=1)
        self.final_date = max(stop_date.date(), self.final_date)
        self.load_data()
        data = self.resample()

        stop = data.index.searchsorted(stop_date)
        start = data.index.searchsorted(start_date)
        data = data.ix[start:stop]

        if len(data.index) == 0:
            return

        plt.clf()
        if logplot:
            pow(10, data).plot(logy=True)
            plt.grid(True, which='both', )
            mi = math.floor(min(data.iloc[:][list(data)[0]]))
            ma = math.ceil(max(data.iloc[:][list(data)[0]]))
            #ax.set_ylim([pow(10,mi), pow(10,ma)])
            plt.ylim([pow(10, mi), pow(10, ma)])
        else:
            data.plot()
            plt.grid(True, which='both', )
            ax = plt.gca()
            ax.set_ylim([ylimbottom, ylimtop])
        plt.legend(bbox_to_anchor=(1, 0.5), loc='center left')
        locator = mdates.AutoDateLocator(minticks=3, maxticks=6)
        plt.gcf().autofmt_xdate()
        plt.ylabel(self.y_label)
        plt.xlabel(self.x_label)

        # ax.set_ylim([50, 200])


        if not file:
            filename = "%s %s.png" % (self.name, stop_date.strftime("%Y-%m-%d %H"))
            file = path.realpath(path.join(self.directory, filename))
        plt.show()
        plt.savefig(file, bbox_inches="tight")

        plt.close()

    def plot(self):
        self.load_data()

        plot_data = self.resample()
        plot_data.plot(legend=False, color=['r', 'b'])

        stop = datetime.now()
        start = datetime.now() - timedelta(self.plot_days)
        ax = plt.gca()
        ax.set_xlim([start, stop])
        xl = ax.get_xlim()
        # print(datetime(xl[0]))

        plt.ylabel(self.y_label)
        plt.xlabel(self.x_label)

        self.lines = ax.get_lines()

        plt.connect('key_press_event', self.on_keypress)
        plt.connect('close_event', self.on_close)
        fig = plt.gcf()
        fig.canvas.set_window_title(self.title)

    def loop(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            plt.draw()
            plt.show()
            sys.stdout.flush()
            plt.pause(0.5)

        print('Auto update is: {}'.format(self.update))
        print('Press "a" to toggle auto updates.\nPress "m" to refresh manually')

        update_timeout = 0
        while self.looping:
            if self.update and update_timeout >= 5:
                self.refresh_plot()
                update_timeout = 0
            update_timeout += 1
            sys.stdout.flush()
            plt.pause(1)

    def on_keypress(self, event):
        if event.key == 'm':
            print('Manual refresh')
            self.refresh_plot()
        elif event.key == 'a':
            self.update = not self.update
            print('Auto update is: {}'.format(self.update))

    def on_close(self, event):
        self.looping = False
        plt.clf()
        plt.close()


class VoltDisplay(LogDisplay):
    def __init__(self, directory, name, final_date=False, start_date=False, load_days=7,
                 plot_days=1, resample=60, columns=('Voltage',), title=''):
        LogDisplay.__init__(self, directory, name, final_date, start_date, load_days,
                            plot_days, resample, columns, y_label='Voltage (V)', title=title)


class TempDisplay(LogDisplay):
    def __init__(self, directory, name, final_date=False, start_date=False, load_days=7,
                 plot_days=1, resample=60, columns=('Temperature',), title='', track=True):
        LogDisplay.__init__(self, directory, name, final_date, start_date, load_days,
                            plot_days, resample, columns, y_label='Temperature (deg C)', title=title, track=track)


class MagDisplay(LogDisplay):
    def __init__(self, directory, name, columns=('x', 'y', 'z'), background={'x': 0, 'y': 0, 'z': 0},
                 final_date=False, start_date=False, load_days=7, plot_days=1,
                 resample=300, title=''):
        LogDisplay.__init__(self, directory, name, final_date, start_date, load_days,
                            plot_days=plot_days, resample=resample, columns=columns,
                            y_label='Field (gauss)', title=title)

        self.columns += ('sum',)
        self.background = background

    def filter_data(self, new_data):
        new_data = LogDisplay.filter_data(self, new_data)

        new_data['x'] -= self.background['x']
        new_data['y'] -= self.background['y']
        new_data['z'] -= self.background['z']
        new_data['sum'] = np.sqrt(np.square(new_data['x'])
                                  + np.square(new_data['y']) + np.square(new_data['z']))
        return new_data
