import datetime
import time
import threading
import importlib
import kmm_data_handler
import kmm_plot_funcs


def logger_routine(keithley_device, save_groups, t_read_freq):
    # This opens the serial port and initializes the multimeter
    with keithley_device as kmm:
        # Initialize channels
        channels = [chan for save_group in save_groups for chan in save_group.channels]
        kmm.init_measurement(channels)
        print('Initialized!')
        delay = datetime.timedelta(seconds=t_read_freq)
        while True:
            try:
                curr_time = datetime.datetime.now()
                kmm.get_data(save_groups)
                while curr_time + delay > datetime.datetime.now():
                    time.sleep(1)
            except (KeyboardInterrupt, SystemExit):
                print('You hit Ctrl-C')
                break


def main():
    log_drive = 'Y:/E6/DataRaid E6/Data/KeithleyLogger/'
    backup_drive = 'C:/KeithleyLoggerBackup/'
    error_drive = 'C:/KeithleyLoggerBackup/Error/'
    webplot_drive = '//oxford.physics.berkeley.edu/web/internal/e6/'

    kmm_port = 'COM6'  # Port for Keithley multimeter (kmm)

    t_read_freq = 30  # How often to query Keithley multimeter for new data
    t_plot_freq = datetime.timedelta(seconds=10)  # How often to produce new plots
    t_plot_history = datetime.timedelta(hours=12)  # How far back in history the plots should reach

    # Bartington Mag690-100 outputs 100 mV/uT = 0.01 V/mG so 100 mG/V, 100 uG/mV
    mag_x = kmm_data_handler.Channel(hard_port=101, chan_name='Mag X', conv_func=lambda v: v * 100)
    mag_y = kmm_data_handler.Channel(hard_port=102, chan_name='Mag Y', conv_func=lambda v: v * 100)
    mag_z = kmm_data_handler.Channel(hard_port=103, chan_name='Mag Z', conv_func=lambda v: v * 100)
    mag_group = kmm_data_handler.SaveGroup([mag_x, mag_y, mag_z], group_name='MagField', quiet=True,
                                           log_drive=log_drive + 'MagField/',
                                           backup_drive=backup_drive + 'MagField/',
                                           error_drive=error_drive,
                                           webplot_drive=webplot_drive)
    # mag_group.plotter.plot_func = kmm_plot_funcs.make_mag_plot

    # Terranova ion gauge controller reads out a pseudo-logarithmic voltage. It is 0.5 volts per decade and has
    # an offset. The Terranova manual expresses this in a very confusing way that makes it difficult to determine
    # the offset. There is a write up in onenote and on the server about it. The data saved here is Log10(P/P0).
    # The actual pressures (1e-10 level) are too high of precision to be straightforwardly stored in the .csv.
    ion_gauge = kmm_data_handler.Channel(hard_port=110, chan_name='IonGauge', conv_func=lambda v: (v - 5) / 0.5)
    ion_gauge_group = kmm_data_handler.SaveGroup([ion_gauge], group_name='IonGauge', quiet=True,
                                                 log_drive=log_drive + 'IonGauge/',
                                                 backup_drive=backup_drive + 'IonGauge/',
                                                 error_drive=error_drive,
                                                 webplot_drive=webplot_drive)
    # ion_gauge_group.plotter.plot_func = kmm_plot_funcs.make_ion_gauge_plot

    # Gamma ion pump controller outputs a logarithmic voltage which is related to either the measured pressure or
    # current of the ion pump. Now it is configured to give a logarithmic reading of the current. The offset is
    # adjustable and set to 10 volts. This means that a current 1 A would register as 10 volts and 1e-8 A (10 nA)
    # would register as 2V. The data saved here is Log10(I/I0).
    ion_pump = kmm_data_handler.Channel(hard_port=104, chan_name='IonPump', conv_func=lambda v: (v - 10))
    ion_pump_group = kmm_data_handler.SaveGroup([ion_pump], group_name='IonPump', quiet=True,
                                                log_drive=log_drive + 'IonPump/',
                                                backup_drive=backup_drive + 'IonPump/',
                                                error_drive=error_drive,
                                                webplot_drive=webplot_drive)
    # ion_pump_group.plotter.plot_func = kmm_plot_funcs.make_ion_pump_plot

    # Omega temperature converters readout 1 degree per mV.
    # temp_exp_cloud = kmm_data_handler.Channel(hard_port=108, chan_name='Temp_exp_cloud', conv_func=lambda v: 1000 * v)
    # temp_exp_table = kmm_data_handler.Channel(hard_port=110, chan_name='Temp_exp_table', conv_func=lambda v: 1000 * v)
    # # temp_bake = kmm_data_handler.Channel(hard_port=111, chan_name='Temp_bake', conv_func=lambda v: 1000 * v)
    # # temp_gauge = kmm_data_handler.Channel(hard_port=113, chan_name='Temp_gauge', conv_func=lambda v: 1000 * v)
    # temp_group = kmm_data_handler.SaveGroup([temp_exp_cloud, temp_exp_table], group_name='Temp', quiet=True,
    #                                         log_drive=log_drive + 'Temp/',
    #                                         backup_drive=backup_drive + 'Temp/',
    #                                         error_drive=error_drive,
    #                                         webplot_drive=webplot_drive)
    # temp_group.plotter.ylabel = r'Temperature ($^{\circ}C)$'

    # Omega temperature converters readout 1 degree per mV.
    # mot_gate = kmm_data_handler.Channel(hard_port=116, chan_name='mot gate', conv_func=lambda v: 1000 * v)
    # sci_east_upper = kmm_data_handler.Channel(hard_port=117, chan_name='sci east upper', conv_func=lambda v: 1000 * v)
    # sci_west_upper = kmm_data_handler.Channel(hard_port=118, chan_name='sci west upper', conv_func=lambda v: 1000 * v)
    # pump_west = kmm_data_handler.Channel(hard_port=119, chan_name='pump west', conv_func=lambda v: 1000 * v)
    # four_way_x = kmm_data_handler.Channel(hard_port=120, chan_name='4 way x', conv_func=lambda v: 1000 * v)
    # bake_group = kmm_data_handler.SaveGroup([mot_gate, sci_east_upper, sci_west_upper, pump_west, four_way_x], group_name='Bake', quiet=True,
    #                                         log_drive=log_drive + 'Bake/',
    #                                         backup_drive=backup_drive + 'Bake/',
    #                                         error_drive=error_drive,
    #                                         webplot_drive=webplot_drive)
    # bake_group.plotter.ylabel = r'Temperature ($^{\circ}C)$'
    #
    # sci_gate = kmm_data_handler.Channel(hard_port=115, chan_name='sci gate', init_cmds_template=kmm_data_handler.Controller.thcpl_cmds)
    # sci_south_lower = kmm_data_handler.Channel(hard_port=114, chan_name='sci south lower', init_cmds_template=kmm_data_handler.Controller.thcpl_cmds)
    # lower_bucket = kmm_data_handler.Channel(hard_port=113, chan_name='lower bucket', init_cmds_template=kmm_data_handler.Controller.thcpl_cmds)
    # angle_bellows = kmm_data_handler.Channel(hard_port=106, chan_name='angle bellows', init_cmds_template=kmm_data_handler.Controller.thcpl_cmds)
    # rga = kmm_data_handler.Channel(hard_port=111, chan_name='rga', init_cmds_template=kmm_data_handler.Controller.thcpl_cmds)
    # turbo = kmm_data_handler.Channel(hard_port=108, chan_name='turbo', init_cmds_template=kmm_data_handler.Controller.thcpl_cmds)
    # bake_group_2 = kmm_data_handler.SaveGroup([sci_gate, sci_south_lower, lower_bucket, angle_bellows, rga, turbo],
    #                                         group_name='Bake 2', quiet=True,
    #                                         log_drive=log_drive + 'Bake 2/',
    #                                         backup_drive=backup_drive + 'Bake 2/',
    #                                         error_drive=error_drive,
    #                                         webplot_drive=webplot_drive)
    # bake_group_2.plotter.ylabel = r'Temperature ($^{\circ}C)$'
    #
    # sci_ion = kmm_data_handler.Channel(hard_port=101, chan_name='sci ion', init_cmds_template=kmm_data_handler.Controller.thcpl_cmds)
    # neg = kmm_data_handler.Channel(hard_port=102, chan_name='neg', init_cmds_template=kmm_data_handler.Controller.thcpl_cmds)
    # pump_east = kmm_data_handler.Channel(hard_port=103, chan_name='pump east', init_cmds_template=kmm_data_handler.Controller.thcpl_cmds)
    # bake_group_3 = kmm_data_handler.SaveGroup([sci_ion, neg, pump_east],
    #                                         group_name='Bake 3', quiet=True,
    #                                         log_drive=log_drive + 'Bake 3/',
    #                                         backup_drive=backup_drive + 'Bake 3/',
    #                                         error_drive=error_drive,
    #                                         webplot_drive=webplot_drive)
    # bake_group_3.plotter.ylabel = r'Temperature ($^{\circ}C)$'

    # save_groups = [mag_group, ion_pump_group, temp_group, ion_gauge_group]
    save_groups = [mag_group, ion_gauge_group, ion_pump_group]

    for save_group in save_groups:
        save_group.plotter.t_plot_freq = t_plot_freq
        save_group.plotter.t_plot_history = t_plot_history
        save_group.plotter.show = False

    kmm = kmm_data_handler.Keithley(port=kmm_port, timeout=15, quiet=True)
    controller = kmm_data_handler.Controller(save_groups=save_groups, device=kmm)

    logger_thread = threading.Thread(target=logger_routine, args=(controller, t_read_freq))
    logger_thread.start()


if __name__ == '__main__':
    main()
