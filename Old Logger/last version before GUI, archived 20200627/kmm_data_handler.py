import serial
import time
import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as animation


class Controller:
    """
    Configure data acquisition, process/organize data as it comes in, and control visualization of data
    """
    def __init__(self, save_groups, device, date_format='%Y-%m-%d', time_format='%H:%M:%S', quiet=False):
        self.save_groups = save_groups
        self.channels = []
        for save_group in save_groups:
            for channel in save_group.channels:
                self.channels.append(channel)  # Add all of the channels in all of the save_groups into self.channels
        self.device = device
        self.quiet = quiet

    def get_data(self):
        curr_time = datetime.datetime.now()
        date_time_string = curr_time.strftime('%Y-%m-%d %H:%M:%S')
        data = self.device.read()
        try:
            if not self.quiet:
                print(date_time_string + " raw data: " + ", ".join([f"{datum:.3f}" for datum in data]))
        except ValueError:
            if data == ["b''"]:
                print(date_time_string + ": Error: Received nothing from Keithley")
            else:
                print(date_time_string + f": Error: Received {data} from Keithley")
        for chan in self.channels:
            chan.curr_data = chan.conv_func(data[chan.chan_idx])
        for save_group in self.save_groups:
            save_group.save_data(curr_time)

    def init_measurement(self):
        for idx, chan in enumerate(self.channels):
            chan.chan_idx = idx
            self.device.write(chan.init_cmds)
        chan_list_str = '(@' + ','.join([str(chan.hard_port) for chan in self.channels]) + ')'
        self.device.write("ROUT:SCAN " + chan_list_str)
        """
        it is the enumeration in chan_list_str which will determine the order in which the channels are read out
        through the "ROUT:SCAN (@...)" command. This is where chan_idx for each channel is configured to match up
        with the data coming out of the Keithley.
        """

        self.device.write(f"SAMP:COUN {len(self.channels)}")
        self.device.write("ROUT:SCAN:LSEL INT")

    @staticmethod
    def volt_cmds(chan_num):
        return [f"SENS:FUNC 'VOLT',(@{chan_num})",
                f"SENS:VOLT:NPLC 5,(@{chan_num})",
                f"SENS:VOLT:RANG 5,(@{chan_num})"]

    @staticmethod
    def rtd_cmds(chan_num):
        return [f"SENS:FUNC 'TEMP',(@{chan_num})",
                f"SENS:TEMP:TRAN FRTD,(@{chan_num})",
                f"SENS:TEMP:FRTD:TYPE PT100,(@{chan_num})",
                f"SENS:TEMP:NPLC 5,(@{chan_num})"]

    @staticmethod
    def thcpl_cmds(chan_num):
        return [f"SENS:FUNC 'TEMP',(@{chan_num})",
                f"SENS:TEMP:TRAN TC,(@{chan_num})",
                f"SENS:TEMP:TC:TYPE K,(@{chan_num})",
                # f"SENS:TEMP:TC:RJUN:RSEL INT,(@{chan_num})",
                f"SENS:TEMP:TC:RJUN:RSEL SIM,(@{chan_num})",
                f"SENS:TEMP:TC:RJUN:SIM 23,(@{chan_num})",
                f"SENS:TEMP:NPLC 5,(@{chan_num})"]


class Keithley:

    def __init__(self, port='COM0', baud=9600, timeout=15, quiet=True):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.quiet = quiet
        self.preamble = ["*RST",
                         "SYST:PRES",
                         "SYST:BEEP OFF",
                         "TRAC:CLE",
                         "TRAC:CLE:AUTO OFF",
                         "INIT:CONT OFF",
                         "TRIG:COUN 1",
                         "FORM:ELEM READ"]

    def __enter__(self):
        self.serial = serial.Serial(self.port, self.baud, timeout=self.timeout)
        print(f'Connected to device at {self.port}')
        for command in self.preamble:
            self.write(command)
            time.sleep(0.5)
        self.serial.flushInput()
        return self

    def __exit__(self, *exc_info):
        try:
            close_it = self.serial.close
            print('Closing serial connection with Keithley')
        except AttributeError:
            pass
        else:
            close_it()
            print(f'Closed connect at {self.port}')

    def write(self, command):
        # Write a single string or a list of strings to the device
        if isinstance(command, str):
            if not self.quiet:
                print(f'writing: {command}')
            self.serial.write(f'{command}\r'.encode())
        elif isinstance(command, list):
            for cmd in command:
                self.write(cmd)
        else:
            raise Exception

    def read(self):
        self.write("READ?")
        # self.write("*IDN?")
        data = self.serial.read_until(b"\r").decode().split(',')
        if not self.quiet:
            print(data)
        data = list(map(float, data))
        return data


