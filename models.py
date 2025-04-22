# models.py

TABLES = [

    # Locations
    """
    CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        lat REAL NOT NULL,
        lon REAL NOT NULL,
        elevation REAL,
        info TEXT
    );
    """,

    # Weather Providers (linked to location)
    """
    CREATE TABLE IF NOT EXISTS weather_providers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        base_url TEXT,
        notes TEXT,
        location_id INTEGER NOT NULL,
        FOREIGN KEY (location_id) REFERENCES locations(id)
    );
    """,

    # Weather Observed
    """
    CREATE TABLE IF NOT EXISTS weather_observed (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        location_id INTEGER NOT NULL,
        date DATE NOT NULL,
        temperature_min REAL,
        temperature_max REAL,
        temperature_avg REAL,
        precipitation_mm REAL,
        humidity_min REAL,
        humidity_max REAL,
        humidity_avg REAL,
        snow_depth_cm REAL,
        sunrise TEXT,
        sunset TEXT,
        daylight_minutes INTEGER,
        pressure_hpa REAL,
        wind_speed_avg REAL,
        visibility_km REAL,
        data_raw TEXT,
        FOREIGN KEY (location_id) REFERENCES locations(id)
    );
    """
]
