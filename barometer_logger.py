import logging
import pandas 
import requests
import urllib3
import yaml
import time
import re
import click
from io import StringIO
from datetime import datetime, timedelta
import os
import shutil
import matplotlib
matplotlib.use('Agg')  # headless backend for background operation
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import numpy as np
from pathlib import Path
# disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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


class BarometerScraper:
    def __init__(self, config_file=None):
        # load config file
        if config_file is None:
            config_file = get_config_file()
        
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
        
        # set values from config
        self.url = config['url']
        self.username = config['username']
        self.password = config['password']
        self.session = requests.Session()
        self.session.verify = False
    
    def login(self):
        #connect to router
        try: 
            response = self.session.get(
                self.url, 
                auth=(self.username, self.password), 
                timeout=10
            )
            
            if response.status_code == 200:
                return response
            elif response.status_code == 401:
                logging.error("Authentication failed, check username/password")
                return None
            else:
                logging.error(f"Failed to access page. Status code: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Connection error: {e}")
            return None
    
    def extract_barometer_value(self, html_content):
        # extract the barometer pressure value using pandas
        try:
            tables = pandas.read_html(StringIO(html_content))
            
            if not tables:
                logging.error("No tables found")
                return None
            
            df = tables[0]
            barometer_row = df[df['Field'] == 'Barometer Value']
            
            if barometer_row.empty:
                logging.error("Could not find 'Barometer Value' in table")
                return None
            
            setting_value = barometer_row['Setting'].values[0]
            match = re.search(r'(\d+)', setting_value)
            
            if match:
                pressure = int(match.group(1))
                return pressure
            else:
                logging.error(f"Could not parse pressure from: {setting_value}")
                return None
            
        except Exception as e:
            logging.error(f"Error parsing HTML: {e}")
            return None
    
    def save_reading(self, pressure):
        # save pressure reading to CSV file
        data_file = get_data_dir() / 'readings.csv'
        
        data = {
            'timestamp': [datetime.now().isoformat()],
            'pressure_pa': [pressure],
            'pressure_hpa': [pressure / 100]
        }
        
        df = pandas.DataFrame(data)
        file_exists = data_file.exists()
        df.to_csv(data_file, mode='a', header=not file_exists, index=False)
        
        return True


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

    #Load readings from CSV, optionally including archives

def load_data(include_archives=False):
    data_file = get_data_dir() / 'readings.csv'
    
    if not data_file.exists():
        return None
    
    dfs = []
    df = pandas.read_csv(data_file)
    df['timestamp'] = pandas.to_datetime(df['timestamp'])
    dfs.append(df)
    
    if include_archives:
        archive_dir = get_archive_dir()
        if archive_dir.exists():
            for csv_file in archive_dir.rglob('*.csv'):
                df_archive = pandas.read_csv(csv_file)
                df_archive['timestamp'] = pandas.to_datetime(df_archive['timestamp'])
                dfs.append(df_archive)
    
    if not dfs:
        return None
    
    combined = pandas.concat(dfs, ignore_index=True)
    combined = combined.sort_values('timestamp').reset_index(drop=True)
    combined = combined.drop_duplicates(subset=['timestamp'], keep='last')
    
    return combined


def generate_line_graph(df, output, days):
    """Standard line graph"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    ax.plot(df['timestamp'], df['pressure_hpa'], 
            linewidth=2, color='#2E86AB', label='Barometric Pressure')
    
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Pressure (hPa)', fontsize=12)
    ax.set_title(f'Barometric Pressure - Last {days} Days', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output, dpi=150, bbox_inches='tight')
    plt.close()


def generate_smooth_graph(df, output, days, window=12):
    """Line graph with rolling average"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Original data
    ax.plot(df['timestamp'], df['pressure_hpa'], 
            linewidth=1, color='#2E86AB', alpha=0.4, label='Raw Data')
    
    # Rolling average
    df['rolling_avg'] = df['pressure_hpa'].rolling(window=window, center=True).mean()
    ax.plot(df['timestamp'], df['rolling_avg'], 
            linewidth=2.5, color='#A23B72', label=f'{window}-point Moving Average')
    
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Pressure (hPa)', fontsize=12)
    ax.set_title(f'Barometric Pressure with Trend - Last {days} Days', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output, dpi=150, bbox_inches='tight')
    plt.close()


