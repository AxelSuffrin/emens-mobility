import requests
import time

from app.velib_client import haversine_distance

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def fetch_restaurants(lat: float, lon: float, radius_m: int = 500) -> list:
    query = f"""
    [out:json][timeout:25];
    node["amenity"="restaurant"](around:{radius_m},{lat},{lon});
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


def normalize_restaurants(elements: list) -> list:
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

        # Skip malformed entries missing core geometry
        if osm_id is None or lat is None or lon is None:
            continue

        name = tags.get("name")  # May be None — don't fake it

        # Build address string from parts if available, else None
        street = tags.get("addr:street")
        housenumber = tags.get("addr:housenumber")
        if street and housenumber:
            address = f"{housenumber} {street}"
        elif street:
            address = street
        else:
            address = None

        opening_hours = tags.get("opening_hours")  # Often missing in OSM
        cuisine = tags.get("cuisine")               # Community-filled, uneven

        # Confidence reflects OSM's community-mapped, non-live nature
        # "community_mapped" < "official_live" in the trust hierarchy
        confidence = "community_mapped"
        if opening_hours:
            # Slightly higher signal: someone bothered to fill hours
            confidence = "community_mapped_enriched"

        normalized.append({
            "entity_id": f"emens:food:restaurant:{osm_id}",
            "name": name,
            "lat": lat,
            "lon": lon,
            "state": {
                "cuisine": cuisine,
                "opening_hours": opening_hours,
                "address": address,
                "phone": tags.get("phone"),
                "website": tags.get("website"),
            },
            "provenance": {
                "source": "osm_overpass",
                "last_reported": None,   # OSM has no live status timestamp
                "freshness_seconds": None,
                "confidence": confidence,
            },
            "actions": ["navigate"],
        })
    return normalized


def find_nearest_restaurant(restaurants: list, user_lat: float, user_lon: float):
    """
    Returns (nearest_restaurant, distance_meters) from a normalized list.
    Reuses haversine_distance from velib_client — no duplication.
    """
    nearest = None
    shortest_distance = None
    for r in restaurants:
        distance = haversine_distance(user_lat, user_lon, r["lat"], r["lon"])
        if shortest_distance is None or distance < shortest_distance:
            shortest_distance = distance
            nearest = r
    return nearest, shortest_distance


if __name__ == "__main__":
    # Quick smoke test — Châtelet area, same reference point as velib_client
    user_lat, user_lon = 48.8583, 2.3470
    elements = fetch_restaurants(user_lat, user_lon, radius_m=300)
    print(f"Raw OSM elements returned: {len(elements)}")
    restaurants = normalize_restaurants(elements)
    print(f"Normalized restaurants: {len(restaurants)}")
    nearest, distance = find_nearest_restaurant(restaurants, user_lat, user_lon)
    if nearest:
        print(f"Nearest: {nearest['name']} ({distance:.0f}m)")
        print(nearest)
    else:
        print("No restaurants found.")