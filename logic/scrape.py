# logic/scrape.py

from db import connect
from datetime import date as dt_date
import json
import html
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from datetime import timedelta
import statistics

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

def scrape_timeanddate_astronomy_history(date: str, base_url: str):
    dt = datetime.strptime(date, "%Y-%m-%d")
    day = dt.day
    month = dt.month
    year = dt.year

    url = f"{base_url}?month={month}&year={year}"
    print(f"Fetching sunrise/sunset data from: {url}")

    resp = requests.get(url)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    row = soup.find("tr", {"data-day": str(day)})
    if not row:
        print(" Could not find row for given day")
        return None

    tds = row.find_all("td")
    if len(tds) < 4:
        print(" Not enough columns in row")
        return None

    sunrise = tds[0].text.strip().split(" ")[0]
    sunset = tds[1].text.strip().split(" ")[0]
    daylight_raw = tds[2].text.strip().split(":")
    try:
        daylight_minutes = int(daylight_raw[0]) * 60 + int(daylight_raw[1])
    except:
        daylight_minutes = None

    return {
        "sunrise": sunrise,
        "sunset": sunset,
        "daylight_minutes": daylight_minutes
    }

def scrape_timeanddate_history(date: str, base_url: str):
    dt = datetime.strptime(date, "%Y-%m-%d")
    year = dt.year
    month = dt.month
    day_str = dt.strftime("%Y%m%d")

    if "@" not in base_url:
        print("Invalid base_url for TimeAndDate history")
        return None

    location_id = base_url.split("@")[1].split("/")[0]
    url = (
        f"https://www.timeanddate.com/scripts/cityajax.php?"
        f"n=@{location_id}&mode=historic&hd={day_str}&month={month}&year={year}&json=1"
    )

    print(f"Fetching TimeAndDate history from: {url}")
    resp = requests.get(url)
    resp.raise_for_status()
    raw_text = resp.text

    # Attempt to convert JS-style structure to JSON
    try:
        # Replace JS-style keys with quoted ones
        fixed = raw_text.replace("c:", "\"c\":").replace("h:", "\"h\":").replace("s:", "\"s\":")
        data = json.loads(fixed)
    except Exception as e:
        print("❌ Failed to parse data structure:", e)
        print(raw_text[:300])
        return None

    temperatures, humidities, wind_speeds = [], [], []
    pressures, visibilities, precipitations = [], [], []

    for entry in data:
        cols = entry.get("c", [])
        if len(cols) < 9:
            continue

        try:
            temp_text = html.unescape(cols[2].get("h", "")).replace("°C", "").strip().replace(",", ".")
            if temp_text:
                temperatures.append(float(temp_text))
        except:
            pass

        try:
            weather_text = html.unescape(cols[3].get("h", "")).lower()
            if "rain" in weather_text or "shower" in weather_text:
                precipitations.append(0.1)  # crude estimate
        except:
            pass

        try:
            wind_text = html.unescape(cols[4].get("h", "")).split(" ")[0].replace(",", ".")
            if wind_text:
                wind_speeds.append(float(wind_text))
        except:
            pass

        try:
            hum_text = html.unescape(cols[6].get("h", "")).replace("%", "")
            if hum_text:
                humidities.append(float(hum_text))
        except:
            pass

        try:
            pressure_text = html.unescape(cols[7].get("h", "")).replace("mbar", "").strip().replace(",", ".")
            if pressure_text:
                pressures.append(float(pressure_text))
        except:
            pass

        try:
            vis_text = html.unescape(cols[8].get("h", "")).replace("km", "").strip().replace(",", ".")
            if vis_text:
                visibilities.append(float(vis_text))
        except:
            pass

    if not temperatures:
        print("No valid temperature data found.")
        return None

    result = {
        "temperature_min": round(min(temperatures), 2),
        "temperature_max": round(max(temperatures), 2),
        "temperature_avg": round(statistics.mean(temperatures), 2),
        "humidity_min": round(min(humidities), 2) if humidities else None,
        "humidity_max": round(max(humidities), 2) if humidities else None,
        "humidity_avg": round(statistics.mean(humidities), 2) if humidities else None,
        "precipitation_mm": round(sum(precipitations), 2),
        "pressure_hpa": round(statistics.mean(pressures), 2) if pressures else None,
        "wind_speed_avg": round(statistics.mean(wind_speeds), 2) if wind_speeds else None,
        "visibility_km": round(statistics.mean(visibilities), 2) if visibilities else None,
        "snow_depth_cm": None,
        "sunrise": None,
        "sunset": None,
        "daylight_minutes": None,
        "data_raw": None
    }

    result["data_raw"] = json.dumps(result, ensure_ascii=False)
    return result


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
    print(f"Scraping history for location {args.location_id} from {args.date_from} to {args.date_to}")

    date_from = datetime.strptime(args.date_from, "%Y-%m-%d").date()
    date_to = datetime.strptime(args.date_to, "%Y-%m-%d").date()

    conn = connect()
    cur = conn.cursor()

    current = date_from
    while current <= date_to:
        date_str = current.strftime("%Y-%m-%d")
        print(f"\n📅 Scraping historical data for {date_str}")

        # Fetch all providers for the location
        cur.execute("""
            SELECT id, name, base_url, notes FROM weather_providers
            WHERE location_id = ? AND notes LIKE '%history%'
        """, (args.location_id,))
        providers = cur.fetchall()

        combined_data = {}

        for prov_id, prov_name, base_url, notes in providers:
            print(f"  Provider: {prov_name} — notes: {notes}")

            if "weather" in base_url:
                result = scrape_timeanddate_history(date_str, base_url)
            elif "sun" in base_url:
                result = scrape_timeanddate_astronomy_history(date_str, base_url)
            else:
                result = None

            if result:
                print(f"    ✔ Data scraped from {prov_name}")
                combined_data.update(result)

        if combined_data:
            # Always include raw snapshot
            combined_data["data_raw"] = json.dumps(combined_data, ensure_ascii=False)
            save_weather_observed(args.location_id, date_str, combined_data)
        else:
            print("  ❌ No data gathered for this day.")

        current += timedelta(days=1)

    conn.close()

# def scrape_history(args):
#     print(f"Scraping history for location {args.location_id} from {args.date_from} to {args.date_to}")
#
#     date_from = datetime.strptime(args.date_from, "%Y-%m-%d").date()
#     date_to = datetime.strptime(args.date_to, "%Y-%m-%d").date()
#
#     conn = connect()
#     cur = conn.cursor()
#
#     # Find base_url for history provider (optional filter by provider ID)
#     if args.provider_id:
#         cur.execute("SELECT base_url FROM weather_providers WHERE id = ?", (args.provider_id,))
#     else:
#         cur.execute("""
#             SELECT base_url FROM weather_providers
#             WHERE location_id = ? AND notes LIKE '%history%'
#             LIMIT 1
#         """, (args.location_id,))
#     row = cur.fetchone()
#
#     if not row:
#         print("No base_url found for history provider.")
#         return
#
#     base_url = row[0]
#
#     # Loop over each day in the date range
#     current = date_from
#     while current <= date_to:
#         date_str = current.strftime("%Y-%m-%d")
#         print(f"\n📅 Scraping historical data for {date_str}")
#         result = scrape_timeanddate_history(date_str, base_url)
#         if result:
#             save_weather_observed(args.location_id, date_str, result)
#         current += timedelta(days=1)
#
#     conn.close()