class Channel:
    """
    Single data channel
    """
    def __init__(self, hard_port=101, chan_idx=0, chan_name="Voltage",
                 conv_func=lambda x: x, init_cmds_template=Controller.volt_cmds):
        self.hard_port = hard_port
        self.chan_idx = chan_idx  # chan_idx will be configured by the controller upon initialization
        self.chan_name = chan_name
        self.conv_func = conv_func
        self.init_cmds = init_cmds_template(hard_port)
        self.curr_data = 0


class SaveGroup:
    """
    Collection of channels whose data will be saved in a common file.
    """
    def __init__(self, channels, group_name='DataGroup',
                 log_drive=None, backup_drive=None, error_drive=None, webplot_drive=None,
                 date_format='%Y-%m-%d', time_format='%H:%M:%S', quiet=True):
        self.channels = channels
        self.group_name = group_name
        self.log_drive = log_drive
        self.backup_drive = backup_drive
        self.error_drive = error_drive
        self.webplot_drive = webplot_drive
        self.date_format = date_format
        self.time_format = time_format
        self.quiet = quiet
        self.loader = Loader(self)
        self.plotter = Plotter(self)

    def save_data(self, time_stamp):
        # should import CSV DictReader, DictWriter functionality so that data columns are
        # labeled with the appropriate channel names. This will improve the ability to add
        # and remove channels quickly as needed.
        data = [chan.curr_data for chan in self.channels]
        date_str = time_stamp.strftime(self.date_format)
        time_str = time_stamp.strftime(self.time_format)
        data_str = f'{date_str}, {time_str},' + ','.join([f'{datum:f}' for datum in data])
        # Legacy format for saving the data. Would make sense to save datetime string in one cell.

        # Attempt to write data to log_drive. Write to error_drive in event of failure.
        file_name = f'{self.log_drive}{self.group_name} {date_str}.csv'
        try:
            with open(file_name, 'a') as file:
                file.write(f'{data_str}\n')
                if not self.quiet:
                    print(f'wrote {data_str} to {file_name}')
        except OSError:
            err_str = f'IO error while attempting to write data to {file_name}'
            print(err_str)
            error_file = f'{self.error_drive}Error - {self.group_name} {date_str}.csv'
            try:
                with open(error_file, 'a') as file:
                    file.write(f'{data_str}\n')
                    file.write(f'{err_str}\n')
            except OSError:
                print(f'Error while logging earlier error data.')

        # Write data to backup drive
        backup_file_name = f'{self.backup_drive}{self.group_name} {date_str}.csv'
        try:
            with open(backup_file_name, 'a') as file:
                file.write(f'{data_str}\n')
                if not self.quiet:
                    print(f'wrote {data_str} to {backup_file_name}')
        except OSError:
            print('Warning, IO error while attempting to write to backup drive: {self.backup_drive}')
            # print("Ok, even backup log directory is having trouble. Shit has gone to hell! Abandon ship!")


