import requests
from bs4 import BeautifulSoup
import re
import sqlite3
import json
import argparse
import logging
from collections import defaultdict
from datetime import datetime

# Configure logging
LOG_FILE = "weather_scraper.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode='a'),  # Append to log file
        logging.StreamHandler()  # Display logs in console
    ]
)

# Database configuration
DB_PATH = "weather_data.db"

# Define locations and their respective data URLs
LOCATIONS = {
    "Breginj": {
        "weather_url": "https://meteo.arso.gov.si/uploads/probase/www/observ/surface/text/sl/observationAms_BREGINJ_history.html",
        "sun_url": "https://www.timeanddate.com/sun/@3203471"
    },
    "Logatec": {
        "weather_url": "https://www.meteo.si/uploads/probase/www/observ/surface/text/sl/observationAms_LOGATEC_history.html",
        "sun_url": "https://www.timeanddate.com/sun/@3203471"
    }
}

# Slovenian day name corrections
DAY_CORRECTIONS = {
    "Ponedeljek": "Monday",
    "Torek": "Tuesday",
    "Sreda": "Wednesday",
    "Četrtek": "Thursday",
    "Petek": "Friday",
    "Sobota": "Saturday",
    "Nedelja": "Sunday",
    "Äetrtek": "Četrtek",
}


