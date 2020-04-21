import datetime
import time
import kmm_data_handler
import threading
import importlib
import matplotlib.pyplot as plt
import matplotlib

importlib.reload(kmm_data_handler)


def logger_routine(controller):
    # This opens the serial port and initializes the multimeter
    with controller.device:
        # Initialize channels
        controller.init_measurement()
        print('Initialized!')
        delay = datetime.timedelta(seconds=5)
        while True:
            try:
                curr_time = datetime.datetime.now()
                controller.get_data()
                while curr_time + delay > datetime.datetime.now():
                    time.sleep(1)

            except (KeyboardInterrupt, SystemExit):
                print('You hit Ctrl-C')
                break


def plotter_routine(controller):
    plt.ioff()
    fig = plt.figure('Data Figure')
    ax = fig.add_subplot(1,1,1)
    fig.show()
    while True:
        for save_group in controller.save_groups:
            time_delta = datetime.timedelta(minutes = 5)
            stop_time = datetime.datetime.now()
            start_time = stop_time - time_delta
            data = save_group.plotter.plot_data(start_time, stop_time, grab_data=False)
            ax.cla()
            data.plot(ax=ax, style=['.', '.', '.'])
            plt.draw()
            fig.canvas.start_event_loop(5)


# Setup communication with Keithley 2700 multimeter, starting with the following
# preamble. This ensures the setup is the same every time, regardless if it has
# been adjusted
def main():
    log_drive = 'Y:/E6/DataRaid E6/Data/KeithleyLogger/'
    backup_drive = 'C:/KeithleyLoggerBackup/'
    error_drive = 'C:/KeithleyLoggerBackup/Error/'

    kmm_port = 'COM6' # Port for Keithley multimeter (kmm)

    # Bartington Mag690-100 outputs 100 mV/uT = 0.01 V/mG so 100 mG/V, 100 uG/mV
    MagX = kmm_data_handler.Channel(hard_port=101, chan_name='Mag X', conv_func=lambda x: x * 100)
    MagY = kmm_data_handler.Channel(hard_port=104, chan_name='Mag Y', conv_func=lambda x: x * 100)
    MagZ = kmm_data_handler.Channel(hard_port=103, chan_name='Mag Z', conv_func=lambda x: x * 100)
    Mag_Group = kmm_data_handler.SaveGroup([MagX, MagY, MagZ], group_name='MagField', quiet=True,
                                           log_drive=log_drive + 'MagField/',
                                           backup_drive=backup_drive + 'MagField/',
                                           error_drive=error_drive + 'MagField/')

    save_groups = [Mag_Group]

    kmm = kmm_data_handler.Keithley(port='COM6', timeout=15, quiet=True)
    controller = kmm_data_handler.Controller(save_groups=save_groups, device=kmm, read_freq=5)

    logger_thread = threading.Thread(target=logger_routine, args=(controller,))
    logger_thread.start()
    time.sleep(1)
    plotter_thread = threading.Thread(target=plotter_routine, args=(controller,))
    plotter_thread.start()


if __name__ == '__main__':
    main()
