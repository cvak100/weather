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
    """Create or update the database schema to ensure all required columns exist."""
    logging.info("Ensuring database schema is up to date.")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create table if it does not exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weather_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT,
            date TEXT,
            avg_temperature REAL,
            min_temperature REAL,
            max_temperature REAL,
            avg_humidity REAL,
            min_humidity REAL,
            max_humidity REAL,
            pressure REAL,
            min_pressure REAL,  -- Added
            max_pressure REAL,  -- Added
            precipitation REAL,
            total_precipitation REAL,
            snow_depth REAL,
            wind_speed REAL,
            wind_gust REAL,
            wind_direction TEXT,
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

    # **Check if columns exist, and add them if missing**
    existing_columns = [row[1] for row in cursor.execute("PRAGMA table_info(weather_data)").fetchall()]
    alter_statements = []

    if "min_pressure" not in existing_columns:
        alter_statements.append("ALTER TABLE weather_data ADD COLUMN min_pressure REAL;")
    if "max_pressure" not in existing_columns:
        alter_statements.append("ALTER TABLE weather_data ADD COLUMN max_pressure REAL;")

    # Execute ALTER TABLE if needed
    for stmt in alter_statements:
        cursor.execute(stmt)
        logging.info(f"Executed: {stmt}")

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

            # Extract and handle missing data
            try:
                temperature_value = float(temperature_elements[i].get_text(strip=True).replace(",", "."))
            except (IndexError, ValueError, AttributeError):
                temperature_value = 0  # Default to 0 if missing

            try:
                humidity_value = int(humidity_elements[i].get_text(strip=True))
            except (IndexError, ValueError, AttributeError):
                humidity_value = 0  # Default to 0 if missing

            try:
                precipitation_value = float(precipitation_elements[i].get_text(strip=True).replace(",", "."))
            except (IndexError, ValueError, AttributeError):
                precipitation_value = 0  # Default to 0 if missing

            try:
                total_precipitation_value = float(
                    total_precipitation_elements[i].get_text(strip=True).replace(",", "."))
            except (IndexError, ValueError, AttributeError):
                total_precipitation_value = 0  # Default to 0 if missing

            try:
                snow_depth_value = float(snow_elements[i].get_text(strip=True).replace(",", "."))
            except (IndexError, ValueError, AttributeError):
                snow_depth_value = 0  # Default to 0 if missing

            # Store the extracted data
            daily_data[formatted_date]["temperature"].append(temperature_value)
            daily_data[formatted_date]["humidity"].append(humidity_value)
            daily_data[formatted_date]["precipitation"].append(precipitation_value)
            daily_data[formatted_date]["total_precipitation"].append(total_precipitation_value)
            daily_data[formatted_date]["snow_depth"].append(snow_depth_value)

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
        min_humidity = round(min(values["humidity"]), 2) if values["humidity"] else None
        max_humidity = round(max(values["humidity"]), 2) if values["humidity"] else None
        total_precipitation = round(sum(values["total_precipitation"]), 2) if values["total_precipitation"] else None
        avg_precipitation = round(sum(values["precipitation"]) / len(values["precipitation"]), 2) if values["precipitation"] else None
        avg_snow_depth = round(sum(values["snow_depth"]), 2) if values["snow_depth"] else None

        # Ensure ALL data is included in the DB
        cursor.execute('''
            INSERT INTO weather_data (
                location, date, avg_temperature, min_temperature, max_temperature, 
                avg_humidity, min_humidity, max_humidity, precipitation, total_precipitation, snow_depth,
                wind_speed, wind_gust, wind_direction, pressure, visibility, uv_index,
                sunshine_duration, cloud_cover, sunrise, sunset, info
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(location, date) DO UPDATE SET 
                avg_temperature=excluded.avg_temperature,
                min_temperature=excluded.min_temperature,
                max_temperature=excluded.max_temperature,
                avg_humidity=excluded.avg_humidity,
                min_humidity=excluded.min_humidity,
                max_humidity=excluded.max_humidity,
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
            avg_humidity, min_humidity, max_humidity, avg_precipitation, total_precipitation, avg_snow_depth,
            values["wind_speed"], values["wind_gust"], values["wind_direction"],
            values["pressure"], values["visibility"], values["uv_index"],
            values["sunshine_duration"], values["cloud_cover"],
            values["sunrise"], values["sunset"], values["info"]  # Added missing column value
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


def clean_numeric_value(text):
    """Extracts only the numeric part from the scraped value (removes extra date/time info)."""
    match = re.search(r"-?\d+(\.\d+)?", text)  # Find numbers including negatives & decimals
    return float(match.group()) if match else None


def extract_historical_weather_data(year, month=None, day=None):
    """Fetch historical weather data from Time and Date for a specific year, month, or day, and save it to DB."""

    try:
        year = int(year)  # Ensure year is an integer
        month = int(month) if month else None
        day = int(day) if day else None
    except ValueError:
        logging.error("Invalid input: Year, month, and day must be integers.")
        return

    # Connect to the database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Determine URL structure based on input type
    if month is None:
        # If only year is provided, get data for the 1st day of each month
        logging.info(f"Fetching historical weather data for {year} (first day of each month).")
        months = range(1, 13)
        days = [1]  # Fetch only the first day
    elif day is None:
        # If year and month are provided, get data for all days in the month
        logging.info(f"Fetching historical weather data for {year}-{month} (all days in month).")
        months = [month]
        days = range(1, 32)  # Attempt all days (invalid dates are skipped)
    else:
        # If year, month, and day are provided, get data for just that day
        logging.info(f"Fetching historical weather data for {year}-{month}-{day}.")
        months = [month]
        days = [day]

    # Iterate over selected months and days
    for month in months:
        for day in days:
            try:
                # Validate the date
                date_str = f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"
                datetime.strptime(date_str, "%Y-%m-%d")  # Throws an error if the date is invalid
            except ValueError:
                continue  # Skip invalid dates

            location_url = f"https://www.timeanddate.com/weather/@3203471/historic?month={month}&year={year}"
            response = requests.get(location_url)
            if response.status_code != 200:
                logging.error(f"Failed to fetch historical data for {date_str} (status code {response.status_code})")
                continue  # Skip to the next date if the request fails

            soup = BeautifulSoup(response.text, "html.parser")

            # Find the historical weather table
            summary_table = soup.find("table", {"class": "zebra tb-wt fw tb-hover"})

            if not summary_table:
                logging.warning(f"No historical weather data found for {date_str}")
                continue  # Skip if no data is available

            rows = summary_table.find_all("tr")

            # Storage for extracted data
            summary_data = {
                "location": "Breginj",
                "date": date_str,
                "avg_temperature": None,
                "min_temperature": None,
                "max_temperature": None,
                "avg_humidity": None,
                "min_humidity": None,
                "max_humidity": None,
                "pressure": None,  # Save as `pressure` in DB
                "min_pressure": None,
                "max_pressure": None,
                "info": f"Historical weather summary for Breginj on {date_str}"
            }

            for row in rows:
                cols = row.find_all("td")

                # Check if this is the High row
                if "High" in row.text:
                    summary_data["max_temperature"] = clean_numeric_value(cols[0].get_text(strip=True))
                    summary_data["max_humidity"] = clean_numeric_value(cols[1].get_text(strip=True))
                    summary_data["max_pressure"] = clean_numeric_value(cols[2].get_text(strip=True))

                # Check if this is the Low row
                elif "Low" in row.text:
                    summary_data["min_temperature"] = clean_numeric_value(cols[0].get_text(strip=True))
                    summary_data["min_humidity"] = clean_numeric_value(cols[1].get_text(strip=True))
                    summary_data["min_pressure"] = clean_numeric_value(cols[2].get_text(strip=True))

                # Check if this is the Average row
                elif "Average" in row.text:
                    summary_data["avg_temperature"] = clean_numeric_value(cols[0].get_text(strip=True))
                    summary_data["avg_humidity"] = clean_numeric_value(cols[1].get_text(strip=True))
                    summary_data["pressure"] = clean_numeric_value(cols[2].get_text(strip=True))  # Saved as `pressure`

            # Replace `None` with `NULL` for proper DB insertion
            summary_data = {key: (value if value is not None else None) for key, value in summary_data.items()}

            # Insert data into the database (or update existing records)
            cursor.execute('''
                INSERT INTO weather_data (
                    location, date, avg_temperature, min_temperature, max_temperature, 
                    avg_humidity, min_humidity, max_humidity, pressure, min_pressure, max_pressure, info
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(location, date) DO UPDATE SET 
                    avg_temperature=excluded.avg_temperature,
                    min_temperature=excluded.min_temperature,
                    max_temperature=excluded.max_temperature,
                    avg_humidity=excluded.avg_humidity,
                    min_humidity=excluded.min_humidity,
                    max_humidity=excluded.max_humidity,
                    pressure=excluded.pressure,
                    min_pressure=excluded.min_pressure,
                    max_pressure=excluded.max_pressure,
                    info=excluded.info
            ''', (
                summary_data["location"], summary_data["date"], summary_data["avg_temperature"],
                summary_data["min_temperature"], summary_data["max_temperature"],
                summary_data["avg_humidity"], summary_data["min_humidity"], summary_data["max_humidity"],
                summary_data["pressure"], summary_data["min_pressure"], summary_data["max_pressure"],
                summary_data["info"]
            ))

            conn.commit()

            # Print extracted summary
            print("\n📊 **Historical Weather Data (Saved to DB)**")
            print(json.dumps(summary_data, indent=4))

    conn.close()
    logging.info(f"Finished fetching and saving historical weather data for {year}.")


# Command-line argument handling
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Weather Data Scraper & Database Manager")
    parser.add_argument("--create_database", action="store_true", help="Create the database if it doesn't exist")
    parser.add_argument("--extract_weather_data", type=str, help="Extract weather data for a specific location")
    parser.add_argument("--extract_historical_weather_data", nargs="+", help="Extract historical weather data for a year or year + month range")
    parser.add_argument("--get_weather_data", nargs="+", help="Get weather data (date or date range, location)")

    args = parser.parse_args()

    if args.create_database:
        create_database()

    if args.extract_weather_data:
        extract_weather_data(args.extract_weather_data)

    if args.extract_historical_weather_data:
        if len(args.extract_historical_weather_data) == 1:  # Only year provided
            extract_historical_weather_data(args.extract_historical_weather_data[0])
        elif len(args.extract_historical_weather_data) == 2:  # Year + start month
            extract_historical_weather_data(args.extract_historical_weather_data[0],
                                            args.extract_historical_weather_data[1])
        elif len(args.extract_historical_weather_data) == 3:  # Year + start month + end month
            extract_historical_weather_data(args.extract_historical_weather_data[0],
                                            args.extract_historical_weather_data[1],
                                            args.extract_historical_weather_data[2])
        else:
            print("Invalid arguments. Use:")
            print("  --extract_historical_weather_data <year>")
            print("  --extract_historical_weather_data <year> <start_month>")
            print("  --extract_historical_weather_data <year> <start_month> <end_month>")

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


