import serial
import time
import datetime


volt_cmds = ["SENS:FUNC 'VOLT',(@{chan_list})\n",
             "SENS:VOLT:NPLC 5,(@{chan_list})\n",
             "SENS:VOLT:RANG 5,(@{chan_list})\n"]

log_drive = 'Y:/E6/DataRaid E6/Data/KeithleyLogger/'
log_backup = 'C:/KeithleyLoggerBackup/'
error_drive = 'C:/KeithleyLoggerBackup/Error/'

# To work on: Figure out structure to "group channels", implement save_data. The idea is that
# the channel object should represent one hardware channel, but if multiple channels have a similar function
# (x,y,z) on magnetometer, or multiple temperature probes, it might be nice if all of that data is saved in the same
# file.
#
#
# class Controller:
#     """
#     Configure data acquisition, process/organize data as it comes in, and control visualization of data
#     """
#     def __init__(self, channels=None, read_freq=60, data_root=log_drive, backup_root=log_backup,
#                  date_format='%Y-%m-%d', time_format='%H:%M:%S', keithley_port='COM4', timeout=15, quiet=True):
#         self.channels = channels
#         self.read_freq = read_freq
#         self.data_root = data_root
#         self.backup_root = backup_root
#         self.date_format = date_format
#         self.time_format = time_format
#         self.keithley_port = keithley_port
#         self.timeout = timeout # serial timeout in seconds
#         self.quiet = quiet
#         self.serial = serial.Serial(self.keithley_port, timeout=self.timeout)
#         self.last_read_time = datetime.datetime.now()
#
#     def write(self, command):
#         if isinstance(command, str):
#             if not self.quiet:
#                 print('writing: ' + command.strip("\n"))
#             self.serial.write(command.encode())
#         elif isinstance(command, list):
#             for cmd in command:
#                 self.write(cmd)
#         else:
#             raise Exception
#
#     def get_data(self):
#         curr_time = datetime.datetime.now()
#         date_time_string = curr_time.strftime(self.date_format + ' ' + self.time_format)
#         t_delta = curr_time - self.last_read_time
#         if t_delta.seconds < self.read_freq:
#             # Don't read the Keithley if it was read too recently.
#             print('Sleeping at ' + date_time_string)
#             return
#
#         self.write("READ?\n")
#         data = self.serial.read_until(b"\r").decode().split(',')
#         data = list(map(float, data))
#         try:
#             print(date_time_string + " raw data: " + ", ".join([f"{datum:.3f}" for datum in data]))
#         except ValueError:
#             if data == ["b''"]:
#                 print(date_time_string + ": Error: Received nothing from Keithley")
#             else:
#                 print(date_time_string + ": Error: Received %s from Keithley" % (str(data)))
#         for chan in self.channels:
#             chan.curr_data = chan.conv_func(data[chan.chan_idx])
#
#     def init_channels(self):
#         for idx, chan in enumerate(self.channels):
#             chan.chan_idx = idx
#             self.write(chan.init_cmds)
#         chan_list_str = '(@'+','.join([str(chan.hard_port) for chan in self.channels]) + ')'
#         self.write("ROUT:SCAN " + chan_list_str + "\n")
#         self.write(f"SAMP:COUN {len(self.channels)}\n")
#         self.write("ROUT:SCAN:LSEL INT\n")
#
#     @staticmethod
#     def volt_cmds(chan_num):
#         return ["SENS:FUNC 'VOLT',(@" + str(chan_num) + ")\n",
#                 "SENS:VOLT:NPLC 5,(@" + str(chan_num) + ")\n",
#                 "SENS:VOLT:RANG 5,(@" + str(chan_num) + ")\n"]
#
#
# class Channel:
#     """
#     Single data channel
#     """
#     def __init__(self, hard_port=101, chan_idx=0, chan_name="Voltage",
#                  conv_func=lambda x: x, init_cmds_template=Controller.volt_cmds):
#         self.hard_port = hard_port
#         self.chan_idx = chan_idx
#         self.chan_name = chan_name
#         self.conv_func = conv_func
#         self.init_cmds = init_cmds_template(hard_port)
#         self.curr_data = 0
#
# class SaveGroup:
#     """
#     Collection of channels whose data will be saved in a common file.
#     """
#     def __init__(self, channels=None, log_drive=None, backup_drive=None, error_drive=None,
#                  group_name='DataGroup', date_format='%Y-%m-%d', time_format='%H:%M%S', quiet=True):
#         self.channels = channels
#         self.log_drive = log_drive
#         self.backup_drive = backup_drive
#         self.error_drive = error_drive
#         self.group_name = group_name
#         self.date_format = date_format
#         self.time_format = time_format
#         self.quiet=quiet
#
#     def save_data(self, time_stamp):
#         data = [chan.curr_data for chan in self.channels]
#         date_str = time_stamp.strftime(self.date_format)
#         time_str = time_stamp.strftime(self.time_format)
#         data_str = f'{date_str}, {time_str},' + ','.join([f'{datum:f}' for datum in data])
#
#         # Attempt to write data to log_drive. Write to error_drive in event of failure.
#         file_name = f'{self.log_drive}{self.group_name} {date_str}.csv'
#         try:
#             with open(file_name, 'a') as file:
#                 file.write(data_str + '\n')
#                 if not self.quiet:
#                     print('wrote ' + data_str + ' to ' + file_name)
#         except IOError:
#             err_str = f'IO error while attempting to write date to {file_name}'
#             print(err_str)
#             error_file = f'{self.error_drive}Error - {self.group_name} {date_str}'
#             with open(error_file, 'a') as file:
#                 file.write(data_str + '\n')
#                 file.write(err_str)
#
#         # Write data to backup drive
#         backup_file_name = f'{self.backup_drive}{self.group_name} {date_str}.csv'
#         try:
#             with open(backup_file_name, 'a') as file:
#                 file.write(data_str + '\n')
#                 if not self.quiet:
#                     print('wrote ' + data_str + ' to ' + backup_file_name)
#         except IOError:
#             print('Warning, IO error while attempting to write to backup drive: {self.backup_drive}')
#             #print("Ok, even backup log directory is having trouble. Shit has gone to hell! Abandon ship!")