class Loader:

    def __init__(self, save_group, quiet=True):
        self.save_group = save_group
        self.quiet = quiet

        self.group_name = self.save_group.group_name
        self.log_drive = self.save_group.log_drive
        self.date_format = self.save_group.date_format
        self.datetime_format = f'{self.save_group.date_format} {self.save_group.time_format}'

        self.chan_columns = [chan.chan_name for chan in self.save_group.channels]
        self.read_columns = ['date', 'time'] + self.chan_columns
        self.data = pd.DataFrame(columns=self.chan_columns)
        self.data.index.name = 'timestamp'

        self.data_loaded = False
        self.loaded_start_date = None
        self.loaded_stop_date = None
        self.lines_loaded = 0

    def load_data(self, start_date):
        # Loads all of the data since start_date into self.data. Note that self.data is overwritten when this method
        # is called.
        curr_date = datetime.datetime.now().date()
        self.data, self.lines_loaded = self.grab_data(start_date, curr_date, report_lines_loaded=True)
        self.data_loaded = True
        self.loaded_start_date = start_date
        self.loaded_stop_date = curr_date

    def grab_data(self, start_date, stop_date, report_lines_loaded=False):
        # grab_data parses through the data log and returns data, a pandas data frame containing all of the data
        # for the days within start_date to stop_date. If the report_lines_loaded option is flagged True then
        # it also returns an integer which specifies how many lines were loaded from the file on the last date.
        # This number is used elsewhere in the loader object such as in the refresh_data method.
        if not self.quiet:
            print(f'Grabbing data for dates '
                  f'{start_date.strftime(self.date_format)} through {stop_date.strftime(self.date_format)}')
        t0 = time.time()
        lines_loaded = 0
        data = pd.DataFrame(columns=self.chan_columns)
        data.index.name = 'timestamp'
        date_range = list(map(lambda x: x.date(), pd.date_range(start_date, stop_date)))
        for date in date_range:
            date_str = date.strftime(self.date_format)
            file_name = f'{self.log_drive}{self.group_name} {date_str}.csv'
            try:
                new_data = pd.read_csv(file_name,
                                       header=None,
                                       names=self.read_columns,
                                       parse_dates={'timestamp': ['date', 'time']},
                                       index_col='timestamp',
                                       infer_datetime_format=True)
                new_data.index = pd.to_datetime(new_data.index, format=self.datetime_format)
                data = data.append(new_data)
                if date == stop_date and report_lines_loaded:
                    # memoization of number of lines loaded on today's file
                    lines_loaded = len(new_data.index)
            except FileNotFoundError:
                print(f'File not found: {file_name}')
        if not self.quiet:
            tf = time.time()
            print(f'Grabbed data for dates '
                  f'{start_date.strftime(self.date_format)} through '
                  f'{stop_date.strftime(self.date_format)}')
            print(f'Grabbing took {(tf-t0):.3f} s')
        if report_lines_loaded:
            return data, lines_loaded
        else:
            return data

    def refresh_data(self, start_date):
        # Refreshes the data set to reflect all data for the days since the current day minus timedelta until now.
        stop_date = datetime.datetime.now().date()
        if not self.quiet:
            print(f'Refreshing data for dates '
                  f'{start_date.strftime(self.date_format)} through {stop_date.strftime(self.date_format)}')
        t0 = time.time()

        if not self.data_loaded or start_date < self.loaded_start_date:
            # hard reset on data required if data not loaded or start date is earlier than self.loaded_start_date
            self.load_data(start_date=start_date)

        date_range = list(map(lambda x: x.date(), pd.date_range(self.loaded_start_date, stop_date)))
        for date in date_range:
            if date < self.loaded_stop_date:
                continue  # dates with date < self.stop_date should already be included in self.data.
            elif date > self.loaded_stop_date:
                self.lines_loaded = 0
                # if date > self.loaded_stop_date it means we have moved onto a new file
                # and must start reading at the beginning.
            elif date == self.loaded_stop_date:
                # if date == self.loaded_stop_date then self.lines_loaded will be used to only load recent data.
                pass
            date_str = date.strftime(self.date_format)
            file_name = f'{self.log_drive}{self.group_name} {date_str}.csv'
            try:
                # Load in new data. Note that lines up until line number self.lines_loaded are skipped
                new_data = pd.read_csv(file_name,
                                       header=None,
                                       names=self.read_columns,
                                       skiprows=self.lines_loaded,
                                       parse_dates={'timestamp': ['date', 'time']},
                                       index_col='timestamp',
                                       infer_datetime_format=True)
                new_data.index = pd.to_datetime(new_data.index, format=self.datetime_format)
                new_row_count = len(new_data.index)
                if new_row_count > 0:
                    self.data = self.data.append(new_data)
                if date == stop_date:
                    self.lines_loaded += new_row_count
            except FileNotFoundError:
                print(f'File not found: {file_name}')
        start_time = datetime.datetime.combine(start_date, datetime.datetime.min.time())
        # start_time is the datetime for the start of the day on start_date.
        time_mask = self.data.index > start_time
        self.data = self.data.loc[time_mask]  # This line removes data from before start_date.
        self.loaded_start_date = start_date
        self.loaded_stop_date = stop_date
        if not self.quiet:
            tf = time.time()
            print(f'Data refreshed to include dates '
                  f'{start_date.strftime(self.date_format)} through '
                  f'{stop_date.strftime(self.date_format)}')
            print(f'Grabbing took {(tf - t0):.3f} s')


