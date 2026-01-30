# Spectrum Router Barometer 

Monitor barometric pressure from Spectrum SAX2V1S routers.

## Installation

### Quick install (recommended)
```bash
pipx install spectrum-barometer
```

Or with pip:
```bash 
pip install spectrum-barometer
```



### Install with pip and git
```bash
pipx install git+https://github.com/BobaTeagrl/spectrum-barometer.git
```

Or with pip:
```bash
pip install git+https://github.com/BobaTeagrl/spectrum-barometer.git
```

### Or clone repo and run the file
```bash
git clone https://github.com/BobaTeagrl/spectrum-barometer.git
cd spectrum-barometer

# and run commands with   

python3 barometer_logger.py <command here>
```

## Updating

```bash
pipx upgrade spectrum-barometer

or

pip install --upgrade spectrum-barometer

# If installed with git
pipx uninstall spectrum-barometer
pipx install git+https://github.com/BobaTeagrl/spectrum-barometer.git

# If you cloned repo you have to re clone it

```


### First Time Setup
```bash
# Configure your router credentials
barometer config

# Test the connection
barometer test

```

![image](./README_IMAGES/install.png "screenshot of install process")

All data is stored in `~/spectrum-barometer/` regardless of where you run the command.

## Usage
```bash
# Collect a single reading
barometer scrape

# Start continuous monitoring (every 5 minutes by default)
barometer monitor

# Generate a graph
barometer graph

# View statistics
barometer stats

# Archive old data
barometer archive

# Open the local web UI
barometer web

# Show information about data locations and project setup
barometer info

Append --help to any command to see extra options

```

## WEB UI

You can run the scraper from the web UI or cli but ending the process stops the scrape. i thought i knew how to get around that, but i dont lol. if you do feel free to fork and if you can you will be pulled into the main codebase but for now we live with these limits. the good news is either are both quite light to run and if you run start in terminal, then open a new one and run web and you can freely play in the ui without stopping monitor as long as you dont hit the big red button and start it again, then the process if part of the web server. so feel free to pick whatever is easier for you!

![image](./README_IMAGES/webui.png "web ui dashboard")
![image](./README_IMAGES/stats.png "web stats page")

## Finding Your Data

Everything is stored in `~/spectrum-barometer/`:

- **Graphs**: `~/spectrum-barometer/graphs/`
- **Data**: `~/spectrum-barometer/data/readings.csv`
- **Config**: `~/spectrum-barometer/config.yaml`
- **Logs**: `~/spectrum-barometer/logs/barometer.log`

You can run `barometer info` to see exact paths and current data.

# FAQ

### Why make this?

I find it funny. 

### Any other reason?

Spectrum is a very anti consumer company. this whole project started because i cant even access port forwarding, A VERY BASIC FEATURE and while trying to find a way around it i found the GitHub with the page and credentials used to find the barometer.

### How often can it update?

The barometer seems to update every second but that's super overkill lol but you can if you want to.

### Will you update this ever?

If i have new ideas or find bugs/bugs get reported i may but as it sits with 2.0.0 im not sure what more i would add to this tool that would be more than just bloat.

### How hard is it to run?

When taking a reading it might take a few % of CPU and max ram use i personally have seen is 111MB (though not to say it can never get higher i cant know for sure I'm just one person) but when sitting idle its no CPU. i wanted this to be able to run on anything from a raspberry pi you already have set up running pi hole or something to someones single laptop that they are actively pushing while it runs in the background (because that's me). The web UI takes about 10-20MB of RAM loading and less just sitting there according to firefox profiler.

### Can i use this on (Insert other router here)?

idk! figure it out! I see no reason it couldnt given the correct login and webpage but the scraping logic is a little basic so if the barometer data doesnt sit in a table element, it would not be found. Its totally possible to modify this tool to better scrape more routers but i only have the one to test on so if you want that fuctionality make it yourself or send me your router and like 20$ lol

# None of this would be possible without the work of MeisterLone on GitHub

## He actually put in the work to reverse engineer this stupid router and i wouldn't have even realized routers had barometers without it lmao

## https://github.com/MeisterLone/Askey-RT5010W-D187-REV6


