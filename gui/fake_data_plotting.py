from PyQt5 import QtCore, QtWidgets
from loader import Loader
from plotwindow import PlotWindow
from ui_plottermanagerwindow import PlotterManagerWindow
from pathlib import Path
import sys

app = QtWidgets.QApplication(sys.argv)
keithley_logger_temp_path = Path('C:/', 'Users', 'Justin', 'Desktop', 'Working', 'Code', 'Keithley Logger Work')
work_dir = Path('C:/', 'Users', 'Justin', 'Desktop', 'Working', 'Code', 'Keithley Logger Work', 'MagField',
                'MagField')
log_drive = Path(keithley_logger_temp_path, 'Log Drive', 'Fake Data')
log_drive_2 = Path(keithley_logger_temp_path, 'Log Drive', 'Mag Data Fake')
file_prefix = 'Fake Data'
fake_data_loader = Loader(log_drive, file_prefix, quiet=True)
mag_data_fake_loader = Loader(log_drive_2, 'Mag Data Fake', quiet=True)
mag_data_loader = Loader(work_dir, 'MagField', quiet=True)
plotter1 = PlotWindow(fake_data_loader)
plotter2 = PlotWindow(mag_data_fake_loader)
plotter3 = PlotWindow(mag_data_loader)

ui = PlotterManagerWindow([plotter1, plotter2, plotter3])
ui.show()
sys.exit(app.exec_())