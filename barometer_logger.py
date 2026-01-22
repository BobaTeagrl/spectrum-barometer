import logging
import pandas 
import requests
import urllib3
import yaml
import time
from datetime import datetime
import os
from io import StringIO
import re

# disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('barometer_readings.log'),
        logging.StreamHandler()
    ]
)

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
        self.wait = config['wait_time']
        
        logging.info(f"Loaded config - URL: {self.url}")
    
    # connect to router
    def login(self):
        try: 
            logging.info("Trying to connect to router...")
            
            # try to access with basic auth
            response = self.session.get(self.url, auth=(self.username, self.password), timeout=10)
            
            logging.info(f"Response status code: {response.status_code}")
            
            if response.status_code == 200:
                logging.info("Successfully accessed the page")
                return response
            elif response.status_code == 401:
                logging.error("Auth failed, check username/password")
                return None
            else:
                logging.error(f"Failed to access page. Status code: {response.status_code}")
                return None
                
        # error handling    
        except requests.exceptions.RequestException as e:
            logging.error(f"Connection error: {e}")
            return None
    
    def extract_barometer_value(self, html_content):
        
        try:
            
            
            
            # wrap HTML string in StringIO to avoid warning
            tables = pandas.read_html(StringIO(html_content))
            
            logging.info(f"Found {len(tables)} table(s) on the page")
            
            if not tables:
                logging.error("No tables found")
                return None
            
            # get the first (and only) table
            df = tables[0]
            
            # find the row where Field column contains "Barometer Value"
            barometer_row = df[df['Field'] == 'Barometer Value']
            
            if barometer_row.empty:
                logging.error("Could not find 'Barometer Value' in table")
                return None
            
            # get the Setting value (should be like "Pressure = 96231")
            setting_value = barometer_row['Setting'].values[0]
            
            # extract the number using regex
            match = re.search(r'(\d+)', setting_value)
            
            if match:
                pressure = int(match.group(1))
                logging.info(f"Extracted pressure: {pressure} Pa ({pressure/100:.2f} hPa)")
                return pressure
            else:
                logging.error(f"Could not parse pressure from: {setting_value}")
                return None
            
        except ValueError as e:
            logging.error(f"No tables found in HTML: {e}")
            return None
        except Exception as e:
            logging.error(f"Error parsing HTML: {e}")
            return None

    def save_reading(self, pressure):
        # save to CSV
        # create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)
        
        data = {
            'timestamp': [datetime.now().isoformat()],
            'pressure_pa': [pressure],
            'pressure_hpa': [pressure / 100]
        }
        
        df = pandas.DataFrame(data)
        
        # check if file exists to determine if we need headers
        file_exists = os.path.isfile('data/readings.csv')
        
        df.to_csv('data/readings.csv', mode='a', header=not file_exists, index=False)
        logging.info(f"Saved reading to data/readings.csv")

if __name__ == "__main__":
    # create scraper ONCE
    scraper = BarometerScraper()
    
    logging.info("Starting barometer monitoring")
    logging.info("Press Ctrl+C to dtop")

 #loop
    while True:
         try:
             # login and get the page
             response = scraper.login()

             if response:
                # get pressure
                 pressure = scraper.extract_barometer_value(response.text)


                 if pressure:
                    # save and print
                     scraper.save_reading(pressure)
                     logging.info(f"Barometer: {pressure} Pa")
                     logging.info("eeping")
                 else: 
                    logging.error("Failed to get pressure")
             else:
                 logging.error("Failed to connect")
         except Exception as e:
             logging.error(f"Error: {e}")
         
         time.sleep(scraper.wait)  # wait in seconds from config file