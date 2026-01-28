"""Background monitoring using threading with file-based state"""
import threading
import time
import logging
from barometer.paths import get_app_dir
from datetime import datetime
from pathlib import Path

def get_state_file():
    """Get path to state file"""
    return get_app_dir() / 'monitor.state'

def get_interval_file():
    """Get path to interval file"""
    return get_app_dir() / 'monitor.interval'

def is_monitoring():
    """Check if monitoring thread is running (in THIS process)"""
    state_file = get_state_file()
    if not state_file.exists():
        return False
    
    try:
        state = state_file.read_text().strip()
        return state == 'running'
    except:
        return False

def get_monitor_info():
    """Get monitoring status"""
    interval_file = get_interval_file()
    interval = 300
    
    if interval_file.exists():
        try:
            interval = int(interval_file.read_text().strip())
        except ValueError:
            pass
    
    running = is_monitoring()
    
    return {
        'running': running,
        'pid': None,
        'interval': interval if running else None,
    }

# Thread management (only exists in the process that started it)
_monitor_thread = None

def _monitor_loop(interval):
    """Internal monitoring loop"""
    from barometer.actions import scrape_single_reading
    
    state_file = get_state_file()
    
    while state_file.exists() and state_file.read_text().strip() == 'running':
        try:
            result = scrape_single_reading()
            if result['success']:
                logging.info(f"Background scrape: {result['pressure']:.2f} hPa")
            else:
                logging.error(f"Background scrape failed: {result['message']}")
        except Exception as e:
            logging.error(f"Monitor error: {e}")
        
        # Sleep in small chunks so we can stop quickly
        for _ in range(interval):
            if not state_file.exists() or state_file.read_text().strip() != 'running':
                break
            time.sleep(1)
    
    # Clean up when loop exits
    state_file.unlink(missing_ok=True)
    logging.info("Background monitoring stopped")

def start_monitoring(interval=300):
    """Start monitoring in background thread"""
    global _monitor_thread
    
    state_file = get_state_file()
    interval_file = get_interval_file()
    
    if state_file.exists() and state_file.read_text().strip() == 'running':
        return {
            'success': False,
            'message': 'Monitoring is already running',
            'pid': None
        }
    
    try:
        # Write state files
        state_file.write_text('running')
        interval_file.write_text(str(interval))
        
        # Start thread
        _monitor_thread = threading.Thread(
            target=_monitor_loop, 
            args=(interval,), 
            daemon=True,
            name="BarometerMonitor"
        )
        _monitor_thread.start()
        
        return {
            'success': True,
            'message': f'Monitoring started (interval: {interval}s)',
            'pid': None
        }
    except Exception as e:
        state_file.unlink(missing_ok=True)
        return {
            'success': False,
            'message': f'Failed to start: {e}',
            'pid': None
        }

def stop_monitoring():
    """Stop monitoring thread"""
    state_file = get_state_file()
    interval_file = get_interval_file()
    
    if not state_file.exists():
        return {
            'success': False,
            'message': 'Monitoring is not running'
        }
    
    # Signal thread to stop
    state_file.unlink(missing_ok=True)
    interval_file.unlink(missing_ok=True)
    
    return {
        'success': True,
        'message': 'Monitoring stopped'
    }