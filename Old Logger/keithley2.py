import serial
import time
import datetime
import pandas as pd
import matplotlib.pyplot as plt


class Controller:
    """
    Configure data acquisition, process/organize data as it comes in, and control visualization of data
    """
    def __init__(self, save_groups, device, read_freq=60, timeout=15,
                 date_format='%Y-%m-%d', time_format='%H:%M:%S'):
        self.save_groups = save_groups
        self.channels = []
        for save_group in save_groups:
            for channel in save_group.channels:
                self.channels.append(channel)  # Add all of the channels in all of the save_groups into self.channels
        self.read_freq = read_freq
        self.device = device
        self.timeout = timeout  # serial timeout in seconds
        self.date_format = date_format
        self.time_format = time_format
        self.last_read_time = datetime.datetime.now()
        self.new_data_flag = False

    def get_data(self):
        curr_time = datetime.datetime.now()
        date_time_string = curr_time.strftime(self.date_format + ' ' + self.time_format)
        t_delta = curr_time - self.last_read_time
        if t_delta.seconds < self.read_freq:
            # Don't read the Keithley if it was read too recently.
            print('Sleeping at ' + date_time_string)
            return

        data = self.device.read()
        self.last_read_time = curr_time
        try:
            print(date_time_string + " raw data: " + ", ".join([f"{datum:.3f}" for datum in data]))
        except ValueError:
            if data == ["b''"]:
                print(date_time_string + ": Error: Received nothing from Keithley")
            else:
                print(date_time_string + ": Error: Received %s from Keithley" % (str(data)))
        for chan in self.channels:
            chan.curr_data = chan.conv_func(data[chan.chan_idx])
        self.new_data_flag = True
        self.save_data()

    def init_measurement(self):
        for idx, chan in enumerate(self.channels):
            chan.chan_idx = idx
            self.device.write(chan.init_cmds)
        chan_list_str = '(@' + ','.join([str(chan.hard_port) for chan in self.channels]) + ')'
        self.device.write("ROUT:SCAN " + chan_list_str + "\n")
        self.device.write(f"SAMP:COUN {len(self.channels)}\n")
        self.device.write("ROUT:SCAN:LSEL INT\n")

    def save_data(self):
        if self.new_data_flag is True:
            for save_group in self.save_groups:
                save_group.save_data(self.last_read_time)

    @staticmethod
    def volt_cmds(chan_num):
        return ["SENS:FUNC 'VOLT',(@" + str(chan_num) + ")\n",
                "SENS:VOLT:NPLC 5,(@" + str(chan_num) + ")\n",
                "SENS:VOLT:RANG 5,(@" + str(chan_num) + ")\n"]

    @staticmethod
    def rtd_cmds(chan_num):
        return ["SENS:FUNC 'TEMP',(@" + str(chan_num) + ")\n",
                "SENS:TEMP:TRAN FRTD,(@" + str(chan_num) + ")\n",
                "SENS:TEMP:FRTD:TYPE PT100,(@" + str(chan_num) + ")\n",
                "SENS:TEMP:NPLC 5,(@" + str(chan_num) + ")\n"]

    @staticmethod
    def thcpl_cmds(chan_num):
        return ["SENS:FUNC 'TEMP',(@" + str(chan_num) + ")\n",
                "SENS:TEMP:TRAN TC,(@" + str(chan_num) + ")\n",
                "SENS:TEMP:TC:TYPE K,(@" + str(chan_num) + ")\n",
                "SENS:TEMP:TC:RJUN:RSEL INT,(@" + str(chan_num) + ")\n",
                "SENS:TEMP:NPLC 5,(@" + str(chan_num) + ")\n"]


class Channel:
    """
    Single data channel
    """
    def __init__(self, hard_port=101, chan_idx=0, chan_name="Voltage",
                 conv_func=lambda x: x, init_cmds_template=Controller.volt_cmds):
        self.hard_port = hard_port
        self.chan_idx = chan_idx
        self.chan_name = chan_name
        self.conv_func = conv_func
        self.init_cmds = init_cmds_template(hard_port)
        self.curr_data = 0


class SaveGroup:
    """
    Collection of channels whose data will be saved in a common file.
    """
    def __init__(self, channels=None, group_name='DataGroup',
                 log_drive=None, backup_drive=None, error_drive=None,
                 date_format='%Y-%m-%d', time_format='%H:%M:%S', plot_func=None, quiet=True):
        self.channels = channels
        self.log_drive = log_drive
        self.backup_drive = backup_drive
        self.error_drive = error_drive
        self.group_name = group_name
        self.date_format = date_format
        self.time_format = time_format
        self.loader = Loader(self)
        self.plotter = Plotter(self, plot_func)
        self.quiet = quiet

    def save_data(self, time_stamp):
        data = [chan.curr_data for chan in self.channels]
        date_str = time_stamp.strftime(self.date_format)
        time_str = time_stamp.strftime(self.time_format)
        data_str = f'{date_str}, {time_str},' + ','.join([f'{datum:f}' for datum in data])

        # Attempt to write data to log_drive. Write to error_drive in event of failure.
        file_name = f'{self.log_drive}{self.group_name} {date_str}.csv'
        try:
            with open(file_name, 'a') as file:
                file.write(data_str + '\n')
                if not self.quiet:
                    print('wrote ' + data_str + ' to ' + file_name)
        except IOError:
            err_str = f'IO error while attempting to write date to {file_name}'
            print(err_str)
            error_file = f'{self.error_drive}Error - {self.group_name} {date_str}'
            with open(error_file, 'a') as file:
                file.write(data_str + '\n')
                file.write(err_str)

        # Write data to backup drive
        backup_file_name = f'{self.backup_drive}{self.group_name} {date_str}.csv'
        try:
            with open(backup_file_name, 'a') as file:
                file.write(data_str + '\n')
                if not self.quiet:
                    print('wrote ' + data_str + ' to ' + backup_file_name)
        except IOError:
            print('Warning, IO error while attempting to write to backup drive: {self.backup_drive}')
            # print("Ok, even backup log directory is having trouble. Shit has gone to hell! Abandon ship!")


