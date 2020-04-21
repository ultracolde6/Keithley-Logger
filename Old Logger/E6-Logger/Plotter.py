#!/usr/bin/python
import time
from datetime import datetime, date, timedelta
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
 
import MultiTemp1
import MultiTemp2
import IonGauge
import IonPump


web_plot_dir = 'Z:/E6/www/' 
plotInterval = .5 # in hours
#webPlotInterval = 1 # in minutes
webPlotInterval = 5 # in seconds
lastPlot = datetime.now() - timedelta(hours = 1)
lastWebPlot = datetime.now() - timedelta(hours = 1)

def save_web_plots():
    print time.strftime("%Y-%m-%d %H:%M:%S: Generating Web Plots")
    #Temp1.save_web_plot(web_plot_dir)
    MultiTemp1.save_web_plot(web_plot_dir)    
    MultiTemp2.save_web_plot(web_plot_dir)   
    IonGauge.save_web_plot(web_plot_dir)	
    IonPump.save_web_plot(web_plot_dir)		
    plt.close('all')

def save_plots():
    print time.strftime("%Y-%m-%d %H:%M:%S: Generating Plots")
    #Temp1.save_plot()
    MultiTemp1.save_plot()    
    MultiTemp2.save_plot()    
    IonGauge.save_plot() 
    IonPump.save_plot() 	
    plt.close('all')

while True:
    try:
        # sleep
        
        time.sleep(1)
        # get data
        curDatetime = datetime.now()
       # if (curDatetime.minute % webPlotInterval) == 0 and (curDatetime - lastWebPlot) > timedelta(minutes=1):
        if (curDatetime - lastWebPlot) > timedelta(seconds=10):
            try:
                save_web_plots()
            except Exception as e:
                print 'Error generating plots:'
                print e
            lastWebPlot = curDatetime
            

        if (curDatetime.hour % plotInterval) == 0 and (curDatetime - lastPlot) > timedelta(hours=1):
            try:
                save_plots()
            except Exception as e:
                print 'Error generating plots:'
                print e
            lastPlot = curDatetime

    except (KeyboardInterrupt, SystemExit):
        print "You hit Ctrl-C"
        break