def generate_area_graph(df, output, days):
    """Filled area chart"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    ax.fill_between(df['timestamp'], df['pressure_hpa'], 
                     alpha=0.4, color='#2E86AB', label='Pressure')
    ax.plot(df['timestamp'], df['pressure_hpa'], 
            linewidth=2, color='#1A5F7A', label='Trend Line')
    
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Pressure (hPa)', fontsize=12)
    ax.set_title(f'Barometric Pressure Area - Last {days} Days', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output, dpi=150, bbox_inches='tight')
    plt.close()


def generate_daily_summary(df, output, days):
    """Daily min/max/avg bars"""
    # Group by date
    df['date'] = df['timestamp'].dt.date
    daily = df.groupby('date').agg({
        'pressure_hpa': ['min', 'max', 'mean']
    }).reset_index()
    daily.columns = ['date', 'min', 'max', 'mean']
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    x = range(len(daily))
    
    # Draw bars for range
    for i, row in daily.iterrows():
        ax.plot([i, i], [row['min'], row['max']], 
                color='#2E86AB', linewidth=8, alpha=0.3)
        ax.scatter(i, row['mean'], color='#A23B72', s=50, zorder=3)
    
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Pressure (hPa)', fontsize=12)
    ax.set_title(f'Daily Pressure Summary - Last {days} Days', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([d.strftime('%m/%d') for d in daily['date']], rotation=45)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color='#2E86AB', linewidth=8, alpha=0.3, label='Min-Max Range'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#A23B72', 
               markersize=8, label='Daily Average')
    ]
    ax.legend(handles=legend_elements)
    
    plt.tight_layout()
    plt.savefig(output, dpi=150, bbox_inches='tight')
    plt.close()


def generate_distribution(df, output, days):
    """Histogram of pressure values"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    ax.hist(df['pressure_hpa'], bins=30, color='#2E86AB', alpha=0.7, edgecolor='black')
    
    # Add mean and median lines
    mean_val = df['pressure_hpa'].mean()
    median_val = df['pressure_hpa'].median()
    
    ax.axvline(mean_val, color='#A23B72', linestyle='--', linewidth=2, label=f'Mean: {mean_val:.2f} hPa')
    ax.axvline(median_val, color='#F18F01', linestyle='--', linewidth=2, label=f'Median: {median_val:.2f} hPa')
    
    ax.set_xlabel('Pressure (hPa)', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title(f'Pressure Distribution - Last {days} Days', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(output, dpi=150, bbox_inches='tight')
    plt.close()


def generate_rate_of_change(df, output, days):
    """Pressure change over time"""
    # Calculate hourly change
    df = df.sort_values('timestamp')
    df['change'] = df['pressure_hpa'].diff()
    df['hours_diff'] = df['timestamp'].diff().dt.total_seconds() / 3600
    df['hourly_change'] = df['change'] / df['hours_diff']
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    colors = ['#EF476F' if x < 0 else '#06D6A0' for x in df['hourly_change']]
    ax.bar(df['timestamp'], df['hourly_change'], color=colors, alpha=0.6, width=0.01)
    
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Pressure Change (hPa/hour)', fontsize=12)
    ax.set_title(f'Rate of Pressure Change - Last {days} Days', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    plt.xticks(rotation=45)
    
    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#06D6A0', alpha=0.6, label='Rising'),
        Patch(facecolor='#EF476F', alpha=0.6, label='Falling')
    ]
    ax.legend(handles=legend_elements)
    
    plt.tight_layout()
    plt.savefig(output, dpi=150, bbox_inches='tight')
    plt.close()


def generate_dashboard(df, output, days):
    """Multi-panel dashboard view"""
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)
    
    # 1. Main time series (top, full width)
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(df['timestamp'], df['pressure_hpa'], linewidth=2, color='#2E86AB')
    ax1.set_title('Pressure Over Time', fontweight='bold')
    ax1.set_ylabel('Pressure (hPa)')
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    
    # 2. Distribution
    ax2 = fig.add_subplot(gs[1, 0])
    ax2.hist(df['pressure_hpa'], bins=20, color='#2E86AB', alpha=0.7, edgecolor='black')
    ax2.set_title('Distribution', fontweight='bold')
    ax2.set_xlabel('Pressure (hPa)')
    ax2.set_ylabel('Frequency')
    ax2.grid(True, alpha=0.3, axis='y')
    
    # 3. Rate of change
    ax3 = fig.add_subplot(gs[1, 1])
    df_sorted = df.sort_values('timestamp')
    df_sorted['change'] = df_sorted['pressure_hpa'].diff()
    colors = ['#EF476F' if x < 0 else '#06D6A0' for x in df_sorted['change']]
    ax3.bar(range(len(df_sorted)), df_sorted['change'], color=colors, alpha=0.6)
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax3.set_title('Reading-to-Reading Change', fontweight='bold')
    ax3.set_ylabel('Change (hPa)')
    ax3.grid(True, alpha=0.3, axis='y')
    
    # 4. Statistics box
    ax4 = fig.add_subplot(gs[2, 0])
    ax4.axis('off')
    stats_text = f"""
    STATISTICS
    ──────────────────
    Current:    {df['pressure_hpa'].iloc[-1]:.2f} hPa
    Average:    {df['pressure_hpa'].mean():.2f} hPa
    Minimum:    {df['pressure_hpa'].min():.2f} hPa
    Maximum:    {df['pressure_hpa'].max():.2f} hPa
    Range:      {df['pressure_hpa'].max() - df['pressure_hpa'].min():.2f} hPa
    Std Dev:    {df['pressure_hpa'].std():.2f} hPa
    """
    ax4.text(0.1, 0.5, stats_text, fontsize=11, verticalalignment='center', 
             fontfamily='monospace', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
    
    # 5. Trend indicator
    ax5 = fig.add_subplot(gs[2, 1])
    ax5.axis('off')
    
    # Calculate 24h trend
    if len(df) > 1:
        recent_avg = df.tail(min(12, len(df)))['pressure_hpa'].mean()
        older_avg = df.head(min(12, len(df)))['pressure_hpa'].mean()
        trend = recent_avg - older_avg
        
        trend_text = "RISING ↗" if trend > 0.5 else "FALLING ↘" if trend < -0.5 else "STABLE →"
        trend_color = '#06D6A0' if trend > 0.5 else '#EF476F' if trend < -0.5 else '#FFD166'
        
        ax5.text(0.5, 0.6, 'TREND', fontsize=14, ha='center', fontweight='bold')
        ax5.text(0.5, 0.4, trend_text, fontsize=24, ha='center', 
                color=trend_color, fontweight='bold')
        ax5.text(0.5, 0.2, f'{trend:+.2f} hPa', fontsize=12, ha='center')
    
    fig.suptitle(f'Barometer Dashboard - Last {days} Days', fontsize=16, fontweight='bold')
    plt.savefig(output, dpi=150, bbox_inches='tight')
    plt.close()



def generate_graph(days=7, output=None, graph_type='line', include_archives=False):
    """Generate pressure graph from stored data"""
    if output is None:
        output = get_graphs_dir() / 'pressure.png'
    else:
        output = Path(output)
    
    df = load_data(include_archives=include_archives)
    
    if df is None or df.empty:
        click.echo("No data available to graph")
        return False
    
    cutoff = datetime.now() - timedelta(days=days)
    df_filtered = df[df['timestamp'] > cutoff].copy()
    
    if df_filtered.empty:
        click.echo(f"No data available for the last {days} days")
        return False
    
    output.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        if graph_type == 'line':
            generate_line_graph(df_filtered, str(output), days)
        elif graph_type == 'smooth':
            generate_smooth_graph(df_filtered, str(output), days)
        elif graph_type == 'area':
            generate_area_graph(df_filtered, str(output), days)
        elif graph_type == 'daily':
            generate_daily_summary(df_filtered, str(output), days)
        elif graph_type == 'distribution':
            generate_distribution(df_filtered, str(output), days)
        elif graph_type == 'change':
            generate_rate_of_change(df_filtered, str(output), days)
        elif graph_type == 'dashboard':
            generate_dashboard(df_filtered, str(output), days)
        elif graph_type == 'all':
            base_name = output.stem
            ext = output.suffix or '.png'
            
            generate_line_graph(df_filtered, str(output.parent / f'{base_name}_line{ext}'), days)
            generate_smooth_graph(df_filtered, str(output.parent / f'{base_name}_smooth{ext}'), days)
            generate_area_graph(df_filtered, str(output.parent / f'{base_name}_area{ext}'), days)
            generate_daily_summary(df_filtered, str(output.parent / f'{base_name}_daily{ext}'), days)
            generate_distribution(df_filtered, str(output.parent / f'{base_name}_distribution{ext}'), days)
            generate_rate_of_change(df_filtered, str(output.parent / f'{base_name}_change{ext}'), days)
            generate_dashboard(df_filtered, str(output.parent / f'{base_name}_dashboard{ext}'), days)
            
            click.echo(f"Generated 7 graphs in {output.parent}")
            return True
        else:
            click.echo(f"Unknown graph type: {graph_type}")
            return False
        
        click.echo(f"Graph saved to {output}")
        return True
        
    except Exception as e:
        click.echo(f"Error generating graph: {e}")
        logging.error(f"Graph generation failed: {e}")
        return False






# CLI Commands

@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, verbose):
    """A CLI tool to make use of the barometer in locked down spectrum routers"""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    setup_logging(verbose)

@cli.command()
def version():
    """Show version information"""
    click.echo("spectrum-barometer version 1.0.2")


@cli.command()
@click.option('--show', is_flag=True, help='Show current configuration')
@click.pass_context
def config(ctx, show):
    """Manage configuration file"""
    config_file = get_config_file()
    
    if show:
        if config_file.exists():
            with open(config_file, 'r') as f:
                cfg = yaml.safe_load(f)
            click.echo("\nCurrent Configuration:")
            click.echo("="*50)
            click.echo(f"URL: {cfg.get('url', 'Not set')}")
            click.echo(f"Username: {cfg.get('username', 'Not set')}")
            click.echo(f"Password: {'*' * len(cfg.get('password', '')) if cfg.get('password') else 'Not set'}")
            click.echo(f"\nConfig location: {config_file}")
        else:
            click.echo(f"No config file found at: {config_file}")
            click.echo("Run 'barometer config' to create one")
        return
    
    click.echo("Configuration Setup")
    click.echo("="*50)
    
    if config_file.exists():
        click.echo(f"\nConfig file already exists at: {config_file}")
        if not click.confirm("Overwrite existing configuration?"):
            click.echo("Configuration unchanged")
            return
    
    url = click.prompt("Router URL", default="https://192.168.1.1/cgi-bin/warehouse.cgi")
    username = click.prompt("Username", default="ThylacineGone")
    password = click.prompt("Password", default="4p@ssThats10ng")
    
    config_data = {
        'url': url,
        'username': username,
        'password': password
    }
    
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f, default_flow_style=False)
    
    click.echo(f"\nConfiguration saved to: {config_file}")
    click.echo("You can now run: barometer test")


