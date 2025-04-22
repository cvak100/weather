# logic/scrape.py

from db import connect
from datetime import date as dt_date
import json

from logic.arso import scrape_arso_observed
from logic.timeanddate import scrape_astronomy_sunrise_sunset
from utils import save_weather_observed

DB_FIELDS = [
    "temperature_min", "temperature_max", "temperature_avg",
    "precipitation_mm",
    "humidity_min", "humidity_max", "humidity_avg",
    "snow_depth_cm",
    "sunrise", "sunset", "daylight_minutes",
    "pressure_hpa", "wind_speed_avg", "visibility_km"
]

def scrape_today(args):
    conn = connect()
    cur = conn.cursor()

    target_date = args.date or str(dt_date.today())

    if args.location_id:
        cur.execute("SELECT id, name FROM locations WHERE id = ?", (args.location_id,))
    else:
        cur.execute("SELECT id, name FROM locations")

    locations = cur.fetchall()

    for loc_id, loc_name in locations:
        cur.execute("""
            SELECT id, name, base_url, notes FROM weather_providers
            WHERE location_id = ?
        """, (loc_id,))
        providers = cur.fetchall()

        combined_data = {}

        for prov_id, prov_name, base_url, notes in providers:
            print(f"\n Location: {loc_name} (ID {loc_id})")
            print(f" Provider: {prov_name} (ID {prov_id}) — notes: {notes}")
            print(f" Target date: {target_date}")

            result = None

            if prov_name.lower() == "arso":
                result = scrape_arso_observed(target_date, base_url)
            elif "astronomy" in (notes or "").lower():
                result = scrape_astronomy_sunrise_sunset("3203471")
            elif "history" in (notes or "").lower():
                print(" Would run: scrape_timeanddate_history()")
            else:
                print(" No matching scrape strategy found.")

            if result:
                print(" Result:", result)
                combined_data.update(result)

        if combined_data:
            # Fill in missing fields with None
            full_record = {field: combined_data.get(field, None) for field in DB_FIELDS}
            full_record["data_raw"] = json.dumps(full_record, ensure_ascii=False)
            combined_data["data_raw"] = full_record["data_raw"]

            save_weather_observed(loc_id, target_date, combined_data)
        else:
            print(f"No data gathered for location {loc_name} on {target_date}")

    conn.close()


def scrape_history(args):
    print(f" Scraping historical data for location ID {args.location_id}")
    print(f" From: {args.date_from} To: {args.date_to}")
    if args.provider_id:
        print(f" Restricted to provider ID {args.provider_id}")

    # Here you'd do similar routing logic to above,
    # but within a date range instead of one date.
