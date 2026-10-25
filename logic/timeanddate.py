# logic/timeanddate.py

import re
from bs4 import BeautifulSoup

from logic.http_client import fetch_text


def scrape_astronomy_sunrise_sunset(location_url_id):
    url = f"https://www.timeanddate.com/astronomy/@{location_url_id}"
    print(f"Fetching astronomy data from: {url}")

    html = fetch_text(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    table = soup.select_one("table.table.left.table--inner-borders-rows")
    if not table:
        # Fallback: newer page layout may only expose "Sunrise Today" text blocks
        text = soup.get_text(" ", strip=True)
        result = {"sunrise": None, "sunset": None, "daylight_minutes": None}
        m_rise = re.search(r"Sunrise Today:\s*(\d{1,2}:\d{2}\s*[ap]m)", text, re.I)
        m_set = re.search(r"Sunset Today:\s*(\d{1,2}:\d{2}\s*[ap]m)", text, re.I)
        if m_rise:
            result["sunrise"] = m_rise.group(1).split()[0]
        if m_set:
            result["sunset"] = m_set.group(1).split()[0]
        if result["sunrise"] and result["sunset"]:
            return result
        print("Table not found")
        return None

    result = {
        "sunrise": None,
        "sunset": None,
        "daylight_minutes": None
    }

    for row in table.find_all("tr"):
        th = row.find("th")
        if not th:
            continue
        header = th.text.strip()
        value_td = row.find("td")
        if not value_td:
            continue
        value_text = value_td.get_text(separator=" ").strip()

        if "Sunrise Today" in header:
            result["sunrise"] = value_text.split()[0]
        elif "Sunset Today" in header:
            result["sunset"] = value_text.split()[0]
        elif "Daylight Hours" in header:
            match = re.search(r"(\d+)\s*hours?,?\s*(\d+)?\s*minutes?", value_text)
            if match:
                hours = int(match.group(1))
                minutes = int(match.group(2) or 0)
                result["daylight_minutes"] = hours * 60 + minutes

    if result["sunrise"] and result["sunset"]:
        return result

    print("Could not find today's astronomy data")
    return None
