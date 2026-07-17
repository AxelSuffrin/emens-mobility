import requests

from app.velib_client import haversine_distance

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def fetch_gyms(lat: float, lon: float, radius_m: int = 1000) -> list:
    """
    Query Overpass API for OSM nodes tagged leisure=fitness_centre
    within radius_m meters of (lat, lon).
    Note: amenity=gym is deprecated in OSM as of 2025 — leisure=fitness_centre
    is the current standard tag.
    """
    query = f"""
    [out:json][timeout:25];
    node["leisure"="fitness_centre"](around:{radius_m},{lat},{lon});
    out body;
    """
    headers = {
        "User-Agent": "eMens/0.1 (personal project; github.com/AxelSuffrin)",
        "Referer": "https://emens-mobility.onrender.com",
    }
    response = requests.post(
        OVERPASS_URL, data={"data": query}, headers=headers, timeout=30
    )
    response.raise_for_status()
    data = response.json()
    return data.get("elements", [])


def normalize_gyms(elements: list) -> list:
    """
    Normalize raw OSM elements into the eMens entity schema.
    Missing OSM fields are left as None — not backfilled.
    """
    normalized = []
    for el in elements:
        osm_id = el.get("id")
        tags = el.get("tags", {})
        lat = el.get("lat")
        lon = el.get("lon")

        if osm_id is None or lat is None or lon is None:
            continue

        name = tags.get("name")

        street = tags.get("addr:street")
        housenumber = tags.get("addr:housenumber")
        if street and housenumber:
            address = f"{housenumber} {street}"
        elif street:
            address = street
        else:
            address = None

        operator = tags.get("operator")            # Chain name, e.g. "Basic-Fit"
        opening_hours = tags.get("opening_hours")
        fee = tags.get("fee")                        # "yes"/"no", sometimes present
        website = tags.get("website")
        phone = tags.get("phone")

        # Confidence: known chain operator is the strongest trust signal,
        # same reasoning as cinema_client
        confidence = "community_mapped"
        if operator:
            confidence = "community_mapped_enriched"

        normalized.append({
            "entity_id": f"emens:leisure:gym:{osm_id}",
            "name": name,
            "lat": lat,
            "lon": lon,
            "state": {
                "operator": operator,
                "opening_hours": opening_hours,
                "fee": fee,
                "address": address,
                "phone": phone,
                "website": website,
            },
            "provenance": {
                "source": "osm_overpass",
                "last_reported": None,
                "freshness_seconds": None,
                "confidence": confidence,
            },
            "actions": ["navigate"],
        })
    return normalized


def find_nearest_gym(gyms: list, user_lat: float, user_lon: float):
    """
    Returns (nearest_gym, distance_meters) from a normalized list.
    Reuses haversine_distance from velib_client — no duplication.
    """
    nearest = None
    shortest_distance = None
    for g in gyms:
        distance = haversine_distance(user_lat, user_lon, g["lat"], g["lon"])
        if shortest_distance is None or distance < shortest_distance:
            shortest_distance = distance
            nearest = g
    return nearest, shortest_distance


if __name__ == "__main__":
    user_lat, user_lon = 48.8583, 2.3470
    elements = fetch_gyms(user_lat, user_lon, radius_m=1000)
    print(f"Raw OSM elements returned: {len(elements)}")
    gyms = normalize_gyms(elements)
    print(f"Normalized gyms: {len(gyms)}")
    nearest, distance = find_nearest_gym(gyms, user_lat, user_lon)
    if nearest:
        print(f"Nearest: {nearest['name']} ({distance:.0f}m)")
        print(nearest)
    else:
        print("No gyms found.")