#!/bin/bash

# Navigate to your weather project directory
cd /opt/weather || exit

# Get yesterday's date in YYYY-MM-DD format
YESTERDAY=$(date -d "yesterday" +%F)

# Run the scraper with yesterday's date
python weather.py scrape-today --location-id 1 --date "$YESTERDAY"
