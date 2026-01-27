from barometer.paths import get_data_dir
import pandas
from datetime import datetime, timedelta
import logging
from barometer.paths import get_logs_dir

def load_data(include_archives=False):
    data_file = get_data_dir() / 'readings.csv'
    
    if not data_file.exists():
        return None
    
    dfs = []
    df = pandas.read_csv(data_file)
    df['timestamp'] = pandas.to_datetime(df['timestamp'], format='ISO8601')
    dfs.append(df)
    
    if include_archives:
        archive_dir = get_archive_dir()
        if archive_dir.exists():
            for csv_file in archive_dir.rglob('*.csv'):
                df_archive = pandas.read_csv(csv_file)
                df_archive['timestamp'] = pandas.to_datetime(df_archive['timestamp'], format='ISO8601')
                dfs.append(df_archive)
    
    if not dfs:
        return None
    
    combined = pandas.concat(dfs, ignore_index=True)
    combined = combined.sort_values('timestamp').reset_index(drop=True)
    combined = combined.drop_duplicates(subset=['timestamp'], keep='last')
    
    return combined

def setup_logging(verbose=False):
    # configure logging
    level = logging.DEBUG if verbose else logging.INFO
    log_file = get_logs_dir() / 'barometer.log'
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )




