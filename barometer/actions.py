# try putting more logic here to make both cli and web code cleaner
import logging
from datetime import datetime, timedelta
import shutil
from pathlib import Path
import pandas
import psutil
from barometer.paths import get_config_file, get_data_dir, get_archive_dir, get_logs_dir
from barometer.data import load_data


def archive_old_data(keep_days=90):
    """
    Archive old logs and data.
    
    Args:
        keep_days: Number of days of recent data to keep
        
    Returns:
        dict: {
            'success': bool,
            'archived_items': int,
            'message': str,
            'archive_path': Path or None
        }
    """
    try:
        archive_dir = get_archive_dir() / datetime.now().strftime('%Y-%m')
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        archived_items = 0
        
        # Archive logs
        log_file = get_logs_dir() / 'barometer.log'
        if log_file.exists():
            log_size = log_file.stat().st_size / 1024 / 1024
            if log_size > 10:
                shutil.copy(log_file, archive_dir / 'barometer.log')
                log_file.write_text('')
                archived_items += 1
        
        # Archive old CSV data
        df = load_data()
        if df is not None and not df.empty:
            cutoff = datetime.now() - timedelta(days=keep_days)
            old_data = df[df['timestamp'] < cutoff]
            recent_data = df[df['timestamp'] >= cutoff]
            
            if not old_data.empty:
                old_data.to_csv(archive_dir / 'readings_archive.csv', index=False)
                data_file = get_data_dir() / 'readings.csv'
                recent_data.to_csv(data_file, index=False)
                archived_items += 1
        
        if archived_items == 0:
            return {
                'success': True,
                'archived_items': 0,
                'message': 'No items needed archiving',
                'archive_path': None
            }
        
        return {
            'success': True,
            'archived_items': archived_items,
            'message': f'Archived {archived_items} item(s)',
            'archive_path': archive_dir
        }
        
    except Exception as e:
        logging.error(f"Archive failed: {e}")
        return {
            'success': False,
            'archived_items': 0,
            'message': f'Error: {e}',
            'archive_path': None
        }


def get_statistics(include_archives=False):
    """
    Get statistical summary of collected data.
    
    Args:
        include_archives: Include archived data in stats
        
    Returns:
        dict or None: Statistics dictionary or None if no data
    """
    df = load_data(include_archives=include_archives)
    
    if df is None or df.empty:
        return None
    
    stats = {
        'total_readings': len(df),
        'first_reading': df['timestamp'].min(),
        'last_reading': df['timestamp'].max(),
        'duration_days': (df['timestamp'].max() - df['timestamp'].min()).days,
        'pressure': {
            'current': float(df['pressure_hpa'].iloc[-1]),
            'average': float(df['pressure_hpa'].mean()),
            'minimum': float(df['pressure_hpa'].min()),
            'maximum': float(df['pressure_hpa'].max()),
            'range': float(df['pressure_hpa'].max() - df['pressure_hpa'].min()),
            'std_dev': float(df['pressure_hpa'].std()),
        }
    }
    
    # Last 24 hours
    last_24h = df[df['timestamp'] > (datetime.now() - timedelta(hours=24))]
    if not last_24h.empty:
        stats['last_24h'] = {
            'readings': len(last_24h),
            'average': float(last_24h['pressure_hpa'].mean()),
            'change': float(last_24h['pressure_hpa'].iloc[-1] - last_24h['pressure_hpa'].iloc[0]),
        }
    
    return stats


def get_latest_reading():
    """
    Get the most recent pressure reading.
    
    Returns:
        dict or None: {'pressure': float, 'timestamp': datetime} or None
    """
    df = load_data()
    
    if df is None or df.empty:
        return None
    
    row = df.iloc[-1]
    return {
        'pressure': float(row['pressure_hpa']),  
        'timestamp': row['timestamp'],
    }

def scrape_single_reading():
    """
    Perform a single scrape and save reading.
    
    Returns:
        dict: {
            'success': bool,
            'pressure': float or None,
            'message': str
        }
    """
    from barometer_logger import BarometerScraper
    
    try:
        scraper = BarometerScraper()
        response = scraper.login()
        
        if not response:
            return {
                'success': False,
                'pressure': None,
                'message': 'Connection failed'
            }
        
        pressure = scraper.extract_barometer_value(response.text)
        
        if not pressure:
            return {
                'success': False,
                'pressure': None,
                'message': 'Failed to extract pressure value'
            }
        
        scraper.save_reading(pressure)
        
        return {
            'success': True,
            'pressure': pressure / 100,  # Convert to hPa
            'message': f'Reading saved: {pressure / 100:.2f} hPa'
        }
        
    except Exception as e:
        logging.error(f"Scrape failed: {e}")
        return {
            'success': False,
            'pressure': None,
            'message': f'Error: {e}'
        }