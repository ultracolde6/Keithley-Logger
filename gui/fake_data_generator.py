import kmm_data_handler as kl
import numpy as np
import datetime
import time


class FakeDataSource:
    def __init__(self, data_funcs):
        self.data_funcs = data_funcs
        self.t0 = datetime.datetime(2020, 1, 1, 0, 0, 0)

    def get_data(self):
        t = datetime.datetime.now() - self.t0
        data_list = [f(t) for f in self.data_funcs]
        return data_list
    
log_drive = 'Y:/DataRaid E6/Data/KeithleyLogger/'
backup_drive = 'C:/KeithleyLoggerBackup/'
error_drive = 'C:/KeithleyLoggerBackup/Error/'
webplot_drive = '//oxford.physics.berkeley.edu/web/internal/e6/'

fake_data = kl.Channel(hard_port=101, chan_name='fake data')
fake_data_group = kl.SaveGroup([fake_data],
                               group_name='Fake Data', quiet=True,
                               log_drive=log_drive + 'Fake Data/',
                               backup_drive=backup_drive + 'Fake Data/',
                               error_drive=error_drive,
                               webplot_drive=webplot_drive)


def add_outlier():
    if np.random.rand() < 0.1:
        return 100
    else:
        return 0


def noisy_sine(clock_time):
    t0 = datetime.datetime(2020, 1, 12, 0, 0, 0)
    t = (clock_time-t0).total_seconds()
    T = 100  # period in (s)
    omega = 2*np.pi/T
    sig = np.sin(omega * t)
    noise = 0.1*np.random.normal() + add_outlier()
    return sig + noise


def generate_fake_data():
    curr_time = datetime.datetime.now()
    data = noisy_sine(curr_time)
    fake_data.curr_data = data
    fake_data_group.save_data(curr_time)
    print(f'sending {data} to savegroup')


if __name__ == "__main__":
    while True:
        generate_fake_data()
        time.sleep(3)
