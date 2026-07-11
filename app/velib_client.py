import requests
from math import radians, sin, cos, sqrt, atan2


STATIONS_URL = "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/station_information.json"
STATUS_URL = "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/station_status.json"

def fetch_stations():
    response = requests.get(STATIONS_URL, timeout=10)
    response.raise_for_status()
    return response.json()["data"]["stations"]

def fetch_status():
    response = requests.get(STATUS_URL, timeout=10)
    response.raise_for_status()
    return response.json()["data"]["stations"]

def merge_station_data(stations, statuses):
    status_by_id = {s["station_id"]: s for s in statuses}
    merged = []
    for station in stations:
        status = status_by_id.get(station["station_id"])
        if status is None:
            continue
        merged.append({
            "station_id": station["station_id"],
            "name": station["name"],
            "lat": station["lat"],
            "lon": station["lon"],
            "mechanical_bikes": status["num_bikes_available_types"][0].get("mechanical", 0),
            "electric_bikes": status["num_bikes_available_types"][1].get("ebike", 0),
            "free_docks": status["num_docks_available"],
            "last_reported": status["last_reported"],
            "is_renting": status["is_renting"] == 1,
        })
    return merged

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))

def find_nearest_station(merged_stations, user_lat, user_lon):
    nearest = None
    shortest_distance = None
    for station in merged_stations:
        distance = haversine_distance(user_lat, user_lon, station["lat"], station["lon"])
        if shortest_distance is None or distance < shortest_distance:
            shortest_distance = distance
            nearest = station
    return nearest, shortest_distance

if __name__ == "__main__":
    stations = fetch_stations()
    statuses = fetch_status()
    merged = merge_station_data(stations, statuses)

    # Example: somewhere in central Paris (Châtelet area)
    user_lat, user_lon = 48.8583, 2.3470
    nearest, distance = find_nearest_station(merged, user_lat, user_lon)
    print(f"Nearest station: {nearest['name']} ({distance:.0f}m away)")
    print(nearest)