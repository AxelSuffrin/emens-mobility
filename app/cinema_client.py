import requests

from app.velib_client import haversine_distance

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def fetch_cinemas(lat: float, lon: float, radius_m: int = 1000) -> list:
    """
    Query Overpass API for OSM nodes tagged amenity=cinema
    within radius_m meters of (lat, lon).
    Returns raw OSM elements (list of dicts).
    """
    query = f"""
    [out:json][timeout:25];
    node["amenity"="cinema"](around:{radius_m},{lat},{lon});
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


def normalize_cinemas(elements: list) -> list:
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

        operator = tags.get("operator")          # Chain name, e.g. "Pathé"
        screens = tags.get("screen")               # Rarely tagged
        wheelchair = tags.get("wheelchair")        # "yes"/"no"/"limited", often missing
        website = tags.get("website")
        phone = tags.get("phone")

        # Confidence: a known chain operator is a stronger trust signal
        # than an untagged independent cinema
        confidence = "community_mapped"
        if operator:
            confidence = "community_mapped_enriched"

        normalized.append({
            "entity_id": f"emens:leisure:cinema:{osm_id}",
            "name": name,
            "lat": lat,
            "lon": lon,
            "state": {
                "operator": operator,
                "screens": screens,
                "wheelchair": wheelchair,
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


def find_nearest_cinema(cinemas: list, user_lat: float, user_lon: float):
    """
    Returns (nearest_cinema, distance_meters) from a normalized list.
    Reuses haversine_distance from velib_client — no duplication.
    """
    nearest = None
    shortest_distance = None
    for c in cinemas:
        distance = haversine_distance(user_lat, user_lon, c["lat"], c["lon"])
        if shortest_distance is None or distance < shortest_distance:
            shortest_distance = distance
            nearest = c
    return nearest, shortest_distance


if __name__ == "__main__":
    user_lat, user_lon = 48.8583, 2.3470
    elements = fetch_cinemas(user_lat, user_lon, radius_m=1000)
    print(f"Raw OSM elements returned: {len(elements)}")
    cinemas = normalize_cinemas(elements)
    print(f"Normalized cinemas: {len(cinemas)}")
    nearest, distance = find_nearest_cinema(cinemas, user_lat, user_lon)
    if nearest:
        print(f"Nearest: {nearest['name']} ({distance:.0f}m)")
        print(nearest)
    else:
        print("No cinemas found.")