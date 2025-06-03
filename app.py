from flask import Flask, render_template, request
import requests
import pandas as pd
from datetime import datetime
import plotly.graph_objs as go
import plotly.io as pio

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
        all_data[station_name] = {
            "data": station_data,
            "danger_level": danger_level
        }

    return all_data

@app.route("/", methods=["GET"])
def index():
    all_data = fetch_data()

    station_plots = []
    for station_name, station_info in all_data.items():
        data = station_info["data"]
        danger_level = station_info["danger_level"]
        plot_html = None

        if data:
            df = pd.DataFrame(data)
            df["date"] = pd.to_datetime(df["date"])

            # Find y_max for shading
            y_max = max(df["water_level"].max(), danger_level if danger_level is not None else float('-inf'))
            show_shading = danger_level is not None and y_max > danger_level

            traces = [
                go.Scatter(
                    x=df["date"],
                    y=df["water_level"],
                    mode="lines+markers",
                    name="Water Level",
                    marker=dict(size=8),
                    hovertemplate="Date: %{x|%Y-%m-%d}<br>Level: %{y:.2f} m<extra></extra>"
                )
            ]

            # Add danger level line
            if danger_level is not None:
                traces.append(
                    go.Scatter(
                        x=df["date"],
                        y=[danger_level]*len(df),
                        mode="lines",
                        name="Danger Level",
                        line=dict(color="orange", dash="dash")
                    )
                )

            # Add shading above danger level if needed
            if show_shading:
                traces.append(
                    go.Scatter(
                        x=pd.concat([df["date"], df["date"][::-1]]),
                        y=pd.concat([
                            pd.Series([y_max]*len(df)),
                            pd.Series([danger_level]*len(df))[::-1]
                        ]),
                        fill="toself",
                        fillcolor="rgba(255,165,0,0.15)",  # light transparent orange
                        line=dict(color="rgba(255,255,255,0)"),
                        hoverinfo="skip",
                        showlegend=False,
                        name="Above Danger Level"
                    )
                )

            layout = go.Layout(
                title=f"Water Level Data for {station_name}",
                xaxis_title="Date",
                yaxis_title="Water Level (m)",
                legend_title="Legend",
                hovermode="x unified",
                margin=dict(l=40, r=40, t=40, b=40),
                height=500
            )
            fig = go.Figure(data=traces, layout=layout)
            plot_html = pio.to_html(fig, full_html=False)

        station_plots.append({
            "name": station_name,
            "plot": plot_html,
            "danger_level": danger_level
        })

    return render_template("index.html", station_plots=station_plots)

if __name__ == "__main__":
    app.run()