class Channel:
    """
    Collection of channels to be monitored on Keithley multimeter and corresponding settings
    """
    def __init__(self, chan_nums=[101], init_cmds=volt_cmds, chan_name="default channel",
                 conv_func=lambda x: x,
                 log_drive=log_drive,
                 log_backup=log_backup,
                 error_drive=error_drive,
                 log_freq=60,
                 date_time_string_format="%Y-%m-%d %H:%M:%S",
                 quiet=True):
        self.chan_nums = chan_nums
        chan_list_string = ",".join([str(i) for i in chan_nums])
        self.init_cmds = [cmd.format(chan_list=chan_list_string) for cmd in init_cmds]
        self.data_idx = range(len(chan_nums))
        # self.data_idx contains indices at which data corresponding to this channel
        # will be read off from the multimeter. Modified in Keithley.init_channels
        self.log_drive = log_drive
        self.log_backup = log_backup
        self.error_drive = error_drive
        self.log_freq = log_freq
        self.chan_name = chan_name
        self.conv_func = conv_func
        self.last_time = datetime.datetime.fromtimestamp(0)
        self.date_time_string_format = date_time_string_format
        self.quiet = quiet

    # This is the logging part. Data is stored under a file "TEMP1 2012-01-19.csv", 
    # or whatever today's date is, and has lines of the format:
    # 2012-01-19 17:21:16, 24.458197         
    def process_data(self, chan_data, curr_time):
        dt = curr_time - self.last_time
        if dt.seconds < self.log_freq:
            # Skip logging if most recent data was collected too recently
            return
        self.last_time = curr_time
        time_str = curr_time.strftime(self.date_time_string_format)
        file_time_str = curr_time.strftime("%Y-%m-%d")

        converted_data = list(map(self.conv_func, chan_data))
        data_str = time_str + ',' + ','.join([f'{datum:f}' for datum in converted_data])
        file_name = f'{self.log_drive}{self.chan_name} {file_time_str}.csv'
        try:
            with open(file_name, 'a') as file:
                file.write(data_str + '\n')
                if not self.quiet:
                    print('wrote ' + data_str + ' to ' + file_name)
        except IOError:
            print("Some sort of IO error. Check the server connection?")
            error_file = f'{self.error_drive}Error - {self.chan_name} {file_time_str}'
            with open(error_file, 'a') as file:
                file.write(data_str + '\n')
                file.write("Some sort of IO error. Check the server connection?")

        backup_file_name = f'{self.log_backup}{self.chan_name} {file_time_str}.csv'
        try:
            with open(backup_file_name, 'a') as file:
                file.write(data_str + '\n')
                if not self.quiet:
                    print('wrote ' + data_str + ' to ' + backup_file_name)
        except IOError:
            print("Ok, even backup log directory is having trouble. Shit has gone to hell! Abandon ship!")


class Keithley:

    def __init__(self, channels=None, port=3, timeout=2, debug=True):
        self.preamble = ["*RST\n",
                         "SYST:PRES\n",
                         "SYST:BEEP OFF\n",
                         "TRAC:CLE\n",
                         "TRAC:CLE:AUTO OFF\n",
                         "INIT:CONT OFF\n",
                         "TRIG:COUN 1\n",
                         "FORM:ELEM READ\n"]
        self.channels = channels
        self.port = port
        self.timeout = timeout
        self.debug = debug
        self.date_time_string_format = "%Y-%m-%d %H:%M:%S"

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
            if self.debug:
                print(command.strip())
            self.serial.write(command.encode())
            print('writing: ' + command.strip("\n"))
        elif isinstance(command, list):
            for cmd in command:
                self.write(cmd)
        else:
            raise Exception
    
    def init_channels(self):
        clist = []
        idx = 0
        for channel in self.channels:
            self.write(channel.init_cmds)
            clist.extend([str(c) for c in channel.chan_nums])
            channel.data_idx = range(idx, idx + len(channel.chan_nums))
            idx += len(channel.chan_nums)
        scan_list = '(@' + ','.join(clist) + ')'
        self.write("ROUT:SCAN {}\n".format(scan_list))
        self.write("SAMP:COUN {}\n".format(len(clist)))
        self.write("ROUT:SCAN:LSEL INT\n")

    def get_data(self):
        self.write("READ?\n")
        #self.write('*IDN?\n')
        data = self.serial.read_until(b"\r").decode().split(',')
        data = list(map(float, data))

        curr_time = datetime.datetime.now()
        date_time_string = curr_time.strftime(self.date_time_string_format)
        try:
            print(date_time_string + " raw data: " + ", ".join([f"{datum:.3f}" for datum in data]))
            for channel in self.channels:
                chan_data = [data[i] for i in channel.data_idx]
                channel.process_data(chan_data, curr_time)
        except ValueError:
            if data == ["b''"]:
                print(date_time_string + ": Error: Received nothing from Keithley")
            else:
                print(date_time_string + ": Error: Received %s from Keithley" % (str(data)))
