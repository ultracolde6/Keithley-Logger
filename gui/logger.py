import serial
import time
import datetime
from pathlib import Path
import csv
from gui.loader import Loader
from PyQt5 import QtCore


class Logger(QtCore.QObject):
    """
    Configure data acquisition, process/organize data as it comes in, and control visualization of data
    """
    def __init__(self, save_groups, device, log_freq, quiet=False):
        super(Logger, self).__init__()
        self.save_groups = save_groups
        self.channels = []
        for save_group in self.save_groups:
            for channel in save_group.channels:
                self.channels.append(channel)  # Add all of the channels in all of the save_groups into self.channels
        self.device = device
        self.log_freq = log_freq
        self.quiet = quiet

        self.data_timer = QtCore.QTimer(self)
        self.data_timer.timeout.connect(self.log_data)
        self.data_timer.start(self.log_freq)

    def log_data(self):
        curr_time, data = self.device.read_data()
        for chan in self.channels:
            chan.curr_data = chan.conv_func(data[chan.chan_idx])  # Consider saving raw data instead of converted data
        for save_group in self.save_groups:
            save_group.save_data(curr_time)


class Keithley:
    """
    Handles serial communication with and initialization of the Keithley2700 multimeter
    """
    preamble = ["*RST",
                "SYST:PRES",
                "SYST:BEEP OFF",
                "TRAC:CLE",
                "TRAC:CLE:AUTO OFF",
                "INIT:CONT OFF",
                "TRIG:COUN 1",
                "FORM:ELEM READ"]

    def __init__(self, port='COM0', log_freq=30, baud_rate=9600, timeout=15, quiet=True):
        self.port = port
        self.log_freq = log_freq
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.quiet = quiet
        self.serial = None
        self.initialize_device()

    def initialize_device(self):
        self.serial = serial.Serial(self.port, self.baud_rate, timeout=self.timeout)
        print(f'Connected to device at {self.port}')
        for command in self.preamble:
            self.write(command)
            time.sleep(0.5)
        self.serial.flushInput()
        return self

    # def __exit__(self, *exc_info):
    #     try:
    #         close_it = self.serial.close
    #         print('Closing serial connection with Keithley')
    #     except AttributeError as er:
    #         print('Exception during serial closing:')
    #         print(er)
    #         # TODO check what this might be catching?
    #         pass
    #     else:
    #         close_it()
    #         print(f'Closed connect at {self.port}')

    def write(self, command):
        # Write a single string or a list of strings to the device
        if isinstance(command, str):
            if not self.quiet:
                print(f'writing: {command}')
            self.serial.write(f'{command}\n'.encode())
        elif isinstance(command, list):
            for cmd in command:
                self.write(cmd)
        else:
            raise TypeError('invalid command or command list')

    def read(self):
        # Read data from Keithley and return list of floats representing recorded values
        self.write("READ?")
        data = self.serial.read_until(b"\r").decode().split(',')
        data = list(map(float, data))
        return data

    def init_measurement(self, channels):
        for idx, chan in enumerate(channels):
            chan.chan_idx = idx
            self.write(chan.init_cmds)
            print(f'Initialized logical channel {chan.chan_idx:d}: {chan.chan_name} '
                  f'at Keithley port ({chan.hard_port:d})')
        chan_list_str = '(@' + ','.join([str(chan.hard_port) for chan in channels]) + ')'
        self.write(f"ROUT:SCAN {chan_list_str}")
        # The order of the hardware channel listing in chan_list_str in the "ROUT:SCAN..." command determines
        # the order in which the Keithley will read out its data. This ordering derives from the order of channels
        # in channels. Here we memoize that order into a logical channel identification for each channel.
        # This identification is used to correctly assign data output from the Keithley to the appropriate channel.
        self.write(f"SAMP:COUN {len(channels)}")
        self.write("ROUT:SCAN:LSEL INT")

    def read_data(self):
        curr_time = datetime.datetime.now()
        date_time_string = curr_time.strftime('%Y-%m-%d %H:%M:%S')
        data = self.read()
        try:
            if not self.quiet:
                print(date_time_string + " raw data: " + ", ".join([f"{datum:.3f}" for datum in data]))
        except ValueError:
            if data == ["b''"]:
                print(date_time_string + ": Error: Received nothing from Keithley")
            else:
                print(date_time_string + f": Error: Received {data} from Keithley")
        return curr_time, data

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


class Channel:
    """
    Single data channel
    """
    def __init__(self, hard_port=101, chan_idx=0, chan_name="Voltage",
                 conv_func=lambda x: x, init_cmds_template=Keithley.volt_cmds):
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
                 date_format='%Y-%m-%d', time_format='%H:%M:%S', data_label='Signal Level', quiet=True):
        if not isinstance(channels, list):
            channels = [channels]
        self.channels = channels
        self.group_name = group_name
        self.log_drive = log_drive
        self.backup_drive = backup_drive
        self.error_drive = error_drive
        self.webplot_drive = webplot_drive
        self.date_format = date_format
        self.time_format = time_format
        self.loader = Loader(log_drive, group_name, date_format, time_format)
        self.data_label = data_label
        # self.plotwindow = PlotWindow(self.loader, ylabel=self.data_label)
        # TODO: savegroup shouldn't contain the plotter, this should be seperate
        self.quiet = quiet

    def save_data(self, time_stamp):
        data = dict()
        data['date'] = time_stamp.strftime(self.date_format)
        data['time'] = time_stamp.strftime(self.time_format)
        for chan in self.channels:
            data[chan.chan_name] = f'{chan.curr_data:f}'

        # Legacy format for saving the data. Would make sense to save datetime string in one cell.

        file_name = f'{self.group_name} {data["date"]}.csv'
        file_path = Path(self.log_drive, file_name)

        # Attempt to write data to log_drive. Write to error_drive in event of failure.
        try:
            write_to_csv(file_path, data, quiet=self.quiet)
        except OSError:
            print(f'Warning, OSError while attempting to write data to log file: {file_path}')
            error_file_name = f'Error - {self.group_name} {data["date"]}.csv'
            error_file_path = Path(self.error_drive, error_file_name)
            try:
                write_to_csv(error_file_path, data, quiet=self.quiet)
            except OSError:
                print(f'Warning, OSError while attempting to write data to error log: {error_file_path}')

        backup_file_name = f'{self.group_name} {data["date"]}.csv'
        backup_file_path = Path(self.backup_drive, backup_file_name)
        try:
            write_to_csv(backup_file_path, data, quiet=self.quiet)
        except OSError:
            print(f'Warning, OSError while attempting to write to backup log: {backup_file_path}')
            # print('Ok, even backup log directory is having trouble. Shit has gone to hell! Abandon ship!')


def write_to_csv(file_path, data_dict, quiet=True):
    keys = data_dict.keys()
    file_exists = Path.is_file(file_path)
    if file_exists:
        fieldnames = get_csv_header(file_path)
        if set(fieldnames) != set(keys):
            raise ValueError(f'keys {keys} in data input do not match header {fieldnames} for {file_path}')
    else:
        fieldnames = keys
    file_path.parent.mkdir(exist_ok=True)
    with file_path.open('a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(data_dict)
        if not quiet:
            print(f'wrote {data_dict} to {file_path}')


def get_csv_header(file_path):
    with open(file_path, 'r', newline='') as file:
        reader = csv.reader(file)
        header = next(reader)
    return header
