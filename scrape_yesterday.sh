#!/bin/bash

# Navigate to your weather project directory
cd /opt/weather || exit

# Get yesterday's date in YYYY-MM-DD format
YESTERDAY=$(date -d "yesterday" +%F)

# Run the scraper with yesterday's date
python weather.py scrape-today --location-id 1 --date "$YESTERDAY"

# DODAJ PATCH za zadnje 3 dni nazaj (ne vključuje danes)
FROM=$(date -d "3 days ago" +%F)
TO=$(date -d "2 days ago" +%F)

python weather.py patch-fields --location-id 1 --from "$FROM" --to "$TO"
