from datetime import datetime, timedelta
from utils import patch_weather_observed
from logic.scrape import scrape_timeanddate_astronomy_history, scrape_timeanddate_history
from logic.sunmath import astronomy_from_location

from db import connect


def get_provider_base_url_sun(location_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT base_url FROM weather_providers WHERE location_id = ? AND notes LIKE ?",
        (location_id, "%history%")
    )
    rows = cur.fetchall()
    conn.close()
    for row in rows:
        if "/sun/" in row[0]:
            return row[0]
    return None


def get_provider_base_url_history(location_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT base_url FROM weather_providers WHERE location_id = ? AND notes LIKE ?",
        (location_id, "%history%")
    )
    rows = cur.fetchall()
    conn.close()
    for row in rows:
        if "/weather/" in row[0]:
            return row[0]
    return None


def patch_selected_fields(location_id: int, date_from: str, date_to: str):
    """
    Za obstoječe zapise PATCHA sunrise, sunset, daylight_minutes, pressure_hpa, wind_speed_avg.
    TimeAndDate napake ne zrušijo joba — uporabi lokalni sun fallback.
    """
    base_url_sun = get_provider_base_url_sun(location_id)
    base_url_history = get_provider_base_url_history(location_id)

    if not base_url_sun:
        print("⚠ Ni sun provider URL — uporabljam lokalni izračun za astronomijo.")
    if not base_url_history:
        print("⚠ Ni weather history provider URL — pressure/wind patch bo preskočen.")

    start = datetime.strptime(date_from, "%Y-%m-%d").date()
    end = datetime.strptime(date_to, "%Y-%m-%d").date()

    current = start
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")

        astronomy = None
        if base_url_sun:
            astronomy = scrape_timeanddate_astronomy_history(date_str, base_url_sun)
        if not astronomy:
            astronomy = astronomy_from_location(location_id, date_str)

        weather = None
        if base_url_history:
            weather = scrape_timeanddate_history(date_str, base_url_history)

        patch = {}

        if astronomy:
            if astronomy.get("sunrise") is not None:
                patch["sunrise"] = astronomy["sunrise"]
            if astronomy.get("sunset") is not None:
                patch["sunset"] = astronomy["sunset"]
            if astronomy.get("daylight_minutes") is not None:
                patch["daylight_minutes"] = astronomy["daylight_minutes"]

        if weather:
            if weather.get("pressure_hpa") is not None:
                patch["pressure_hpa"] = weather["pressure_hpa"]
            if weather.get("wind_speed_avg") is not None:
                patch["wind_speed_avg"] = weather["wind_speed_avg"]

        if patch:
            patch_weather_observed(location_id, date_str, patch)
        else:
            print(f"Ni novih podatkov za {date_str}")

        current += timedelta(days=1)
