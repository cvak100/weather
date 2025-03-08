📄 README: Weather Data Scraper & Database Manager
This Python script scrapes weather data from public sources and stores it in a SQLite database.
It supports real-time and historical weather data extraction, as well as data retrieval.

📌 Features
✅ Extract live weather data for a location and store it in the database.
✅ Extract historical weather data (monthly or daily) and store it.
✅ Retrieve saved weather data for a specific date or date range.
✅ Automatic database schema management (ensures all necessary columns exist).


🚀 Usage Examples

1️⃣ Initialize the Database
Before running extractions, ensure the database schema is set up:

python weather.py --create_database
✅ This creates/updates the database if needed.

2️⃣ Extract Current Weather Data
Fetch and store the latest weather data for a location:

python weather.py --extract_weather_data Breginj
✅ This scrapes the latest weather and inserts it into the database.

3️⃣ Extract Historical Weather Data
📌 (a) Extract First Day of Each Month in a Year

python weather.py --extract_historical_weather_data 2024
✅ Fetches weather for the first day of each month in 2024.

📌 (b) Extract All Days for a Specific Month

python weather.py --extract_historical_weather_data 2024 2
✅ Fetches weather for all days in February 2024.

📌 (c) Extract Weather for a Specific Day

python weather.py --extract_historical_weather_data 2024 2 1
✅ Fetches weather only for February 1st, 2024.

4️⃣ Retrieve Weather Data from the Database
📌 (a) Get All Saved Data

python weather.py --get_weather_data
✅ Returns all saved weather records.

📌 (b) Get Data for a Specific Day

python weather.py --get_weather_data 2024-02-01 Breginj
✅ Fetches weather data for February 1st, 2024, in Breginj.

📌 (c) Get Data for a Date Range

python weather.py --get_weather_data 2024-01-01 2024-02-01 Breginj
✅ Fetches all weather data from Jan 1 to Feb 1, 2024.

🔧 Logs & Debugging
All logs are saved to weather_scraper.log.

📌 Notes
Data is stored in weather_data.db (SQLite).
The script auto-creates missing database columns.
Works for multiple locations (extend LOCATIONS dictionary in the script).