@cli.command()
@click.pass_context
def info(ctx):
    """Show information about data locations and project setup"""
    click.echo("\nBarometer Project Information")
    click.echo("="*50)
    
    app_dir = get_app_dir()
    click.echo(f"App directory: {app_dir}")
    
    config_file = get_config_file()
    if config_file.exists():
        click.echo(f"\nConfig file: {config_file}")
    else:
        click.echo(f"\nConfig file: NOT FOUND")
        click.echo(f"  Run 'barometer config' to create at: {config_file}")
    
    data_file = get_data_dir() / 'readings.csv'
    if data_file.exists():
        size = data_file.stat().st_size / 1024
        click.echo(f"\nData file: {data_file} ({size:.1f} KB)")
        df = load_data()
        if df is not None and not df.empty:
            click.echo(f"  - {len(df)} readings")
            click.echo(f"  - From {df['timestamp'].min()} to {df['timestamp'].max()}")
    else:
        click.echo(f"\nData file: NOT FOUND")
        click.echo(f"  Run 'barometer scrape' to start collecting")
    
    graphs_dir = get_graphs_dir()
    graphs = list(graphs_dir.glob('*.png'))
    click.echo(f"\nGraphs directory: {graphs_dir}")
    if graphs:
        click.echo(f"  - {len(graphs)} graph(s)")
        for g in graphs:
            click.echo(f"    - {g.name}")
    else:
        click.echo(f"  - No graphs yet (run 'barometer graph' to create)")
    
    log_file = get_logs_dir() / 'barometer.log'
    if log_file.exists():
        size = log_file.stat().st_size / 1024
        click.echo(f"\nLog file: {log_file} ({size:.1f} KB)")
    else:
        click.echo(f"\nLog file: {get_logs_dir() / 'barometer.log'}")
        click.echo(f"  - Will be created on first run")
    
    archive_dir = get_archive_dir()
    if archive_dir.exists():
        archive_files = list(archive_dir.rglob('*.csv'))
        if archive_files:
            click.echo(f"\nArchives: {archive_dir}")
            click.echo(f"  - {len(archive_files)} archive file(s)")






