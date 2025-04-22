# logic/timeanddate.py

import requests
from bs4 import BeautifulSoup
import re

def scrape_astronomy_sunrise_sunset(location_url_id):
    url = f"https://www.timeanddate.com/astronomy/@{location_url_id}"
    print(f"Fetching astronomy data from: {url}")

    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    table = soup.select_one("table.table.left.table--inner-borders-rows")
    if not table:
        print("Table not found")
        return None

    result = {
        "sunrise": None,
        "sunset": None,
        "daylight_minutes": None
    }

    for row in table.find_all("tr"):
        header = row.find("th").text.strip()
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
    else:
        print("Could not find today's astronomy data")
        return None
