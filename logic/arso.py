# logic/arso.py (debug row printer)

import requests
from bs4 import BeautifulSoup
from datetime import datetime

def scrape_arso_observed(target_date_str, base_url):
    from datetime import datetime
    import requests
    from bs4 import BeautifulSoup

    print(f"Fetching ARSO data from: {base_url}")

    date_obj = datetime.strptime(target_date_str, "%Y-%m-%d")
    date_for_match = f"{date_obj.day:02d}.{date_obj.month:02d}.{date_obj.year}"

    try:
        resp = requests.get(base_url)
        resp.raise_for_status()
    except Exception as e:
        print("Failed to fetch ARSO data:", e)
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table")
    if not table:
        print("Table not found.")
        return None

    temperatures = []
    humidities = []
    precipitation_total = 0.0
    snow_depth_values = []

    for row in table.find_all("tr"):
        date_cell = row.find("td", class_="meteoSI-th")
        if not date_cell:
            continue

        full_text = date_cell.text.strip()
        if date_for_match not in full_text:
            continue

        # temp
        temp_cell = next((td for td in row.find_all("td", class_="t") if "display:none" not in td.get("style", "")), None)
        hum_cell = next((td for td in row.find_all("td", class_="rh") if "display:none" not in td.get("style", "")), None)
        precip_cell = next((td for td in row.find_all("td", class_="rr_val") if "display:none" not in td.get("style", "")), None)
        snow_cell = next((td for td in row.find_all("td", class_="snow") if "display:none" not in td.get("style", "")), None)

        try:
            if temp_cell:
                temperatures.append(float(temp_cell.text.strip().replace(",", ".")))
            if hum_cell:
                humidities.append(float(hum_cell.text.strip().replace(",", ".")))
            if precip_cell:
                precipitation_total += float(precip_cell.text.strip().replace(",", "."))
            if snow_cell:
                value = snow_cell.text.strip().replace(",", ".")
                if value not in ["...", "-", ""]:
                    snow_depth_values.append(float(value))
        except ValueError:
            continue

    if not temperatures or not humidities:
        print("No valid data for that date.")
        return None

    result = {
        "temperature_min": min(temperatures),
        "temperature_max": max(temperatures),
        "temperature_avg": round(sum(temperatures) / len(temperatures), 2),
        "humidity_min": min(humidities),
        "humidity_max": max(humidities),
        "humidity_avg": round(sum(humidities) / len(humidities), 2),
        "precipitation_mm": round(precipitation_total, 2),
        "snow_depth_cm": snow_depth_values[-1] if snow_depth_values else None
    }

    return result
