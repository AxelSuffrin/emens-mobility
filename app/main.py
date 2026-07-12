from fastapi import FastAPI, Query, HTTPException
from app.velib_client import fetch_stations, fetch_status, merge_station_data, find_nearest_station
from app.restaurant_client import fetch_restaurants, normalize_restaurants, find_nearest_restaurant
from fastapi.middleware.cors import CORSMiddleware
#from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse



app = FastAPI(
    title="eMens Mobility API",
    description="Real-time Vélib' station and restaurant lookup — eMens v0.1",
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



#app.mount("/static", StaticFiles(directory="."), name="static")



@app.get("/")
async def serve_frontend():
    return FileResponse("index.html")


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


@app.get("/restaurants/nearest")
def get_nearest_restaurant(
    lat: float = Query(..., description="Latitude of the user's position"),
    lon: float = Query(..., description="Longitude of the user's position")
):
    """
    Returns the nearest restaurant (OpenStreetMap data) and its
    available details for a given lat/lon coordinate.
    """
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