class Plotter:
    # Needs a lot of work. Things like passing parameters through, periodicity of plotting, etc.
    def __init__(self, save_group, plot_func=None, show=False, save=True, web_save=True, quiet=True,
                 t_plot_history=datetime.timedelta(hours=6), t_plot_freq=datetime.timedelta(seconds=10)):
        self.save_group = save_group
        self.loader = self.save_group.loader
        self.show = show
        self.save = save
        self.web_save = web_save
        self.quiet = quiet
        self.t_plot_history = t_plot_history
        self.t_plot_freq = t_plot_freq

        self.fig = plt.figure(self.save_group.group_name)
        self.ax = None
        self.xlabel = 'Time'
        self.ylabel = 'Voltage'
        if plot_func is not None:
            self.plot_func = plot_func
        else:
            self.plot_func = self.plot_func_default
        self.initialized = False
        self.animation = animation.FuncAnimation(self.fig, self.plot,
                                                 interval=self.t_plot_freq.seconds*1e3, fargs=(False,))
        # self.plot()

    # noinspection PyUnusedLocal
    def plot(self, i, grab_data=True):
        stop_datetime = datetime.datetime.now()
        start_datetime = stop_datetime - self.t_plot_history
        data = self.retrieve_data(start_datetime, stop_datetime, grab_data)
        self.plot_func(self, data)  # Note that self must be explicitly passed here. See note below plot_func_default.
        try:
            if self.save:
                self.fig.savefig(self.save_group.log_drive + self.save_group.group_name, bbox_inches="tight")
            if self.web_save:
                self.fig.savefig(self.save_group.webplot_drive + self.save_group.group_name, bbox_inches="tight")
        except (PermissionError, FileNotFoundError, OSError):
            datetime_string = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(datetime_string + ' message: Error saving figure')

    @staticmethod
    def plot_func_default(plotter, data):
        # This is the default behavior for self.plot_func. However, to leave it so that the user can implement
        # their own plotting function this function has been left as static.
        if not plotter.initialized:
            plotter.ax = plotter.fig.add_subplot(1, 1, 1)
            if plotter.show:
                plotter.fig.show()
            plotter.initialized = True
        plotter.ax.cla()
        # data.plot(ax=plotter.ax, marker='.', linestyle='None')
        plotter.ax.set_xlabel(plotter.xlabel)
        plotter.ax.set_ylabel(plotter.ylabel)
        plotter.ax.grid(which='both')
        # plotter.ax.set_ylim(15,220)

    def retrieve_data(self, start_datetime, stop_datetime, grab_data=True):
        start_date = start_datetime.date()
        stop_date = stop_datetime.date()
        if grab_data:
            if not self.quiet:
                print('grabbing Data for plotting')
            data = self.loader.grab_data(start_date, stop_date)
        else:
            if not self.loader.data_loaded:
                if not self.quiet:
                    print('Loading Data for plotting')
                self.loader.load_data(start_date)
            elif start_date < self.loader.loaded_start_date:
                if not self.quiet:
                    print('Loading data for plotting')
                self.loader.load_data(start_date)
            else:
                if not self.quiet:
                    print('Refreshing data for plotting')
                self.loader.refresh_data(start_date)
            data = self.loader.data
        time_mask = np.logical_and(np.array(start_datetime < data.index), np.array(data.index < stop_datetime))
        data = data.loc[time_mask]
        return data
