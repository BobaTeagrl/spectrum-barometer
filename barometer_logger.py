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
from barometer.paths import get_config_file, get_app_dir, get_data_dir, get_archive_dir, get_graphs_dir, get_logs_dir
from barometer.graphs import  generate_area_graph, generate_daily_summary, generate_dashboard, generate_distribution, generate_graph, generate_line_graph, generate_rate_of_change, generate_smooth_graph
from barometer.data import load_data, setup_logging
from barometer.actions import  archive_old_data, get_latest_reading, get_statistics, scrape_single_reading
# disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


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
    click.echo("spectrum-barometer version 2.1.1! (that was fast :3)")


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
@click.pass_context
def scrape(ctx):
    """perform a single scrape and save reading"""
    
    click.echo("Performing single scrape...")
    
    result = scrape_single_reading()
    
    if result['success']:
        click.echo(result['message'])
    else:
        click.echo(f"Failed: {result['message']}")

@cli.command()
@click.option('--days', '-d', default=7, show_default=True, help='Number of days to display')
@click.option('--output', '-o',  show_default=True, help='Output file path')
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
    
    result = generate_graph(days, output, graph_type, include_archives=archives)

    if result:
        abs_path = os.path.abspath(result)
        click.echo("Graph generated successfully")
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
    
    result = archive_old_data(keep_days)
    
    if result['success']:
        click.echo(result['message'])
        if result['archive_path']:
            click.echo(f"Archive location: {result['archive_path']}")
    else:
        click.echo(f"Failed: {result['message']}")

@cli.command()
@click.pass_context
def stats(ctx):
    """Show statistics about collected data"""
    
    stats = get_statistics(include_archives=False)
    
    if stats is None:
        click.echo("No data available")
        return
    
    click.echo("\nStatistics\n" + "="*50)
    click.echo(f"Total readings: {stats['total_readings']}")
    click.echo(f"First reading: {stats['first_reading']}")
    click.echo(f"Last reading: {stats['last_reading']}")
    click.echo(f"Duration: {stats['duration_days']} days")
    
    click.echo(f"\nPressure Statistics (hPa)\n" + "="*50)
    p = stats['pressure']
    click.echo(f"Current: {p['current']:.2f}")
    click.echo(f"Average: {p['average']:.2f}")
    click.echo(f"Minimum: {p['minimum']:.2f}")
    click.echo(f"Maximum: {p['maximum']:.2f}")
    click.echo(f"Range: {p['range']:.2f}")
    
    if 'last_24h' in stats:
        click.echo(f"\nLast 24 Hours\n" + "="*50)
        h24 = stats['last_24h']
        click.echo(f"Readings: {h24['readings']}")
        click.echo(f"Average: {h24['average']:.2f} hPa")
        click.echo(f"Change: {h24['change']:+.2f} hPa")



# web gui
@cli.command()
@click.option("--port", default=5888 )
def web(port):
    """Run local web dashboard"""
    from web.app import create_app

    app = create_app()
    click.echo(f"Web UI running at http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=5888)





@cli.command()
@click.option('--interval', '-i', default=300, show_default=True, help='Interval between readings in seconds')
@click.pass_context
def start(ctx, interval):
    """Start monitoring (runs in foreground)"""
    
    from barometer.background import start_monitoring

    result = start_monitoring(interval)
    
    if result['success']:
        click.echo(f"✓ {result['message']}")
        click.echo(f"  PID: {result['pid']}")
        click.echo("\nMonitoring started. Press Ctrl+C to stop...")
        
        try:
            # Keep process alive
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            click.echo("\n\nStopping monitoring...")
            from barometer.background import stop_monitoring
            stop_monitoring()
            click.echo("Monitoring stopped")
    else:
        click.echo(f"✗ {result['message']}")


@cli.command()
@click.pass_context
def stop(ctx):
    """Stop background monitoring"""

    from barometer.background import stop_monitoring

    result = stop_monitoring()
    
    if result['success']:
        click.echo(f"✓ {result['message']}")
    else:
        click.echo(f"✗ {result['message']}")

if __name__ == "__main__":
    cli(obj={})