@cli.command()
@click.pass_context
def test(ctx):
    """Test connection to router and data extraction"""
    click.echo("Testing connection to router...")
    
    try:
        scraper = BarometerScraper()
        click.echo("Config loaded")
        
        response = scraper.login()
        if response:
            click.echo("Connection successful")
            
            pressure = scraper.extract_barometer_value(response.text)
            if pressure:
                click.echo(f"Data extraction successful")
                click.echo(f"\nCurrent pressure: {pressure} Pa ({pressure/100:.2f} hPa)")
                click.echo("\n All tests passed!")
                return
        
        click.echo("Test failed, check logs for details")
        
    except Exception as e:
        click.echo(f" Error: {e}")
        logging.error(f"Test failed: {e}")


@cli.command()
@click.option('--interval', '-i', default=300, help='Interval between readings in seconds (default: 300)')
@click.pass_context
def monitor(ctx, interval):
    """start continuous monitoring (default mode)"""
    click.echo(f"Starting continuous monitoring (interval: {interval}s)")
    click.echo("Press Ctrl+C to stop\n")
    
    scraper = BarometerScraper()
    readings_count = 0
    
    while True:
        try:
            response = scraper.login()
            
            if response:
                pressure = scraper.extract_barometer_value(response.text)
                
                if pressure:
                    scraper.save_reading(pressure)
                    readings_count += 1
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    click.echo(f"[{timestamp}] Pressure: {pressure/100:.2f} hPa | Total readings: {readings_count}")
                else:
                    click.echo(" Failed to extract pressure value")
            else:
                click.echo(" Connection failed")
                
        except KeyboardInterrupt:
            click.echo(f"\n\nStopping monitoring... (collected {readings_count} readings)")
            break
        except Exception as e:
            click.echo(f" Error: {e}")
            logging.error(f"Monitor error: {e}")
        
        time.sleep(interval)


