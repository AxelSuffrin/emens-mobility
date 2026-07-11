from fastapi import FastAPI, Query, HTTPException
from app.velib_client import fetch_stations, fetch_status, merge_station_data, find_nearest_station

app = FastAPI(
    title="eMens Mobility API",
    description="Real-time Vélib' station lookup — eMens v0.1",
    version="0.1.0"
)

@app.get("/stations/nearest")
def get_nearest_station(
    lat: float = Query(..., description="Latitude of the user's position"),
    lon: float = Query(..., description="Longitude of the user's position")
):
    """
    Returns the nearest Vélib' station and its live status
    for a given lat/lon coordinate.
    """
    try:
        stations = fetch_stations()
        statuses = fetch_status()
        merged = merge_station_data(stations, statuses)
        station, distance = find_nearest_station(merged, lat, lon)
        station["distance_meters"] = round(distance, 1)
        return station
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))