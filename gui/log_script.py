import gui.logger as logger
from pathlib import Path
from PyQt5 import QtWidgets
from plotwindow import PlotWindow, IonPumpPlotWindow
from ui_plottermanagerwindow import PlotterManagerWindow
from loader import Loader
import sys

app = QtWidgets.QApplication(sys.argv)

log_drive = Path('Y:/', 'smalldata-e6', 'KeithleyLogger Data')
backup_drive = Path('C:/', 'KeithleyLoggerBackup')
error_drive = Path('C:/', 'KeithleyLoggerBackup,' 'Error')
webplot_drive = Path('//oxford.physics.berkeley.edu/web/internal/e6/')

keithley_port = 'COM6'  # Port for Keithley multimeter (kmm)
t_read_freq = 30  # How often to query Keithley multimeter for new data

# Bartington Mag690-100 outputs 100 mV/uT = 0.01 V/mG so 100 mG/V, 100 uG/mV
mag_x = logger.Channel(hard_port=101, chan_name='Mag X', conv_func=lambda v: v * 100)
mag_y = logger.Channel(hard_port=102, chan_name='Mag Y', conv_func=lambda v: v * 100)
mag_z = logger.Channel(hard_port=103, chan_name='Mag Z', conv_func=lambda v: v * 100)
mag_group = logger.SaveGroup([mag_x, mag_y, mag_z], group_name='MagField', quiet=True,
                             log_drive=Path(log_drive, 'MagField'),
                             backup_drive=Path(backup_drive, 'MagField'),
                             error_drive=error_drive,
                             webplot_drive=webplot_drive)

# Terranova ion gauge controller reads out a pseudo-logarithmic voltage. It is 0.5 volts per decade and has
# an offset. The Terranova manual expresses this in a very confusing way that makes it difficult to determine
# the offset. There is a write up in onenote and on the server about it. The data saved here is Log10(P/P0).
# The actual pressures (1e-10 level) are too high of precision to be straightforwardly stored in the .csv.
ion_gauge = logger.Channel(hard_port=106, chan_name='IonGauge', conv_func=lambda v: (v - 5) / 0.5)
ion_gauge_group = logger.SaveGroup([ion_gauge], group_name='IonGauge', quiet=True,
                                   log_drive=Path(log_drive, 'IonGauge'),
                                   backup_drive=Path(backup_drive, 'IonGauge'),
                                   error_drive=error_drive,
                                   webplot_drive=webplot_drive)

# Gamma ion pump controller outputs a logarithmic voltage which is related to either the measured pressure or
# current of the ion pump. Now it is configured to give a logarithmic reading of the current. The offset is
# adjustable and set to 10 volts. This means that a current 1 A would register as 10 volts and 1e-8 A (10 nA)
# would register as 2V. The data saved here is Log10(I/I0).
ion_pump = logger.Channel(hard_port=104, chan_name='IonPump', conv_func=lambda v: (v - 10))
ion_pump_group = logger.SaveGroup([ion_pump], group_name='IonPump', quiet=True,
                                  log_drive=Path(log_drive, 'IonPump'),
                                  backup_drive=Path(backup_drive, 'IonPump'),
                                  error_drive=error_drive,
                                  webplot_drive=webplot_drive)

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

save_groups = [mag_group, ion_pump_group, ion_gauge_group]

keithley_device = logger.Keithley(port=keithley_port, timeout=15, quiet=False)
controller = logger.Logger(save_groups=save_groups, device=keithley_device, log_freq=t_read_freq, quiet=False)

mag_plotter = PlotWindow(Loader(Path(log_drive, 'MagField'), 'MagField', quiet=True),
                         save_path=webplot_drive, ylabel='Magnetic Field', units_label='(mG)')
ion_pump_plotter = IonPumpPlotWindow(Loader(Path(log_drive, 'IonPump'), 'IonPump', quiet=True),
                                     save_path=webplot_drive, conv_func=(lambda x: 10**x*1e9),
                                     ylabel='Ion Pump Current', units_label='(nA)')
ion_gauge_plotter = PlotWindow(Loader(Path(log_drive, 'IonGauge'), 'IonGauge', quiet=True),
                               save_path=webplot_drive, conv_func=(lambda x: 10**x),
                               ylabel='Ion Gauge Pressure', units_label='(torr)')

plotters = [mag_plotter, ion_pump_plotter, ion_gauge_plotter]
plotter_manager = PlotterManagerWindow(plotters)
plotter_manager.show()

sys.exit(app.exec_())
