import logger as kl
import numpy as np
import datetime
import time
from pathlib import Path


# class FakeDataSource:
#     def __init__(self, data_funcs):
#         self.data_funcs = data_funcs
#         self.t0 = datetime.datetime(2020, 1, 1, 0, 0, 0)
#
#     def get_data(self):
#         t = datetime.datetime.now() - self.t0
#         data_list = [f(t) for f in self.data_funcs]
#         return data_list


keithley_logger_temp_path = Path('C:/', 'Users', 'Justin', 'Desktop', 'Working', 'Code', 'Keithley Logger Work')
log_drive = Path(keithley_logger_temp_path, 'Log Drive')
backup_drive = Path(keithley_logger_temp_path, 'Backup Drive')
error_drive = Path(keithley_logger_temp_path, 'Error Drive')
webplot_drive = Path(keithley_logger_temp_path, 'Webplot Drive')


fake_data_channel = kl.Channel(hard_port=101, chan_name='fake data')
fake_data_group = kl.SaveGroup([fake_data_channel],
                               group_name='Fake Data', quiet=True,
                               log_drive=Path(log_drive, 'Fake Data'),
                               backup_drive=Path(backup_drive, 'Fake Data'),
                               error_drive=error_drive,
                               webplot_drive=webplot_drive)

fake_magx_channel = kl.Channel(hard_port=101, chan_name='magx fake')
fake_magy_channel = kl.Channel(hard_port=102, chan_name='magy fake')
fake_magz_channel = kl.Channel(hard_port=103, chan_name='magz fake')
mag_data_fake_group = kl.SaveGroup([fake_magx_channel, fake_magy_channel, fake_magz_channel],
                                   group_name='Mag Data Fake', quiet=True,
                                   log_drive=Path(log_drive, 'Mag Data Fake'),
                                   backup_drive=Path(backup_drive, 'Mag Data Fake'),
                                   error_drive=error_drive,
                                   webplot_drive=webplot_drive)


def add_outlier(magnitude = 100, probability = 0.1):
    if np.random.rand() < probability:
        return magnitude
    else:
        return 0


def noisy_sine(clock_time, t0=datetime.datetime(2020, 1, 12, 0, 0, 0), period=100.0, amplitude=1.0, offset=0.0,
               phase=0.0, noise_amplitude = 0.1):
    t = (clock_time - t0).total_seconds()
    omega = 2 * np.pi / period
    sig = amplitude * np.sin(omega * t + phase) + offset
    noise = noise_amplitude * np.random.normal()
    return sig + noise

# def noisy_sine(clock_time):
#     t0 = datetime.datetime(2020, 1, 12, 0, 0, 0)
#     t = (clock_time-t0).total_seconds()
#     T = 100  # period in (s)
#     omega = 2*np.pi/T
#     sig = np.sin(omega * t)
#     noise = 0.1*np.random.normal() + add_outlier()
#     return sig + noise


def generate_fake_data():
    curr_time = datetime.datetime.now()
    data = noisy_sine(curr_time)
    fake_data_channel.curr_data = noisy_sine(curr_time, period=100, amplitude=1) + add_outlier()
    fake_magx_channel.curr_data = noisy_sine(curr_time, period=20, amplitude=1, offset=3, noise_amplitude=0)
    fake_magy_channel.curr_data = noisy_sine(curr_time, period=20, amplitude=0.1, offset=4, noise_amplitude=0)
    fake_magz_channel.curr_data = noisy_sine(curr_time, period=20, amplitude=0.5, offset=5, noise_amplitude=0)
    fake_data_group.save_data(curr_time)
    mag_data_fake_group.save_data(curr_time)
    print(f'sending data to savegroup')


if __name__ == "__main__":
    while True:
        generate_fake_data()
        time.sleep(3)
