from pathlib import Path

# save everything to /spectrum-barometer
def get_app_dir():
    """Get the application directory, create if needed"""
    app_dir = Path.home() / 'spectrum-barometer'
    app_dir.mkdir(exist_ok=True)
    return app_dir

def get_config_file():
    return get_app_dir() / 'config.yaml'


def get_data_dir():
    data_dir = get_app_dir() / 'data'
    data_dir.mkdir(exist_ok=True)
    return data_dir

def get_logs_dir():
    logs_dir = get_app_dir() / 'logs'
    logs_dir.mkdir(exist_ok=True)
    return logs_dir

def get_graphs_dir():
    graphs_dir = get_app_dir() / 'graphs'
    graphs_dir.mkdir(exist_ok=True)
    return graphs_dir

def get_archive_dir():
    archive_dir = get_app_dir() / 'archive'
    archive_dir.mkdir(exist_ok=True)
    return archive_dir