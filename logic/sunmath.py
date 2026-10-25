# logic/sunmath.py — local sunrise/sunset fallback (NOAA-style)

import math
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Europe/Ljubljana")


def _sin(deg):
    return math.sin(math.radians(deg))


def _cos(deg):
    return math.cos(math.radians(deg))


def _asin(x):
    return math.degrees(math.asin(max(-1.0, min(1.0, x))))


def _acos(x):
    return math.degrees(math.acos(max(-1.0, min(1.0, x))))


def sunrise_sunset(lat: float, lon: float, day: date):
    """
    Return sunrise/sunset as HH:MM in Europe/Ljubljana and daylight_minutes.
    Uses solar elevation -0.833° (refraction + disk).
    """
    a = (14 - day.month) // 12
    y = day.year + 4800 - a
    m = day.month + 12 * a - 3
    jd = day.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    n = jd - 2451545.0 + 0.0008

    j_star = n - lon / 360.0
    m_anom = (357.5291 + 0.98560028 * j_star) % 360
    c = 1.9148 * _sin(m_anom) + 0.0200 * _sin(2 * m_anom) + 0.0003 * _sin(3 * m_anom)
    lam = (m_anom + c + 180 + 102.9372) % 360
    j_transit = 2451545.0 + j_star + 0.0053 * _sin(m_anom) - 0.0069 * _sin(2 * lam)

    delta = _asin(_sin(lam) * _sin(23.4397))
    cos_omega = (_sin(-0.833) - _sin(lat) * _sin(delta)) / (_cos(lat) * _cos(delta))
    if cos_omega < -1 or cos_omega > 1:
        return None

    omega = _acos(cos_omega)
    j_rise = j_transit - omega / 360.0
    j_set = j_transit + omega / 360.0

    def jd_to_local(j):
        days = j - 2440587.5
        utc = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(days=days)
        return utc.astimezone(LOCAL_TZ)

    rise_dt = jd_to_local(j_rise)
    set_dt = jd_to_local(j_set)
    daylight = int((set_dt - rise_dt).total_seconds() // 60)

    return {
        "sunrise": rise_dt.strftime("%H:%M"),
        "sunset": set_dt.strftime("%H:%M"),
        "daylight_minutes": daylight,
    }


def astronomy_from_location(location_id: int, date_str: str):
    """Load lat/lon for location and compute sunrise/sunset."""
    from db import connect

    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT lat, lon, name FROM locations WHERE id = ?", (location_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        print(f"No location {location_id} for sun fallback")
        return None

    lat, lon, name = row
    day = datetime.strptime(date_str, "%Y-%m-%d").date()
    result = sunrise_sunset(float(lat), float(lon), day)
    if result:
        print(f"Sun fallback for {name} on {date_str}: {result}")
    return result
