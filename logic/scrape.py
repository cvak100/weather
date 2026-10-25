# logic/scrape.py

from db import connect
from datetime import date as dt_date
import json
import html
import re
from bs4 import BeautifulSoup
from datetime import datetime
from datetime import timedelta
import statistics

from logic.arso import scrape_arso_observed
from logic.timeanddate import scrape_astronomy_sunrise_sunset
from logic.http_client import fetch_text
from logic.sunmath import astronomy_from_location
from utils import save_weather_observed

DB_FIELDS = [
    "temperature_min", "temperature_max", "temperature_avg",
    "precipitation_mm",
    "humidity_min", "humidity_max", "humidity_avg",
    "snow_depth_cm",
    "sunrise", "sunset", "daylight_minutes",
    "pressure_hpa", "wind_speed_avg", "visibility_km"
]


def _location_id_from_url(base_url: str):
    if not base_url or "@" not in base_url:
        return None
    return base_url.split("@", 1)[1].split("/")[0].split("?")[0]


def scrape_timeanddate_astronomy_history(date: str, base_url: str):
    dt = datetime.strptime(date, "%Y-%m-%d")
    day = dt.day
    month = dt.month
    year = dt.year

    url = f"{base_url}?month={month}&year={year}"
    print(f"Fetching sunrise/sunset data from: {url}")

    page = fetch_text(url)
    if not page:
        return None

    soup = BeautifulSoup(page, "html.parser")
    row = soup.find("tr", {"data-day": str(day)})
    if not row:
        # Newer markup: first column is day number
        for tr in soup.select("table tr"):
            tds = tr.find_all("td")
            if not tds:
                continue
            day_cell = tds[0].get_text(strip=True)
            if day_cell == str(day) or day_cell == f"{day:02d}":
                row = tr
                break

    if not row:
        print(" Could not find row for given day")
        return None

    tds = row.find_all("td")
    # data-day rows: td[0]=sunrise, td[1]=sunset, td[2]=daylength
    # numbered-day rows: td[0]=day, td[1]=sunrise, td[2]=sunset, td[3]=length
    if row.has_attr("data-day"):
        if len(tds) < 3:
            print(" Not enough columns in row")
            return None
        sunrise_raw = tds[0].get_text(" ", strip=True)
        sunset_raw = tds[1].get_text(" ", strip=True)
        daylight_raw = tds[2].get_text(" ", strip=True)
    else:
        if len(tds) < 4:
            print(" Not enough columns in row")
            return None
        sunrise_raw = tds[1].get_text(" ", strip=True)
        sunset_raw = tds[2].get_text(" ", strip=True)
        daylight_raw = tds[3].get_text(" ", strip=True)

    def _first_time(text):
        m = re.search(r"\d{1,2}:\d{2}", text)
        return m.group(0) if m else text.split(" ")[0]

    sunrise = _first_time(sunrise_raw)
    sunset = _first_time(sunset_raw)

    daylight_minutes = None
    # formats: "10:28:46" or "10 hours, 28 minutes"
    hm = re.match(r"(\d+):(\d+)", daylight_raw)
    if hm:
        daylight_minutes = int(hm.group(1)) * 60 + int(hm.group(2))
    else:
        m = re.search(r"(\d+)\s*hours?,?\s*(\d+)?", daylight_raw, re.I)
        if m:
            daylight_minutes = int(m.group(1)) * 60 + int(m.group(2) or 0)

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

    location_id = _location_id_from_url(base_url)
    if not location_id:
        print("Invalid base_url for TimeAndDate history")
        return None

    url = (
        f"https://www.timeanddate.com/scripts/cityajax.php?"
        f"n=@{location_id}&mode=historic&hd={day_str}&month={month}&year={year}&json=1"
    )

    print(f"Fetching TimeAndDate history from: {url}")
    raw_text = fetch_text(url)
    if not raw_text:
        return None

    try:
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
        except Exception:
            pass

        try:
            weather_text = html.unescape(cols[3].get("h", "")).lower()
            if "rain" in weather_text or "shower" in weather_text:
                precipitations.append(0.1)
        except Exception:
            pass

        try:
            wind_text = html.unescape(cols[4].get("h", "")).split(" ")[0].replace(",", ".")
            if wind_text:
                wind_speeds.append(float(wind_text))
        except Exception:
            pass

        try:
            hum_text = html.unescape(cols[6].get("h", "")).replace("%", "")
            if hum_text:
                humidities.append(float(hum_text))
        except Exception:
            pass

        try:
            pressure_text = html.unescape(cols[7].get("h", "")).replace("mbar", "").strip().replace(",", ".")
            if pressure_text:
                pressures.append(float(pressure_text))
        except Exception:
            pass

        try:
            vis_text = html.unescape(cols[8].get("h", "")).replace("km", "").strip().replace(",", ".")
            if vis_text:
                visibilities.append(float(vis_text))
        except Exception:
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
    today = str(dt_date.today())

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
            notes_l = (notes or "").lower()
            name_l = (prov_name or "").lower()

            if name_l == "arso" or "arso" in notes_l:
                result = scrape_arso_observed(target_date, base_url)
            elif "astronomy" in notes_l or "/astronomy/" in (base_url or ""):
                if target_date == today:
                    tad_id = _location_id_from_url(base_url) or "3203471"
                    result = scrape_astronomy_sunrise_sunset(tad_id)
                else:
                    sun_url = base_url.replace("/astronomy/", "/sun/") if base_url else None
                    if sun_url and "/sun/" in sun_url:
                        result = scrape_timeanddate_astronomy_history(target_date, sun_url)
                if not result:
                    result = astronomy_from_location(loc_id, target_date)
            elif "history" in notes_l:
                if "/sun/" in (base_url or ""):
                    result = scrape_timeanddate_astronomy_history(target_date, base_url)
                    if not result:
                        result = astronomy_from_location(loc_id, target_date)
                elif "/weather/" in (base_url or ""):
                    result = scrape_timeanddate_history(target_date, base_url)
                else:
                    print(" History provider URL not recognized.")
            else:
                print(" No matching scrape strategy found.")

            if result:
                print(" Result:", result)
                combined_data.update({k: v for k, v in result.items() if v is not None})

        if combined_data:
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

        cur.execute("""
            SELECT id, name, base_url, notes FROM weather_providers
            WHERE location_id = ? AND notes LIKE '%history%'
        """, (args.location_id,))
        providers = cur.fetchall()

        combined_data = {}

        for prov_id, prov_name, base_url, notes in providers:
            print(f"  Provider: {prov_name} — notes: {notes}")

            if "weather" in (base_url or ""):
                result = scrape_timeanddate_history(date_str, base_url)
            elif "sun" in (base_url or ""):
                result = scrape_timeanddate_astronomy_history(date_str, base_url)
                if not result:
                    result = astronomy_from_location(args.location_id, date_str)
            else:
                result = None

            if result:
                print(f"    ✔ Data scraped from {prov_name}")
                combined_data.update({k: v for k, v in result.items() if v is not None})

        if combined_data:
            combined_data["data_raw"] = json.dumps(combined_data, ensure_ascii=False)
            save_weather_observed(args.location_id, date_str, combined_data)
        else:
            print("  ❌ No data gathered for this day.")

        current += timedelta(days=1)

    conn.close()
