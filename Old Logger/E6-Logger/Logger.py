import time
import math
import serial
import datetime
from kmm_data_handler import *
                
# Setup communication with Keithley 2700 multimeter, starting with the following
# preamble. This ensures the setup is the same every time, regardless if it has
# been adjusted
preamble = ["*RST\n",
            'SYST:PRES\n',
            "SYST:BEEP OFF\n",
            "TRAC:CLE\n",
            "TRAC:CLE:AUTO OFF\n",
            "INIT:CONT OFF\n",
            "TRIG:COUN 1\n",
            "FORM:ELEM READ\n"]
            
rtdCmds = ["SENS:FUNC 'TEMP',(@{chan})\n",
            "SENS:TEMP:TRAN FRTD,(@{chan})\n",
            "SENS:TEMP:FRTD:TYPE PT100,(@{chan})\n",
            "SENS:TEMP:NPLC 5,(@{chan})\n"]

thcplCmds = ["SENS:FUNC 'TEMP',(@{chan})\n",
            "SENS:TEMP:TRAN TC,(@{chan})\n",
            "SENS:TEMP:TC:TYPE K,(@{chan})\n",
            "SENS:TEMP:TC:RJUN:RSEL INT,(@{chan})\n",
            "SENS:TEMP:NPLC 5,(@{chan})\n"]

voltCmds = ["SENS:FUNC 'VOLT',(@{chan})\n",
           "SENS:VOLT:NPLC 5,(@{chan})\n",
           "SENS:VOLT:RANG 5,(@{chan})\n"]

# Define channels to scan, and then bind them to the multimeter
# class channel:
#    def __init__(self, chanNums = [], initCmds = [], name = "default", \
#                 convData = lambda x: x, \
#                 logD = "W:/E4/logging/", \
#                 logDBackup = "C:/Documents and Settings/E4/My Documents/python apps/", \
#                 errD = "C:/Documents and Settings/E4/My Documents/python apps/", \
#                 logfreq = 60, \
#                 dateTimeStringFormat = "%Y-%m-%d %H:%M:%S")
# class keithley:
#    def __init__(self, channels = [], port=3, timeout=2)


#~ magField = channel(chanNums = [101, 102, 103], initCmds = voltCmds, name = "VOLT1",\
                    #~ convData = lambda x: x/10, \
                    #~ logD = "Z:/E6/MagLog/", \
                    #~ logDBackup = "C:/Data/MagLog2018", \
                    #~ errD = "C:/Data/MagLog2018", \
                    #~ logfreq = 10, \
                    #~ dateTimeStringFormat = "%Y-%m-%d, %H:%M:%S")



MultiTemp1 = channel(chanNums = [104, 105, 106, 117, 108, 116], initCmds = voltCmds, name = "MULTITEMP1",
                    convData = lambda x: x*1000,
                    # x*1000 chosen because the Omega temperature to voltage converters output 1 mV/C -JAG 02/12/2018 
                    #logD = "Z:/E6/TempLog/", \
                    #logDBackup = "C:/Data/TempLog2018", \
                    #errD = "C:/Data/TempLog2018", \
                    logD = "Y:/Data/KeithleyLogger/MultiTemp1/",
                    logDBackup = "C:/KeithleyLoggerBackup/MultiTemp1/",
                    errD = "C:/KeithleyLoggerBackup/Error/",
                    logfreq = 3,
                    dateTimeStringFormat = "%Y-%m-%d, %H:%M:%S")

MultiTemp2 = channel(chanNums = [110, 111, 112, 113, 114, 115], initCmds = voltCmds, name = "MULTITEMP2",
                    convData = lambda x: x*1000,
                    # x*1000 chosen because the Omega temperature to voltage converters output 1 mV/C -JAG 02/12/2018         
                    #logD = "Z:/E6/TempLog/",
                    #logDBackup = "C:/Data/TempLog2018",
                    #errD = "C:/Data/TempLog2018",
                    logD = "Y:/Data/KeithleyLogger/MultiTemp2/",
                    logDBackup = "C:/KeithleyLoggerBackup/MultiTemp2/",
                    errD = "C:/KeithleyLoggerBackup/Error/",
                    logfreq = 3,
                    dateTimeStringFormat = "%Y-%m-%d, %H:%M:%S")

IonGauge = channel(chanNums = [118], initCmds = voltCmds, name = "IONGAUGE",
                    convData = lambda x: (x-4.935)/0.5004,
                    # The ion gauge outputs a logarithmic voltage which is strangely documented in the TERRANOVA ion gauge controller manual. I found the in the code to give roughly log10(P) (P in torr) according to the formula in the documentation. -JAG 02/12/2018 
                    #logD = "Z:/E6/IonLog/",
                    #logDBackup = "C:/Data/IonLog2018",
                    #errD = "C:/Data/IonLog2018",
                    logD = "Y:/Data/KeithleyLogger/IonGauge/",
                    logDBackup = "C:/KeithleyLoggerBackup/IonGauge/",
                    errD = "C:/KeithleyLoggerBackup/Error/",
                    logfreq = 3,
                    dateTimeStringFormat = "%Y-%m-%d, %H:%M:%S")
                    
IonPump = channel(chanNums = [119], initCmds = voltCmds, name = "IONPUMP",
                    convData = lambda x: x*100,
                    # The ion pump controller has been configured to output 1 V/100 nA -JAG 02/12/2018
                    #logD = "Z:/E6/IonPumpLog/",
                    #logDBackup = "C:/Data/IonPumpLog2018",
                    #errD = "C:/Data/IonPumpLog2018",
                    logD = "Y:/Data/KeithleyLogger/IonPump/",
                    logDBackup = "C:/KeithleyLoggerBackup/IonPump/",
                    errD = "C:/KeithleyLoggerBackup/Error/",
                    logfreq = 3,
                    dateTimeStringFormat = "%Y-%m-%d, %H:%M:%S")


# Define multimeter
kmm = keithley(port = 1 - 1, timeout=15, debug=False,
        channels=[MultiTemp1, MultiTemp2, IonGauge, IonPump]) 
kmm.preamble = preamble

# This opens the serial port and initializes the multimeter
with kmm:
    # Initialize channels
    kmm.initChannels()
    print "Initialized!"
    delay = datetime.timedelta(seconds=5)
    while True:
        try:
            curtime = datetime.datetime.now()
            # get data
            kmm.getData()
            # sleep
            while curtime + delay > datetime.datetime.now():
                print('sleeping at' + dattime.datetime.now())
                time.sleep(1)
                
        except (KeyboardInterrupt, SystemExit):
            print "You hit Ctrl-C"
            break
