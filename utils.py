# utils.py

from db import connect

# All columns in table (except id)
ALL_FIELDS = [
    "location_id", "date",
    "temperature_min", "temperature_max", "temperature_avg",
    "precipitation_mm",
    "humidity_min", "humidity_max", "humidity_avg",
    "snow_depth_cm",
    "sunrise", "sunset", "daylight_minutes",
    "pressure_hpa", "wind_speed_avg", "visibility_km",
    "data_raw"
]


def save_weather_observed(location_id: int, date: str, data: dict):
    conn = connect()
    cur = conn.cursor()

    # Check if row exists
    cur.execute("""
        SELECT id FROM weather_observed
        WHERE location_id = ? AND date = ?
    """, (location_id, date))

    exists = cur.fetchone()

    if exists:
        # UPDATE only fields from data (non-None)
        fields_to_update = [k for k, v in data.items() if v is not None]
        if not fields_to_update:
            print(f"Nothing to update for location {location_id} on {date}")
            conn.close()
            return

        set_clause = ", ".join([f"{field} = ?" for field in fields_to_update])
        values = [data[field] for field in fields_to_update]

        cur.execute(f"""
            UPDATE weather_observed
            SET {set_clause}
            WHERE location_id = ? AND date = ?
        """, values + [location_id, date])

        print(f" Updated fields: {fields_to_update} for location {location_id} on {date}")

    else:
        # INSERT a full row, use 0 or None for missing fields
        full_data = {
            field: data.get(field, 0 if field.startswith("temperature") or field.endswith("_mm") or field.endswith(
                "_cm") else None)
            for field in ALL_FIELDS if field not in ("id")
        }

        full_data["location_id"] = location_id
        full_data["date"] = date

        columns = ", ".join(full_data.keys())
        placeholders = ", ".join(["?"] * len(full_data))
        values = list(full_data.values())

        cur.execute(f"""
            INSERT INTO weather_observed ({columns})
            VALUES ({placeholders})
        """, values)

        print(f" Inserted new record for location {location_id} on {date}")

    conn.commit()
    conn.close()


def patch_weather_observed(location_id: int, date: str, patch_data: dict):
    """
    Posodobi SAMO izbrane ključev (npr. sunrise, sunset, daylight_minutes) za dan/location.
    Ostalo naj pusti nedotaknjeno.
    """
    conn = connect()
    cur = conn.cursor()

    # Check če zapis obstaja
    cur.execute("""
        SELECT id FROM weather_observed
        WHERE location_id = ? AND date = ?
    """, (location_id, date))
    row = cur.fetchone()

    if not row:
        print(f"❌ Ne obstaja zapis za location {location_id} na {date} — nič za popravljat.")
        conn.close()
        return

    fields_to_update = [k for k, v in patch_data.items() if v is not None]
    if not fields_to_update:
        print(f"❌ Ni podatkov za patch za location {location_id} na {date}")
        conn.close()
        return

    set_clause = ", ".join([f"{field} = ?" for field in fields_to_update])
    values = [patch_data[field] for field in fields_to_update]

    cur.execute(f"""
        UPDATE weather_observed
        SET {set_clause}
        WHERE location_id = ? AND date = ?
    """, values + [location_id, date])

    print(f"🟢 Patchano: {fields_to_update} za location {location_id} na {date}")

    conn.commit()
    conn.close()
