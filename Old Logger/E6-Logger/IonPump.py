#!/usr/bin/env python

from LogDisplay import TempDisplay
from os import system, path

logDirectory = 'Y:/Data/KeithleyLogger/IonPump/'

log = TempDisplay(logDirectory, 'IONPUMP', columns = ('Current (nA)',), title = 'IonPump', resample=False)
if __name__ == "__main__":
    log.plot()
    log.loop()
    
def save_plot(stop=False, start=False, days=1):
    log.save_plot(stop, start, days)
    
def save_web_plot(dir, stop=False, start=False, days=1):
    filename = "%s.png" % (log.name)
    file = path.realpath(path.join(dir, filename))
    log.save_plot(stop, start, days, file=file)