def create_database():
    """Create database table if it does not exist."""
    logging.info("Creating database if not exists.")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weather_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT,
            date TEXT,
            avg_temperature REAL,
            min_temperature REAL,
            max_temperature REAL,
            humidity REAL,
            precipitation REAL,
            total_precipitation REAL,
            snow_depth REAL,
            wind_speed REAL,
            wind_gust REAL,
            wind_direction TEXT,
            pressure REAL,
            visibility REAL,
            uv_index REAL,
            sunshine_duration REAL,
            cloud_cover REAL,
            sunrise TEXT,
            sunset TEXT,
            info TEXT,
            UNIQUE(location, date) ON CONFLICT REPLACE
        )
    ''')
    conn.commit()
    conn.close()



def extract_weather_data(location):
    """Fetch weather data and sunrise/sunset times for a specific location and save all data to DB."""
    if location not in LOCATIONS:
        logging.error(f"Location '{location}' not found in settings.")
        return

    weather_url = LOCATIONS[location]["weather_url"]
    sun_url = LOCATIONS[location]["sun_url"]

    logging.info(f"Fetching weather data for {location} from {weather_url}")
    response = requests.get(weather_url)
    if response.status_code != 200:
        logging.error(f"Failed to fetch weather data for {location} (status code {response.status_code})")
        return

    soup = BeautifulSoup(response.text, "html.parser")

    # Find elements by ID
    date_elements = soup.find_all("td", class_="meteoSI-th")
    temperature_elements = soup.find_all("td", id="t")
    humidity_elements = soup.find_all("td", id="rh")
    precipitation_elements = soup.find_all("td", id="rr_val")
    total_precipitation_elements = soup.find_all("td", id="tp_12h_acc")
    snow_elements = soup.find_all("td", id="snow")

    # Store data per day
    daily_data = defaultdict(lambda: {
        "temperature": [], "humidity": [], "precipitation": [], "total_precipitation": [], "snow_depth": [],
        "wind_speed": None, "wind_gust": None, "wind_direction": None,
        "pressure": None, "visibility": None, "uv_index": None, "sunshine_duration": None, "cloud_cover": None,
        "sunrise": None, "sunset": None, "info": None
    })

    for i, date_element in enumerate(date_elements):
        raw_date_text = date_element.get_text(strip=True)

        # Extract date (without time)
        match = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", raw_date_text)
        if match:
            day, month, year = match.groups()
            formatted_date = f"{year}-{month}-{day}"  # Convert to YYYY-MM-DD format

            # Append temperature data to calculate min/max/avg
            temperature_value = float(temperature_elements[i].get_text(strip=True).replace(",", "."))
            daily_data[formatted_date]["temperature"].append(temperature_value)

            # Append other weather data
            daily_data[formatted_date]["humidity"].append(int(humidity_elements[i].get_text(strip=True)))
            daily_data[formatted_date]["precipitation"].append(float(precipitation_elements[i].get_text(strip=True).replace(",", ".")))
            daily_data[formatted_date]["total_precipitation"].append(float(total_precipitation_elements[i].get_text(strip=True).replace(",", ".")))
            daily_data[formatted_date]["snow_depth"].append(float(snow_elements[i].get_text(strip=True).replace(",", ".")))

    # Fetch sunrise and sunset times
    logging.info(f"Fetching sunrise and sunset data for {location} from {sun_url}")
    sun_response = requests.get(sun_url)
    if sun_response.status_code != 200:
        logging.error(f"Failed to fetch sunrise/sunset data for {location} (status code {sun_response.status_code})")
        return

    sun_soup = BeautifulSoup(sun_response.text, "html.parser")
    sun_table = sun_soup.find("table", {"class": "table table--left table--inner-borders-rows"})

    if sun_table:
        rows = sun_table.find_all("tr")
        for row in rows:
            th = row.find("th")
            td = row.find("td")

            if th and td:
                header_text = th.get_text(strip=True)
                value_text = td.get_text(strip=True).split("↑")[0].strip()  # Remove directional arrows

                # Apply sunrise and sunset to ALL available dates
                for date in daily_data.keys():
                    if "Sunrise Today" in header_text:
                        daily_data[date]["sunrise"] = value_text
                    elif "Sunset Today" in header_text:
                        daily_data[date]["sunset"] = value_text

    # Compute daily averages and save to DB
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for date, values in daily_data.items():
        avg_temperature = round(sum(values["temperature"]) / len(values["temperature"]), 2) if values["temperature"] else None
        min_temperature = round(min(values["temperature"]), 2) if values["temperature"] else None
        max_temperature = round(max(values["temperature"]), 2) if values["temperature"] else None
        avg_humidity = round(sum(values["humidity"]) / len(values["humidity"]), 2) if values["humidity"] else None
        total_precipitation = round(sum(values["total_precipitation"]), 2) if values["total_precipitation"] else None
        avg_precipitation = round(sum(values["precipitation"]) / len(values["precipitation"]), 2) if values["precipitation"] else None
        avg_snow_depth = round(sum(values["snow_depth"]), 2) if values["snow_depth"] else None

        # Ensure ALL data is included in the DB
        cursor.execute('''
            INSERT INTO weather_data (
                location, date, avg_temperature, min_temperature, max_temperature, 
                humidity, precipitation, total_precipitation, snow_depth,
                wind_speed, wind_gust, wind_direction, pressure, visibility, uv_index,
                sunshine_duration, cloud_cover, sunrise, sunset, info
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(location, date) DO UPDATE SET 
                avg_temperature=excluded.avg_temperature,
                min_temperature=excluded.min_temperature,
                max_temperature=excluded.max_temperature,
                humidity=excluded.humidity,
                precipitation=excluded.precipitation,
                total_precipitation=excluded.total_precipitation,
                snow_depth=excluded.snow_depth,
                wind_speed=excluded.wind_speed,
                wind_gust=excluded.wind_gust,
                wind_direction=excluded.wind_direction,
                pressure=excluded.pressure,
                visibility=excluded.visibility,
                uv_index=excluded.uv_index,
                sunshine_duration=excluded.sunshine_duration,
                cloud_cover=excluded.cloud_cover,
                sunrise=excluded.sunrise,
                sunset=excluded.sunset,
                info=excluded.info
        ''', (
            location, date, avg_temperature, min_temperature, max_temperature,
            avg_humidity, avg_precipitation, total_precipitation, avg_snow_depth,
            values["wind_speed"], values["wind_gust"], values["wind_direction"],
            values["pressure"], values["visibility"], values["uv_index"],
            values["sunshine_duration"], values["cloud_cover"],
            values["sunrise"], values["sunset"], values["info"]
        ))

    conn.commit()
    conn.close()
    logging.info(f"Weather data for {location} successfully saved to database!")



def get_weather_data(start_date=None, end_date=None, location=None):
    """Retrieve all weather data from the database and return as JSON, including missing values."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = "SELECT * FROM weather_data WHERE 1=1"
    params = []

    if location:
        query += " AND location = ?"
        params.append(location)

    if start_date and end_date:
        query += " AND date BETWEEN ? AND ?"
        params.extend([start_date, end_date])
    elif start_date:
        query += " AND date = ?"
        params.append(start_date)

    cursor.execute(query, params)
    rows = cursor.fetchall()

    # Get column names
    column_names = [desc[0] for desc in cursor.description]

    conn.close()

    # Convert rows into JSON format, ensuring all fields are included
    result = []
    for row in rows:
        data_entry = dict(zip(column_names, row))

        # Ensure every key has a value (if missing, set to None)
        for key in column_names:
            if key not in data_entry or data_entry[key] is None:
                data_entry[key] = None

        result.append(data_entry)

    return json.dumps(result, indent=4)


def extract_historical_weather_data(location, year, month):
    """Fetch monthly summary weather data from Time and Date and print it."""
    if location not in LOCATIONS:
        logging.error(f"Location '{location}' not found in settings.")
        return

    base_url = "https://www.timeanddate.com/weather/@3203471/historic"
    location_url = f"{base_url}?month={month}&year={year}"

    logging.info(f"Fetching monthly summary weather data for {location}: {year}-{month}")

    response = requests.get(location_url)
    if response.status_code != 200:
        logging.error(f"Failed to fetch monthly summary data for {location} (status code {response.status_code})")
        return

    soup = BeautifulSoup(response.text, "html.parser")

    # Find the monthly summary table
    summary_table = soup.find("table", {"class": "zebra tb-wt fw tb-hover"})

    if not summary_table:
        logging.error("No monthly summary table found on the page.")
        print("Error: No summary data available for the selected month.")
        return

    rows = summary_table.find_all("tr")

    # Storage for extracted data
    summary_data = {
        "high_temp": None,
        "high_temp_time": None,
        "low_temp": None,
        "low_temp_time": None,
        "avg_temp": None,
        "high_humidity": None,
        "high_humidity_time": None,
        "low_humidity": None,
        "low_humidity_time": None,
        "avg_humidity": None,
        "high_pressure": None,
        "high_pressure_time": None,
        "low_pressure": None,
        "low_pressure_time": None,
        "avg_pressure": None
    }

    for row in rows:
        cols = row.find_all("td")

        # Check if this is the High row
        if "High" in row.text:
            summary_data["high_temp"] = cols[0].get_text(strip=True).replace("°C", "").strip()
            summary_data["high_temp_time"] = cols[0].find("span").get_text(strip=True).replace("(", "").replace(")", "")
            summary_data["high_humidity"] = cols[1].get_text(strip=True).replace("%", "").strip()
            summary_data["high_humidity_time"] = cols[1].find("span").get_text(strip=True).replace("(", "").replace(")", "")
            summary_data["high_pressure"] = cols[2].get_text(strip=True).replace("mbar", "").strip()
            summary_data["high_pressure_time"] = cols[2].find("span").get_text(strip=True).replace("(", "").replace(")", "")

        # Check if this is the Low row
        elif "Low" in row.text:
            summary_data["low_temp"] = cols[0].get_text(strip=True).replace("°C", "").strip()
            summary_data["low_temp_time"] = cols[0].find("span").get_text(strip=True).replace("(", "").replace(")", "")
            summary_data["low_humidity"] = cols[1].get_text(strip=True).replace("%", "").strip()
            summary_data["low_humidity_time"] = cols[1].find("span").get_text(strip=True).replace("(", "").replace(")", "")
            summary_data["low_pressure"] = cols[2].get_text(strip=True).replace("mbar", "").strip()
            summary_data["low_pressure_time"] = cols[2].find("span").get_text(strip=True).replace("(", "").replace(")", "")

        # Check if this is the Average row
        elif "Average" in row.text:
            summary_data["avg_temp"] = cols[0].get_text(strip=True).replace("°C", "").strip()
            summary_data["avg_humidity"] = cols[1].get_text(strip=True).replace("%", "").strip()
            summary_data["avg_pressure"] = cols[2].get_text(strip=True).replace("mbar", "").strip()

    # Print extracted summary
    print(f"\n📊 **Monthly Weather Summary for {location} ({year}-{month})**\n")
    print(f"   🔥 **Highest Temperature:** {summary_data['high_temp']}°C at {summary_data['high_temp_time']}")
    print(f"   ❄️ **Lowest Temperature:** {summary_data['low_temp']}°C at {summary_data['low_temp_time']}")
    print(f"   🌡️ **Average Temperature:** {summary_data['avg_temp']}°C")
    print(f"   💦 **Highest Humidity:** {summary_data['high_humidity']}% at {summary_data['high_humidity_time']}")
    print(f"   💨 **Lowest Humidity:** {summary_data['low_humidity']}% at {summary_data['low_humidity_time']}")
    print(f"   💧 **Average Humidity:** {summary_data['avg_humidity']}%")
    print(f"   🔼 **Highest Pressure:** {summary_data['high_pressure']} mbar at {summary_data['high_pressure_time']}")
    print(f"   🔽 **Lowest Pressure:** {summary_data['low_pressure']} mbar at {summary_data['low_pressure_time']}")
    print(f"   📊 **Average Pressure:** {summary_data['avg_pressure']} mbar")
    print("-" * 50)

    logging.info(f"Finished fetching monthly summary weather data for {location} ({year}-{month}).")



# Command-line argument handling
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Weather Data Scraper & Database Manager")
    parser.add_argument("--create_database", action="store_true", help="Create the database if it doesn't exist")
    parser.add_argument("--extract_weather_data", type=str, help="Extract weather data for a specific location")
    parser.add_argument("--extract_historical_weather_data", nargs=3,
                        help="Extract historical weather data (location, year, month)")
    parser.add_argument("--get_weather_data", nargs="+", help="Get weather data (date or date range, location)")

    args = parser.parse_args()

    if args.create_database:
        create_database()

    if args.extract_weather_data:
        extract_weather_data(args.extract_weather_data)

    if args.extract_historical_weather_data:
        location = args.extract_historical_weather_data[0]
        year = int(args.extract_historical_weather_data[1])
        month = int(args.extract_historical_weather_data[2])
        extract_historical_weather_data(location, year, month)

    if hasattr(args, "get_weather_data") and args.get_weather_data:
        if len(args.get_weather_data) == 2:  # Single date request
            start_date = args.get_weather_data[0]
            location = args.get_weather_data[1]
            print(get_weather_data(start_date, None, location))
        elif len(args.get_weather_data) == 3:  # Date range request
            start_date = args.get_weather_data[0]
            end_date = args.get_weather_data[1]
            location = args.get_weather_data[2]
            print(get_weather_data(start_date, end_date, location))
        else:
            print(
                "Invalid arguments. Use: --get_weather_data <start_date> <end_date> <location> OR --get_weather_data <date> <location>")