@cli.command()
@click.pass_context
def scrape(ctx):
    """perform a single scrape and save reading"""
    click.echo("Performing single scrape...")
    
    try:
        scraper = BarometerScraper()
        response = scraper.login()
        
        if response:
            pressure = scraper.extract_barometer_value(response.text)
            
            if pressure:
                scraper.save_reading(pressure)
                click.echo(f" Reading saved: {pressure} Pa ({pressure/100:.2f} hPa)")
            else:
                click.echo(" Failed to extract pressure value")
        else:
            click.echo(" Connection failed")
            
    except Exception as e:
        click.echo(f" Error: {e}")


@cli.command()
@click.option('--days', '-d', default=7, show_default=True, help='Number of days to display')
@click.option('--output', '-o', default='none', show_default=True, help='Output file path')
@click.option('--type', '-t', 'graph_type', 
              type=click.Choice(['line', 'smooth', 'area', 'daily', 'distribution', 'change', 'dashboard', 'all'], 
                               case_sensitive=False),
              default='dashboard', show_default=True,
              help='Type of graph to generate')
@click.option('--archives', '-a', is_flag=True, help='Include archived data in graph')
@click.pass_context
def graph(ctx, days, output, graph_type, archives):
    """\b
    Generate pressure graph from stored data
    \b
    Graph types:
     
      line         - Standard line graph (default)
      
      smooth       - Line with moving average trend
      
      area         - Filled area chart
      
      daily        - Daily min/max/average summary
      
      distribution - Histogram of pressure values
      
      change       - Rate of pressure change over time
      
      dashboard    - Multi-panel overview
      
      all          - Generate all graph types
    """
    
    if archives:
        click.echo(f"Generating {graph_type} graph for last {days} days (including archives)...")
    else:
        click.echo(f"Generating {graph_type} graph for last {days} days...")
    
    if generate_graph(days, output, graph_type, include_archives=archives):
        # Show absolute path
        abs_path = os.path.abspath(output)
        click.echo(f"Graph generated successfully")
        click.echo(f"Location: {abs_path}")
    else:
        click.echo("Failed to generate graph")
        