class Loader:

    def __init__(self, save_group, quiet=False):
        self.save_group = save_group
        self.quiet = quiet
        self.group_name = self.save_group.group_name
        self.log_drive = self.save_group.log_drive
        self.date_format = self.save_group.date_format
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
        # grab_data parses through the data log and returns data, a pandas dataframe containing all of the data
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
                                       index_col='timestamp')
                data = data.append(new_data)
                if date == stop_date and report_lines_loaded:
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
        if not self.data_loaded:
            self.load_data(start_date=start_date)
        elif start_date < self.loaded_start_date:
            # hard reset on data required if start date is earlier than self.loaded_start_date
            self.load_data(start_date=start_date)

        date_range = list(map(lambda x: x.date(), pd.date_range(self.loaded_start_date, stop_date)))
        for date in date_range:
            if date < self.loaded_stop_date:
                continue  # dates with date < self.stop_date should already be included in self.data.
            if date > self.loaded_stop_date:
                self.lines_loaded = 0
                # if date > self.loaded_stop_date it means we have moved onto a new file
                # and must start reading at the beginning.
            date_str = date.strftime(self.date_format)
            file_name = f'{self.log_drive}{self.group_name} {date_str}.csv'
            try:
                # Load in new data. Note that lines up until line number self.lines_loaded are skipped
                new_data = pd.read_csv(file_name,
                                       header=None,
                                       names=self.read_columns,
                                       skiprows=self.lines_loaded,
                                       parse_dates={'timestamp': ['date', 'time']},
                                       index_col='timestamp')
                new_row_count = len(new_data.index)
                if new_row_count > 0:
                    self.data = self.data.append(new_data)
                if date == stop_date:
                    self.lines_loaded += new_row_count
            except FileNotFoundError:
                print(f'File not found: {file_name}')
        # self.data = self.data.loc[start_date:stop_date]  # This line removes data from before start_date.
        self.loaded_start_date = start_date
        self.loaded_stop_date = stop_date
        if not self.quiet:
            print(f'Data refreshed to include dates '
                  f'{start_date.strftime(self.date_format)} through '
                  f'{stop_date.strftime(self.date_format)}')


class Plotter:

    def __init__(self, save_group, plot_func=None):
        self.save_group = save_group
        if plot_func is not None:
            self.plot_func = plot_func
        else:
            self.plot_func = self.plot_func_default
        self.loader = self.save_group.loader

    def plot_data(self, start_datetime, stop_datetime, grab_data=True):
        start_date = start_datetime.date()
        stop_date = stop_datetime.date()
        if grab_data:
            print('GRABBING')
            data = self.loader.grab_data(start_date, stop_date)
        else:
            if not self.loader.data_loaded:
                print('LOADING')
                self.loader.load_data(start_date)
            elif start_date < self.loader.loaded_start_date:
                print('LOADING')
                self.loader.load_data(start_date)
            else:
                print('REFRESHING')
                self.loader.refresh_data(start_date)
            data = self.loader.data
        data = data.loc[start_datetime:stop_datetime]
        return data
        # data.plot()
        # self.plot_func(data)

    @staticmethod
    def plot_func_default(data, x_label='Time', y_label='signal'):
        # plt.clf()
        # plt.figure()
        print('about to plot')
        data.plot()


class Keithley:

    def __init__(self, port='COM0', timeout=2, quiet=True):
        self.port = port
        self.timeout = timeout
        self.quiet = quiet
        self.preamble = ["*RST\n",
                         "SYST:PRES\n",
                         "SYST:BEEP OFF\n",
                         "TRAC:CLE\n",
                         "TRAC:CLE:AUTO OFF\n",
                         "INIT:CONT OFF\n",
                         "TRIG:COUN 1\n",
                         "FORM:ELEM READ\n"]

    def __enter__(self):
        self.serial = serial.Serial(self.port, timeout=self.timeout)
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
        if isinstance(command, str):
            if not self.quiet:
                print('writing: ' + command.strip("\n"))
            self.serial.write(command.encode())
        elif isinstance(command, list):
            for cmd in command:
                self.write(cmd)
        else:
            raise Exception

    def read(self):
        self.write("READ?\n")
        data = self.serial.read_until(b"\r").decode().split(',')
        data = list(map(float, data))
        return data
