# Weather Tracker v1.0

A modular, CLI-based weather data collection system using SQLite.  
Supports scraping actual & historical weather and astronomy data from ARSO and TimeAndDate.  
Automated via cron or Jenkins with backup & export features.

## Requirements

- Python 3.8+
- pip install -r requirements.txt (BeautifulSoup, requests, etc.)
- Fedora (or any Linux with bash support)
- SQLite (default)
- Optional: Jenkins, cron

## Setup

git clone https://github.com/cvak100/weather.git
cd weather

# Initialize the database
python weather.py init-db

## Add Locations

python weather.py add-location Breginj 46.2630 13.4263 576 --info "Alpine"

## Add Providers

python weather.py add-provider TimeAndDate https://www.timeanddate.com/astronomy/@3203471 --location-id 1 --notes "astronomy"

python weather.py add-provider TimeAndDate https://www.timeanddate.com/weather/@3203471/historic --location-id 1 --notes "history"

python weather.py add-provider Arso https://meteo.arso.gov.si/uploads/probase/www/observ/surface/text/sl/observationAms_BREGINJ_history.html --location-id 1 --notes "arso"

python weather.py add-provider TimeAndDate https://www.timeanddate.com/sun/@3203471 --location-id 1 --notes "history"

## Scrape Weather

# Scrape today's data
python weather.py scrape-today

python weather.py scrape-today --location-id 1

python weather.py scrape-today --location-id 1 --date 2025-04-21

# Scrape historical range
python weather.py scrape-history --location-id 1 --from 2025-01-01 --to 2025-03-30

## Export Data

python weather.py export --location-id 1 --date 2025-04-21

python weather.py export --location-id 1 --from 2025-03-01 --to 2025-03-07

# Output is pretty JSON and includes location info.

## Automation

# scrape_yesterday.sh

# Cron (every 6h)
H */6 * * * /opt/weather/scrape_yesterday.sh >> /var/log/weather_scrape.log 2>&1

## Backups

# backup_db.sh

# Cron (daily backup)
H 0 * * * /opt/weather/backup_db.sh >> /var/log/weather_backup.log 2>&1

## Version

v1.0 – April 2025  
- Actual & historic scraping  
- Astronomy data  
- Unified DB entries  
- Automation  
- Export  
- Backups

## Future Ideas

- Forecast evaluation
- Chart exports
- Web dashboard
- REST API
 

Maintained with love, cron, and cloudy skies ☁️