@cli.command()
@click.option('--keep-days', '-k', default=90, show_default=True, help='Keep data from last N days')
@click.confirmation_option(prompt='This will move old logs and data to archive. Continue?')
@click.pass_context
def archive(ctx, keep_days):
    """Archive old logs and data"""
    click.echo(f"Archiving data older than {keep_days} days...")
    
    archive_dir = get_archive_dir() / datetime.now().strftime('%Y-%m')
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    archived_items = 0
    
    log_file = get_logs_dir() / 'barometer.log'
    if log_file.exists():
        log_size = log_file.stat().st_size / 1024 / 1024
        if log_size > 10:
            shutil.copy(log_file, archive_dir / 'barometer.log')
            log_file.write_text('')
            click.echo(f"Archived log file ({log_size:.1f} MB)")
            archived_items += 1
    
    df = load_data()
    if df is not None and not df.empty:
        cutoff = datetime.now() - timedelta(days=keep_days)
        old_data = df[df['timestamp'] < cutoff]
        recent_data = df[df['timestamp'] >= cutoff]
        
        if not old_data.empty:
            old_data.to_csv(archive_dir / 'readings_archive.csv', index=False)
            data_file = get_data_dir() / 'readings.csv'
            recent_data.to_csv(data_file, index=False)
            click.echo(f"Archived {len(old_data)} old readings")
            archived_items += 1
    
    if archived_items == 0:
        click.echo("No items needed archiving")
    else:
        click.echo(f"\nArchived {archived_items} item(s) to {archive_dir}")


@cli.command()
@click.pass_context
def stats(ctx):
    """Show statistics about collected data"""
    df = load_data(include_archives=False)
    
    if df is None or df.empty:
        click.echo("No data available")
        return
    
    click.echo("\nStatistics\n" + "="*50)
    click.echo(f"Total readings: {len(df)}")
    click.echo(f"First reading: {df['timestamp'].min()}")
    click.echo(f"Last reading: {df['timestamp'].max()}")
    click.echo(f"Duration: {(df['timestamp'].max() - df['timestamp'].min()).days} days")
    
    click.echo(f"\nPressure Statistics (hPa)\n" + "="*50)
    click.echo(f"Current: {df['pressure_hpa'].iloc[-1]:.2f}")
    click.echo(f"Average: {df['pressure_hpa'].mean():.2f}")
    click.echo(f"Minimum: {df['pressure_hpa'].min():.2f}")
    click.echo(f"Maximum: {df['pressure_hpa'].max():.2f}")
    click.echo(f"Range: {df['pressure_hpa'].max() - df['pressure_hpa'].min():.2f}")
    
    # Last 24 hours
    last_24h = df[df['timestamp'] > (datetime.now() - timedelta(hours=24))]
    if not last_24h.empty:
        click.echo(f"\nLast 24 Hours\n" + "="*50)
        click.echo(f"Readings: {len(last_24h)}")
        click.echo(f"Average: {last_24h['pressure_hpa'].mean():.2f} hPa")
        change = last_24h['pressure_hpa'].iloc[-1] - last_24h['pressure_hpa'].iloc[0]
        click.echo(f"Change: {change:+.2f} hPa")
    
    # Check for archives
    if os.path.exists('archive'):
        archive_count = 0
        for root, dirs, files in os.walk('archive'):
            archive_count += len([f for f in files if f.endswith('.csv')])
        if archive_count > 0:
            click.echo(f"\nArchives: {archive_count} file(s) available (use --archives flag to include)")


if __name__ == "__main__":
    cli(obj={})
