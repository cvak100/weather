# 📄 Weather Data Scraper

This Python script scrapes weather data from public sources and stores it in a SQLite database. It supports real-time and historical weather data extraction, as well as data retrieval.

## 📌 Features

✅ **Extract live weather data** for a location and store it in the database.  
✅ **Extract historical weather data** (monthly or daily) and store it.  
✅ **Retrieve saved weather data** for a specific date or date range.  
✅ **Automatic database schema management** (ensures all necessary columns exist).  

---

## 🚀 Usage Examples

### 1️⃣ Initialize the Database
Before running extractions, ensure the database schema is set up:
```bash
python weather.py --create_database
```

### 2️⃣ Extract Current Weather Data
Fetch and store the **latest** weather data for a location:
```bash
python weather.py --extract_weather_data Breginj
```

### 3️⃣ Extract Historical Weather Data

##### 📌 (a) Extract First Day of Each Month in a Year
```bash
python weather.py --extract_historical_weather_data 2024
```
##### 📌 (b) Extract All Days for a Specific Month
```bash
python weather.py --extract_historical_weather_data 2024 2
```
##### 📌 (c) Extract Weather for a Specific Day
```bash
python weather.py --extract_historical_weather_data 2024 2 1
```

### 4️⃣ Retrieve Weather Data from the Database

##### 📌 (a) Get All Saved Data
```bash
python weather.py --get_weather_data
```
##### 📌  (b) Get Data for a Specific Day
```bash
python weather.py --get_weather_data 2024-02-01 Breginj
```
##### 📌 (c) Get Data for a Date Range
```bash
python weather.py --get_weather_data 2024-01-01 2024-02-01 Breginj
```

---

## 🔧 Logs & Debugging
All logs are saved to weather_scraper.log.

## 🔧 Logs & Debugging
Data is stored in weather_data.db (SQLite).
The script auto-creates missing database columns.
Works for multiple locations (extend LOCATIONS dictionary in the script).

