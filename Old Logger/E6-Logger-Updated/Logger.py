import time
import math
import serial
import datetime
from kmm_data_handler import *

# Setup communication with Keithley 2700 multimeter, starting with the following
# preamble. This ensures the setup is the same every time, regardless if it has
# been adjusted


rtdCmds = ["SENS:FUNC 'TEMP',(@{chan})\n",
           "SENS:TEMP:TRAN FRTD,(@{chan}\n",
           "SENS:TEMP:FRTD:TYPE PT100,(@{chan})\n",
           "SENS:TEMP:NPLC 5,(@{chan})\n"]

thcplCmds = ["SENS:FUNC 'TEMP',(@{chan})\n",
             "SENS:TEMP:TRAN TC,(@{chan})\n",
             "SENS:TEMP:TC:TYPE K,(@{chan})\n",
             "SENS:TEMP:TC:RJUN:RSEL INT,(@{chan})\n",
             "SENS:TEMP:NPLC 5,(@{chan})\n"]

volt_cmds = ["SENS:FUNC 'VOLT',(@{chan_list})\n",
             "SENS:VOLT:NPLC 5,(@{chan_list})\n",
             "SENS:VOLT:RANG 5,(@{chan_list})\n"]

log_drive = 'Y:/E6/DataRaid E6/Data/KeithleyLogger/'
log_backup = 'C:/KeithleyLoggerBackup/'
error_drive = 'C:/KeithleyLoggerBackup/Error/'

# Define channels to scan, and then bind them to the multimeter
MagField = Channel(chan_nums=[101, 104, 103], init_cmds=volt_cmds, chan_name="MagField",
                   conv_func=lambda x: x * 100,
                   # Bartington Mag690-100 outputs 100 mV/uT = 0.01 V/mG so 100 mG/V, 100 uG/mV
                   log_drive=log_drive + 'MagField/',
                   log_backup=log_backup + 'MagField/',
                   error_drive=error_drive + 'MagField/',
                   log_freq=5,
                   date_time_string_format="%Y-%m-%d, %H:%M:%S")

# MultiTemp2 = Channel(chan_nums=[110, 111, 112, 113, 114, 115], init_cmds=volt_cmds, chan_name="MULTITEMP2",
#                      conv_func=lambda x: x * 1000,
#                      # x*1000 chosen because the Omega temperature to voltage converters output 1 mV/C -JAG 02/12/2018
#                      log_drive=log_drive + 'MultiTemp2/',
#                      log_backup=log_backup + 'MultiTemp2/',
#                      error_drive=error_drive + 'MultiTemp2/',
#                      log_freq=3,
#                      date_time_string_format="%Y-%m-%d, %H:%M:%S")
#
# IonGauge = Channel(chan_nums=[118], init_cmds=volt_cmds, chan_name="IONGAUGE",
#                    conv_func=lambda x: (x - 4.935) / 0.5004,
#                    # The ion gauge outputs a logarithmic voltage which is strangely documented in the
#                    # TERRANOVA ion gauge controller manual. I found the in the code
#                    # to give roughly log10(P) (P in torr) according to the formula
#                    # in the documentation. -JAG 02/12/2018
#                    log_drive=log_drive + 'IonGauge/',
#                    log_backup=log_backup + 'IonGauge/',
#                    error_drive=error_drive + 'IonGauge/',
#                    log_freq=3,
#                    date_time_string_format="%Y-%m-%d, %H:%M:%S")
#
# IonPump = Channel(chan_nums=[119], init_cmds=volt_cmds, chan_name="IONPUMP",
#                   conv_func=lambda x: x * 100,
#                   # The ion pump controller has been configured to output 1 V/100 nA -JAG 02/12/2018
#                   log_drive=log_drive + 'IonPump/',
#                   log_backup=log_backup + 'IonPump/',
#                   error_drive=error_drive + 'IonPump/',
#                   log_freq=3,
#                   date_time_string_format="%Y-%m-%d, %H:%M:%S")


# Define multimeter
kmm = Keithley(port='COM6', timeout=15, debug=False,
               channels=[MagField])
kmm.preamble = preamble

# This opens the serial port and initializes the multimeter
with kmm:
    # Initialize channels
    kmm.init_channels()
    print('Initialized!')
    delay = datetime.timedelta(seconds=5)
    while True:
        try:
            curr_time = datetime.datetime.now()
            # get data
            kmm.get_data()
            # sleep
            while curr_time + delay > datetime.datetime.now():
                # print('sleeping at ' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                time.sleep(1)

        except (KeyboardInterrupt, SystemExit):
            print('You hit Ctrl-C')
            break


