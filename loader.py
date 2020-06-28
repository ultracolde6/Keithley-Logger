import numpy as np
import pandas as pd
import datetime
from pathlib import Path
import csv


class Loader:
    def __init__(self, log_drive, file_prefix, date_format='%Y-%m-%d', time_format='%H:%M:%S', quiet=True):

        self.log_drive = log_drive
        self.file_prefix = file_prefix
        self.date_format = date_format
        self.time_format = time_format
        self.datetime_format = f'{self.date_format} {self.time_format}'
        self.quiet = quiet

        self.data = None
        self.loaded_start_date = None
        self.loaded_stop_date = None
        self.lines_loaded = 0

    def grab_dates(self, start_date, stop_date):
        """
        grab_dates parses through the data log and returns a pandas data frame containing all of the data
        for the days within start_date to stop_date.
        """
        if isinstance(start_date, datetime.datetime):
            start_date = start_date.date()
        if isinstance(stop_date, datetime.datetime):
            stop_date = stop_date.date()

        if not self.quiet:
            print(f'Grabbing data for dates '
                  f'{start_date.strftime(self.date_format)} through {stop_date.strftime(self.date_format)}')
        t0 = datetime.datetime.now()
        data = pd.DataFrame()
        date_range = [dt.date() for dt in pd.date_range(start_date, stop_date).to_pydatetime()]
        for date in date_range:
            date_str = date.strftime(self.date_format)
            file_name = f'{self.file_prefix} {date_str}.csv'
            file_path = Path(self.log_drive, file_name)
            try:
                new_data = pd.read_csv(file_path,
                                       header=0,
                                       parse_dates={'datetime': ['date', 'time']},
                                       index_col='datetime',
                                       infer_datetime_format=True)
                new_data.index = pd.to_datetime(new_data.index, format=self.datetime_format)
                data = data.append(new_data)
            except FileNotFoundError:
                print(f'File not found: {file_path}')
        if not self.quiet:
            tf = datetime.datetime.now()
            dt = (tf-t0).total_seconds()
            print(f'Grabbed data for dates '
                  f'{start_date.strftime(self.date_format)} through '
                  f'{stop_date.strftime(self.date_format)}')
            print(f'Grabbing took {dt:.3f} s')
        return data

    def refresh_data(self, start_datetime):
        """
        refresh_data parses through the data log returning a pandas data frame which contains all of the data
        from start_datetime.date() through the present moment. The Loader class keeps track of which data has
        previously been loaded by saving previously loaded data in self.data and keeping track of how many
        lines of data have already been read in from the data file corresponding to the present day in
        self.lines_loaded. Correspondingly there are chains of logic to ensure this method exhibits the
        appropriate behaviour depending on the state of the data log and the data which is loaded into self.data
        and the time period for which data is being requested.
        """
        start_date = start_datetime.date()
        stop_datetime = datetime.datetime.now()
        stop_date = stop_datetime.date()

        if not self.quiet:
            print(f'Refreshing data from '
                  f'{start_datetime.strftime(self.datetime_format)} through '
                  f'{stop_datetime.strftime(self.datetime_format)}')
        t0 = datetime.datetime.now()

        # If no data is loaded of if the data range being requested ranges to a time earlier than the
        # start of the loaded data a `hard reset' is required. A hard reset simply involves clearing self.data
        # and resetting some flags.
        hard_reset = False
        if self.loaded_start_date is None:
            hard_reset = True
        elif self.loaded_start_date is not None:
            if start_date < self.loaded_start_date:
                hard_reset = True
            elif self.loaded_start_date < start_date:
                # Remove data from dates older than the range which is being requested to save memory
                time_mask = np.logical_and(np.array(start_datetime <= self.data.index),
                                           np.array(self.data.index <= stop_datetime))
                self.data = self.data.loc[time_mask]
                self.loaded_start_date = start_datetime.date()
        if hard_reset:
            self.data = pd.DataFrame()
            self.loaded_start_date = None
            self.loaded_stop_date = None
            self.lines_loaded = 0

        date_range = [dt.date() for dt in pd.date_range(start_date, stop_date).to_pydatetime()]
        for date in date_range:
            if self.loaded_start_date is None or self.loaded_stop_date is None:
                pass
            else:
                if date < self.loaded_stop_date:
                    # dates with date < self.loaded_stop_date should already be included in self.data.
                    # Skip to next date.
                    continue
                elif date > self.loaded_stop_date:
                    # if date > self.loaded_stop_date it means we have moved onto a new file
                    # and must start reading at the beginning.
                    self.lines_loaded = 0
                elif date == self.loaded_stop_date:
                    # if date == self.loaded_stop_date then current value of self.lines_loaded
                    # will be used to load only recent data.
                    pass
            date_str = date.strftime(self.date_format)
            file_name = f'{self.file_prefix} {date_str}.csv'
            file_path = Path(self.log_drive, file_name)
            try:
                # Load in new data. Note that lines up until line number self.lines_loaded are skipped
                new_data = pd.read_csv(file_path,
                                       header=0,
                                       skiprows=range(1, self.lines_loaded + 1),
                                       parse_dates={'datetime': ['date', 'time']},
                                       index_col='datetime',
                                       infer_datetime_format=True)
                new_data.index = pd.to_datetime(new_data.index, format=self.datetime_format)
                new_row_count = new_data.shape[0]
                if new_row_count > 0:
                    self.data = self.data.append(new_data)
                if date == stop_date:
                    self.lines_loaded += new_row_count
            except FileNotFoundError:
                print(f'File not found: {file_path}')
            if self.loaded_start_date is None:
                self.loaded_start_date = date
            self.loaded_stop_date = date

        if not self.quiet:
            tf = datetime.datetime.now()
            dt = (tf-t0).total_seconds()
            print(f'Data refreshed to include dates '
                  f'{start_date.strftime(self.date_format)} through '
                  f'{stop_date.strftime(self.date_format)}')
            print(f'Refreshing took {dt:.3f} s')
        return self.data

    def get_header(self):
        file_path = list(Path(self.log_drive).glob('*.csv'))[0]  # extract header from first matching file
        with file_path.open('r', newline='') as file:
            reader = csv.reader(file)
            header = next(reader)
        return header
