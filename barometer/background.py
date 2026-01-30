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

def get_pid_file():
    """Get path to PID file"""
    return get_app_dir() / 'monitor.pid'

def is_monitoring():
    """Check if monitoring thread is running (in THIS process)"""
    import os
    import psutil
    
    state_file = get_state_file()
    pid_file = get_pid_file()
    
    if not state_file.exists() or not pid_file.exists():
        return False
    
    try:
        state = state_file.read_text().strip()
        pid = int(pid_file.read_text().strip())
        
        # Check if state says running AND process exists
        if state != 'running':
            return False
            
        # Check if the PID is still alive
        if psutil.pid_exists(pid):
            return True
        else:
            # Stale state files - clean them up
            state_file.unlink(missing_ok=True)
            pid_file.unlink(missing_ok=True)
            get_interval_file().unlink(missing_ok=True)
            return False
    except:
        return False

def get_monitor_info():
    """Get monitoring status"""
    import os
    
    interval_file = get_interval_file()
    pid_file = get_pid_file()
    interval = 300
    pid = None
    
    if interval_file.exists():
        try:
            interval = int(interval_file.read_text().strip())
        except ValueError:
            pass
    
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
        except ValueError:
            pass
    
    running = is_monitoring()
    
    return {
        'running': running,
        'pid': pid if running else None,
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
    import os
    
    state_file = get_state_file()
    interval_file = get_interval_file()
    pid_file = get_pid_file()
    
    # Check if already running (cleans up stale files automatically)
    if is_monitoring():
        pid = int(pid_file.read_text().strip()) if pid_file.exists() else None
        return {
            'success': False,
            'message': 'Monitoring is already running',
            'pid': pid
        }
    
    try:
        # Write state files including PID
        state_file.write_text('running')
        interval_file.write_text(str(interval))
        pid_file.write_text(str(os.getpid()))
        
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
            'pid': os.getpid()
        }
    except Exception as e:
        state_file.unlink(missing_ok=True)
        pid_file.unlink(missing_ok=True)
        return {
            'success': False,
            'message': f'Failed to start: {e}',
            'pid': None
        }

def stop_monitoring():
    """Stop monitoring thread"""
    state_file = get_state_file()
    interval_file = get_interval_file()
    pid_file = get_pid_file()
    
    if not state_file.exists():
        return {
            'success': False,
            'message': 'Monitoring is not running'
        }
    
    # Signal thread to stop and clean up all state files
    state_file.unlink(missing_ok=True)
    interval_file.unlink(missing_ok=True)
    pid_file.unlink(missing_ok=True)
    
    return {
        'success': True,
        'message': 'Monitoring stopped'
    }