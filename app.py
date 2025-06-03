from flask import Flask, render_template, request
import requests
import pandas as pd
from datetime import datetime
import plotly.graph_objs as go
import plotly.io as pio
import time

from stations import STATION_MAPPING

app = Flask(__name__)
API_URL = "https://api.ffwc.gov.bd/data_load/seven-days-forecast-waterlevel-24-hours/"

# Build STATION_MAP using the correct key "dangerlevel"
STATION_MAP = {
    station['id']: {
        "name": station['name'],
        "danger_level": float(station.get('dangerlevel')) if station.get('dangerlevel') is not None else None
    }
    for station in STATION_MAPPING if 'id' in station and 'name' in station
}

ALLOWED_STATIONS = [
    "Jamalpur", "Durgapur", "Mymensingh", "B. Baria", "Habiganj", "Bhairabbazar",
    "Derai", "Khaliajuri", "Manu-RB", "Moulvibazar", "Narsingdi", "Sheola",
    "Sherpur-Sylhet", "Sunamganj", "Sylhet"
]

CACHE = {}
CACHE_TIMEOUT = 1800  # seconds (30 minutes)

def fetch_data():
    resp = requests.get(API_URL)
    resp.raise_for_status()
    json_body = resp.json()

    all_data = {}
    for id_str, date_dict in json_body.items():
        try:
            station_id = int(id_str)
        except ValueError:
            continue

        station_info = STATION_MAP.get(station_id)
        if not station_info:
            continue

        station_name = station_info["name"]
        danger_level = station_info.get("danger_level")

        if station_name not in ALLOWED_STATIONS:
            continue

        station_data = []
        for date_str, wl_value in date_dict.items():
            try:
                mm, dd, yyyy = map(int, date_str.split("-"))
                iso_date = datetime(yyyy, mm, dd).date().isoformat()
                if isinstance(wl_value, (int, float)):
                    station_data.append({
                        "date": iso_date,
                        "water_level": wl_value
                    })
            except:
                continue

        station_data.sort(key=lambda x: x["date"])
        # Find river name from STATION_MAPPING
        river = None
        for s in STATION_MAPPING:
            if s.get("name") == station_name:
                river = s.get("river")
                break

        all_data[station_name] = {
            "data": station_data,
            "danger_level": danger_level,
            "river": river
        }

    return all_data

def fetch_data_cached():
    now = time.time()
    if "data" in CACHE and now - CACHE["time"] < CACHE_TIMEOUT:
        return CACHE["data"]
    data = fetch_data()
    CACHE["data"] = data
    CACHE["time"] = now
    return data

@app.route("/", methods=["GET"])
def index():
    all_data = fetch_data_cached()
    current_date = datetime.now().strftime("%B %d, %Y")
    return render_template("index.html", station_data=all_data, current_date=current_date)
