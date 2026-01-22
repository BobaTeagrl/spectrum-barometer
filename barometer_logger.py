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

# disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class BarometerScraper:
    def __init__(self, config_file='config.yaml'):
        # load config file
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
        os.makedirs('data', exist_ok=True)
        
        data = {
            'timestamp': [datetime.now().isoformat()],
            'pressure_pa': [pressure],
            'pressure_hpa': [pressure / 100]
        }
        
        df = pandas.DataFrame(data)
        file_exists = os.path.isfile('data/readings.csv')
        df.to_csv('data/readings.csv', mode='a', header=not file_exists, index=False)
        
        return True


def setup_logging(verbose=False):
    # configure logging
    level = logging.DEBUG if verbose else logging.INFO
    
    os.makedirs('logs', exist_ok=True)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/barometer.log'),
            logging.StreamHandler()
        ]
    )


def load_data():
    # load readings from CSV
    if not os.path.exists('data/readings.csv'):
        return None
    
    df = pandas.read_csv('data/readings.csv')
    df['timestamp'] = pandas.to_datetime(df['timestamp'])
    return df


def generate_graph(days=7, output='graphs/pressure.png'):
    # generate pressure graph from data
    df = load_data()
    
    if df is None or df.empty:
        click.echo("No data available to graph")
        return False
    
    # filter to last N days
    cutoff = datetime.now() - timedelta(days=days)
    df_filtered = df[df['timestamp'] > cutoff]
    
    if df_filtered.empty:
        click.echo(f"No data available for the last {days} days")
        return False
    
    # create output directory
    os.makedirs('graphs', exist_ok=True)
    
    # create figure
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # plot
    ax.plot(df_filtered['timestamp'], df_filtered['pressure_hpa'], 
            linewidth=2, color='#2E86AB', label='Barometric Pressure')
    
    # formatting
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Pressure (hPa)', fontsize=12)
    ax.set_title(f'Barometric Pressure - Last {days} Days', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # format x-axis dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    plt.xticks(rotation=45)
    
    # tight layout
    plt.tight_layout()
    
    # save
    plt.savefig(output, dpi=150, bbox_inches='tight')
    plt.close()
    
    click.echo(f"Graph saved to {output}")
    return True


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
                click.echo(f"✓ Data extraction successful")
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
@click.option('--days', '-d', default=7, show_default= True, help='Number of days to display (default: 7)')
@click.option('--output', '-o', default='graphs/pressure.png', show_default= True, help='Output file path')
@click.pass_context
def graph(ctx, days, output):
    """Generate pressure graph from stored data"""
    click.echo(f"Generating graph for last {days} days...")
    
    if generate_graph(days, output):
        click.echo(" Graph generated successfully")
    else:
        click.echo(" Failed to generate graph")


@cli.command()
@click.option('--keep-days', '-k', default=90, help='Keep data from last N days (default: 90)')
@click.confirmation_option(prompt='This will move old logs and data to archive. Continue?')
@click.pass_context
def archive(ctx, keep_days):
    """Archive old logs and data"""
    click.echo(f"Archiving data older than {keep_days} days...")
    
    # Create archive directory
    archive_dir = f"archive/{datetime.now().strftime('%Y-%m')}"
    os.makedirs(archive_dir, exist_ok=True)
    
    archived_items = 0
    
    # Archive logs
    if os.path.exists('logs/barometer.log'):
        log_size = os.path.getsize('logs/barometer.log') / 1024 / 1024  # MB
        if log_size > 10:  # Archive if > 10MB
            shutil.copy('logs/barometer.log', f'{archive_dir}/barometer.log')
            # Clear the log file
            open('logs/barometer.log', 'w').close()
            click.echo(f"✓ Archived log file ({log_size:.1f} MB)")
            archived_items += 1
    
    # Archive old CSV data
    df = load_data()
    if df is not None and not df.empty:
        cutoff = datetime.now() - timedelta(days=keep_days)
        old_data = df[df['timestamp'] < cutoff]
        recent_data = df[df['timestamp'] >= cutoff]
        
        if not old_data.empty:
            # Save old data to archive
            old_data.to_csv(f'{archive_dir}/readings_archive.csv', index=False)
            # Keep only recent data in main file
            recent_data.to_csv('data/readings.csv', index=False)
            click.echo(f" Archived {len(old_data)} old readings")
            archived_items += 1
    
    if archived_items == 0:
        click.echo("No items needed archiving")
    else:
        click.echo(f"\n Archived {archived_items} item(s) to {archive_dir}")


@cli.command()
@click.pass_context
def stats(ctx):
    """Show statistics about collected data"""
    df = load_data()
    
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


if __name__ == "__main__":
    cli(obj={})
