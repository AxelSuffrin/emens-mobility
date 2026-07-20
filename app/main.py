from fastapi import FastAPI, Query, HTTPException
from app.velib_client import fetch_stations, fetch_status, merge_station_data, find_nearest_station
from app.restaurant_client import fetch_restaurants, normalize_restaurants, find_nearest_restaurant
from app.cinema_client import fetch_cinemas, normalize_cinemas, find_nearest_cinema
from app.gym_client import fetch_gyms, normalize_gyms, find_nearest_gym
from app.bar_client import fetch_bars, normalize_bars, find_nearest_bar
from fastapi.middleware.cors import CORSMiddleware
#from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse



app = FastAPI(
    title="eMens Mobility API",
    description="Real-time Vélib' station, restaurant, cinema, gym, and bar lookup — eMens v0.1",
    version="0.1.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://emens-mobility.onrender.com",
    ],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/")
async def serve_frontend():
    return FileResponse("index.html")


@app.get("/stations/nearest")
def get_nearest_station(
    lat: float = Query(..., description="Latitude of the user's position"),
    lon: float = Query(..., description="Longitude of the user's position")
):
    try:
        stations = fetch_stations()
        statuses = fetch_status()
        merged = merge_station_data(stations, statuses)
        station, distance = find_nearest_station(merged, lat, lon)
        station["distance_meters"] = round(distance, 1)
        return station
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/restaurants/nearest")
def get_nearest_restaurant(
    lat: float = Query(..., description="Latitude of the user's position"),
    lon: float = Query(..., description="Longitude of the user's position")
):
    try:
        elements = fetch_restaurants(lat, lon, radius_m=500)
        restaurants = normalize_restaurants(elements)
        if not restaurants:
            raise HTTPException(status_code=404, detail="No restaurants found nearby")
        restaurant, distance = find_nearest_restaurant(restaurants, lat, lon)
        restaurant["distance_meters"] = round(distance, 1)
        return restaurant
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cinemas/nearest")
def get_nearest_cinema(
    lat: float = Query(..., description="Latitude of the user's position"),
    lon: float = Query(..., description="Longitude of the user's position")
):
    try:
        elements = fetch_cinemas(lat, lon, radius_m=1000)
        cinemas = normalize_cinemas(elements)
        if not cinemas:
            raise HTTPException(status_code=404, detail="No cinemas found nearby")
        cinema, distance = find_nearest_cinema(cinemas, lat, lon)
        cinema["distance_meters"] = round(distance, 1)
        return cinema
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/gyms/nearest")
def get_nearest_gym(
    lat: float = Query(..., description="Latitude of the user's position"),
    lon: float = Query(..., description="Longitude of the user's position")
):
    try:
        elements = fetch_gyms(lat, lon, radius_m=1000)
        gyms = normalize_gyms(elements)
        if not gyms:
            raise HTTPException(status_code=404, detail="No gyms found nearby")
        gym, distance = find_nearest_gym(gyms, lat, lon)
        gym["distance_meters"] = round(distance, 1)
        return gym
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/bars/nearest")
def get_nearest_bar(
    lat: float = Query(..., description="Latitude of the user's position"),
    lon: float = Query(..., description="Longitude of the user's position")
):
    """
    Returns the nearest bar (OpenStreetMap data) and its
    available details for a given lat/lon coordinate.
    """
    try:
        elements = fetch_bars(lat, lon, radius_m=500)
        bars = normalize_bars(elements)
        if not bars:
            raise HTTPException(status_code=404, detail="No bars found nearby")
        bar, distance = find_nearest_bar(bars, lat, lon)
        bar["distance_meters"] = round(distance, 1)
        return bar
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))