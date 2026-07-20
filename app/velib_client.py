import requests
import time
from math import radians, degrees, sin, cos, sqrt, atan2


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


def parse_bike_types(num_bikes_available_types):
    mechanical = 0
    ebike = 0

    if not isinstance(num_bikes_available_types, list):
        return mechanical, ebike

    for item in num_bikes_available_types:
        if not isinstance(item, dict):
            continue
        if "mechanical" in item and isinstance(item["mechanical"], int):
            mechanical += item["mechanical"]
        if "ebike" in item and isinstance(item["ebike"], int):
            ebike += item["ebike"]

    return mechanical, ebike


def merge_station_data(stations, statuses):
    status_by_id = {s["station_id"]: s for s in statuses}
    merged = []
    for station in stations:
        status = status_by_id.get(station["station_id"])
        if status is None:
            continue
        freshness_seconds = int(time.time()) - status["last_reported"]

        mechanical_bikes, electric_bikes = parse_bike_types(
            status.get("num_bikes_available_types", [])
        )

        merged.append({
            "entity_id": f"emens:mobility:velib:station:{station['station_id']}",
            "name": station["name"],
            "lat": station["lat"],
            "lon": station["lon"],
            "state": {
                "mechanical_bikes": mechanical_bikes,
                "electric_bikes": electric_bikes,
                "free_docks": status["num_docks_available"],
                "is_renting": status["is_renting"] == 1,
            },
            "provenance": {
                "source": "velib_gbfs",
                "last_reported": status["last_reported"],
                "freshness_seconds": freshness_seconds,
                "confidence": "official_live",
            },
            "actions": ["navigate", "open_official_app"],
        })
    return merged


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))


def calculate_bearing(lat1, lon1, lat2, lon2):
    """
    Returns compass bearing (0-360 degrees) from point 1 to point 2.
    0 = North, 90 = East, 180 = South, 270 = West.
    """
    phi1, phi2 = radians(lat1), radians(lat2)
    dlambda = radians(lon2 - lon1)
    y = sin(dlambda) * cos(phi2)
    x = cos(phi1) * sin(phi2) - sin(phi1) * cos(phi2) * cos(dlambda)
    theta = atan2(y, x)
    return (degrees(theta) + 360) % 360


def is_in_cone(bearing_to_target, user_heading, fov_deg=60):
    """
    Returns True if bearing_to_target falls within +/- fov_deg/2
    of user_heading (the direction the user is currently facing).
    """
    diff = abs((bearing_to_target - user_heading + 180) % 360 - 180)
    return diff <= fov_deg / 2


def find_nearest_station(merged_stations, user_lat, user_lon):
    """
    Returns (nearest_station, distance_meters) — single closest match,
    ignoring direction. Kept for backward compatibility with existing
    /stations/nearest endpoint behavior.
    """
    nearest = None
    shortest_distance = None
    for station in merged_stations:
        distance = haversine_distance(user_lat, user_lon, station["lat"], station["lon"])
        if shortest_distance is None or distance < shortest_distance:
            shortest_distance = distance
            nearest = station
    return nearest, shortest_distance


def find_stations_in_cone(merged_stations, user_lat, user_lon, user_heading, fov_deg=60, max_results=5):
    """
    Returns a ranked list of (station, distance_meters, bearing_deg) tuples
    for stations falling within the user's field-of-view cone, sorted by
    distance ascending. This is the gaze-aware alternative to
    find_nearest_station — it returns everything relevant in view rather
    than a single absolute-nearest winner.
    """
    candidates = []
    for station in merged_stations:
        distance = haversine_distance(user_lat, user_lon, station["lat"], station["lon"])
        bearing = calculate_bearing(user_lat, user_lon, station["lat"], station["lon"])
        if is_in_cone(bearing, user_heading, fov_deg):
            candidates.append((station, distance, bearing))
    candidates.sort(key=lambda c: c[1])
    return candidates[:max_results]


if __name__ == "__main__":
    stations = fetch_stations()
    statuses = fetch_status()
    merged = merge_station_data(stations, statuses)

    user_lat, user_lon = 48.8583, 2.3470

    nearest, distance = find_nearest_station(merged, user_lat, user_lon)
    print(f"Nearest station (no direction): {nearest['name']} ({distance:.0f}m away)")
    print(nearest)

    print()

    user_heading = 270  # facing west
    in_cone = find_stations_in_cone(merged, user_lat, user_lon, user_heading, fov_deg=60, max_results=5)
    print(f"Stations in cone (heading={user_heading} deg, fov=60 deg):")
    for station, dist, bearing in in_cone:
        print(f"  {station['name']} — {dist:.0f}m away, bearing {bearing:.0f} deg")
