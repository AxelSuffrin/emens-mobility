import requests

from app.velib_client import haversine_distance

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def fetch_bars(lat: float, lon: float, radius_m: int = 500) -> list:
    """
    Query Overpass API for OSM nodes tagged amenity=bar
    within radius_m meters of (lat, lon).
    Note: amenity=music_venue is too narrow (dedicated concert halls only) —
    bars are more realistic for "going out tonight" use cases. live_music
    is captured as an honest, often-missing state field rather than filtered on.
    """
    query = f"""
    [out:json][timeout:25];
    node["amenity"="bar"](around:{radius_m},{lat},{lon});
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


def normalize_bars(elements: list) -> list:
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

        opening_hours = tags.get("opening_hours")
        live_music = tags.get("live_music")   # "yes"/"no", often missing entirely
        outdoor_seating = tags.get("outdoor_seating")
        website = tags.get("website")
        phone = tags.get("phone")

        # Confidence: live_music being tagged at all (yes or no) signals
        # someone bothered to describe the venue in detail
        confidence = "community_mapped"
        if live_music is not None:
            confidence = "community_mapped_enriched"

        normalized.append({
            "entity_id": f"emens:leisure:bar:{osm_id}",
            "name": name,
            "lat": lat,
            "lon": lon,
            "state": {
                "live_music": live_music,
                "opening_hours": opening_hours,
                "outdoor_seating": outdoor_seating,
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


def find_nearest_bar(bars: list, user_lat: float, user_lon: float):
    """
    Returns (nearest_bar, distance_meters) from a normalized list.
    Reuses haversine_distance from velib_client — no duplication.
    """
    nearest = None
    shortest_distance = None
    for b in bars:
        distance = haversine_distance(user_lat, user_lon, b["lat"], b["lon"])
        if shortest_distance is None or distance < shortest_distance:
            shortest_distance = distance
            nearest = b
    return nearest, shortest_distance


if __name__ == "__main__":
    user_lat, user_lon = 48.8583, 2.3470
    elements = fetch_bars(user_lat, user_lon, radius_m=500)
    print(f"Raw OSM elements returned: {len(elements)}")
    bars = normalize_bars(elements)
    print(f"Normalized bars: {len(bars)}")
    nearest, distance = find_nearest_bar(bars, user_lat, user_lon)
    if nearest:
        print(f"Nearest: {nearest['name']} ({distance:.0f}m)")
        print(nearest)
    else:
        print("No bars found.")