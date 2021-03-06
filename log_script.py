import sys
from pathlib import Path
from PyQt5 import QtWidgets
import logger
from plotwindow import PlotWindow
from ui_plottermanagerwindow import PlotterManagerWindow


def setup_mag_group(log_drive, backup_drive, error_drive, webplot_drive):
    # Bartington Mag690-100 outputs 100 mV/uT = 0.01 V/mG so 100 mG/V, 100 uG/mV
    mag_x = logger.Channel(hard_port=101, chan_name='Mag X', conv_func=lambda v: v * 100)
    mag_y = logger.Channel(hard_port=102, chan_name='Mag Y', conv_func=lambda v: v * 100)
    mag_z = logger.Channel(hard_port=103, chan_name='Mag Z', conv_func=lambda v: v * 100)
    mag_group = logger.SaveGroup([mag_x, mag_y, mag_z], group_name='MagField', quiet=True,
                                 log_drive=Path(log_drive, 'MagField'),
                                 backup_drive=Path(backup_drive, 'MagField'),
                                 error_drive=error_drive,
                                 webplot_drive=webplot_drive)
    mag_loader = mag_group.make_loader()
    mag_plotter = PlotWindow(mag_loader, save_path=webplot_drive, ylabel='Magnetic Field',
                             units_label='(mG)', plot_mode='multiplot')
    return mag_group, mag_plotter


def setup_ion_gauge_group(log_drive, backup_drive, error_drive, webplot_drive):
    """
    Terranova ion gauge controller reads out a pseudo-logarithmic voltage. It is 0.5 volts per decade and has
    an offset. The Terranova manual expresses this in a very confusing way that makes it difficult to determine
    the offset. There is a write up in onenote and on the server about it. The data saved here is Log10(P/P0).
    The actual pressures (1e-10 level) are too high of precision to be straightforwardly stored in the .csv.
    """
    ion_gauge = logger.Channel(hard_port=106, chan_name='IonGauge', conv_func=lambda v: (v - 5) / 0.5)
    ion_gauge_group = logger.SaveGroup([ion_gauge], group_name='IonGauge', quiet=True,
                                       log_drive=Path(log_drive, 'IonGauge'),
                                       backup_drive=Path(backup_drive, 'IonGauge'),
                                       error_drive=error_drive,
                                       webplot_drive=webplot_drive)
    ion_gauge_loader = ion_gauge_group.make_loader()
    ion_gauge_plotter = PlotWindow(ion_gauge_loader, save_path=webplot_drive, conv_func=(lambda x: 10 ** x),
                                   ylabel='Ion Gauge Pressure', units_label='(torr)', yscale='log')
    return ion_gauge_group, ion_gauge_plotter


def setup_ion_pump_group(log_drive, backup_drive, error_drive, webplot_drive):
    """
    Gamma ion pump controller outputs a logarithmic voltage which is related to either the measured pressure or
    current of the ion pump. Now it is configured to give a logarithmic reading of the current. The offset is
    adjustable and set to 10 volts. This means that a current 1 A would register as 10 volts and 1e-8 A (10 nA)
    would register as 2V. The data saved here is Log10(I/I0).
    """
    ion_pump = logger.Channel(hard_port=104, chan_name='IonPump', conv_func=lambda v: (v - 10))
    ion_pump_group = logger.SaveGroup([ion_pump], group_name='IonPump', quiet=True,
                                      log_drive=Path(log_drive, 'IonPump'),
                                      backup_drive=Path(backup_drive, 'IonPump'),
                                      error_drive=error_drive,
                                      webplot_drive=webplot_drive)
    ion_pump_loader = ion_pump_group.make_loader()

    def curr2press(curr):
        # formula given in ion pump controller to convert current (expressed in nA) to pressure (in torr)
        return 0.066 * curr * 10 ** -9 * 5600 / 7000 / 70
    ion_pump_plotter = PlotWindow(ion_pump_loader, save_path=webplot_drive, conv_func=(lambda x: 10 ** x * 1e9),
                                  ylabel='Ion Pump Current', units_label='(nA)',
                                  twinx_on=True, twinx_func=curr2press, twinx_label='Pressure (torr)')
    return ion_pump_group, ion_pump_plotter


def setup_temperature_group(log_drive, backup_drive, error_drive, webplot_drive):
    # Omega temperature converters readout 1 degree per mV.
    temp_exp_cloud = logger.Channel(hard_port=108, chan_name='Temp_exp_cloud', conv_func=lambda t: t,
                                    init_cmds_template=logger.Keithley.thrmstr_cmds)
    temp_exp_table = logger.Channel(hard_port=111, chan_name='Temp_exp_table', conv_func=lambda t: t,
                                    init_cmds_template=logger.Keithley.thrmstr_cmds)
    temp_laser_table = logger.Channel(hard_port=113, chan_name='Temp_laser_table', conv_func=lambda t: t,
                                    init_cmds_template=logger.Keithley.thrmstr_cmds)
    temp_group = logger.SaveGroup([temp_exp_cloud, temp_exp_table, temp_laser_table], group_name='LabTemp', quiet=True,
                                  log_drive=Path(log_drive, 'LabTemp'),
                                  backup_drive=Path(backup_drive, 'LabTemp'),
                                  error_drive=error_drive,
                                  webplot_drive=webplot_drive)
    temp_loader = temp_group.make_loader()
    temp_plotter = PlotWindow(temp_loader, save_path=webplot_drive, ylabel='Temperature', units_label=r'($^{\circ}C$)')
    return temp_group, temp_plotter


def main():
    app = QtWidgets.QApplication(sys.argv)

    log_drive = Path('Y:/', 'smalldata-e6', 'KeithleyLogger Data')
    backup_drive = Path('C:/', 'KeithleyLoggerBackup')
    error_drive = Path('C:/', 'KeithleyLoggerBackup,' 'Error')
    webplot_drive = Path('//oxford.physics.berkeley.edu/web/internal/e6/')

    keithley_port = 'COM6'  # Port for Keithley multimeter (kmm)
    t_read_freq = 30  # How often to query Keithley multimeter for new data

    mag_group, mag_plotter = setup_mag_group(log_drive, backup_drive, error_drive, webplot_drive)
    ion_gauge_group, ion_gauge_plotter = setup_ion_gauge_group(log_drive, backup_drive, error_drive, webplot_drive)
    ion_pump_group, ion_pump_plotter = setup_ion_pump_group(log_drive, backup_drive, error_drive, webplot_drive)
    temperature_group, temperature_plotter = setup_temperature_group(log_drive, backup_drive, error_drive, webplot_drive)

    keithley_device = logger.Keithley(port=keithley_port, timeout=15, quiet=True)
    save_groups = [mag_group, ion_pump_group, ion_gauge_group, temperature_group]
    keithley_logger = logger.Logger(save_groups=save_groups, device=keithley_device, log_freq=t_read_freq, quiet=False)
    keithley_logger.start_logging()

    plotters = [mag_plotter, ion_pump_plotter, ion_gauge_plotter, temperature_plotter]
    plotter_manager = PlotterManagerWindow(plotters)
    plotter_manager.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
