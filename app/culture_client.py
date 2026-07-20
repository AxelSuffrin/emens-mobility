import requests

from app.velib_client import haversine_distance

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Historic site types worth surfacing — castle/fort/monument/ruins/archaeological_site are
# the most recognizable "worth visiting" categories; excludes minor/ambiguous
# tags like historic=building (too broad, low signal)
HISTORIC_VALUES = ["castle", "fort", "monument","ruins", "archaeological_site"]

def fetch_culture_sites(lat: float, lon: float, radius_m: int = 1500) -> list:
    """
    Query Overpass API for OSM nodes/ways tagged tourism=museum OR
    historic=<castle|fort|monument|ruins|archaeological_site>
    within radius_m meters of (lat, lon).

    Two distinct OSM key families in one query (tourism, historic) —
    broader schema test than a single-tag client. Union achieved via
    Overpass QL's multiple statements + union block.
    """
    historic_filter = "|".join(HISTORIC_VALUES)
    query = f"""
    [out:json][timeout:40];
    (
      node["tourism"="museum"](around:{radius_m},{lat},{lon});
      node["historic"~"^({historic_filter})$"](around:{radius_m},{lat},{lon});
    );
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


def normalize_culture_sites(elements: list) -> list:
    """
    Normalize raw OSM elements into the eMens entity schema.
    Missing OSM fields are left as None — not backfilled.
    state.category distinguishes museum vs. which historic subtype.
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
        if not name:
            # Skip unnamed culture sites — not useful for end users
            continue

        # Determine category: museum takes precedence if both somehow present
        if tags.get("tourism") == "museum":
            category = "museum"
        elif tags.get("historic") in HISTORIC_VALUES:
            category = tags.get("historic")
        else:
            category = "unknown"

        street = tags.get("addr:street")
        housenumber = tags.get("addr:housenumber")
        if street and housenumber:
            address = f"{housenumber} {street}"
        elif street:
            address = street
        else:
            address = None

        opening_hours = tags.get("opening_hours")
        fee = tags.get("fee")
        wheelchair = tags.get("wheelchair")
        website = tags.get("website")
        phone = tags.get("phone")

        # Confidence: opening_hours presence is the strongest trust signal
        # here — museums/historic sites vary wildly in how well they're
        # tagged, hours being filled in usually means a maintained entry
        confidence = "community_mapped"
        if opening_hours:
            confidence = "community_mapped_enriched"

        normalized.append({
            "entity_id": f"emens:culture:{category}:{osm_id}",
            "name": name,
            "lat": lat,
            "lon": lon,
            "state": {
                "category": category,
                "opening_hours": opening_hours,
                "fee": fee,
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


def find_nearest_culture_site(sites: list, user_lat: float, user_lon: float):
    """
    Returns (nearest_site, distance_meters) from a normalized list.
    Reuses haversine_distance from velib_client — no duplication.
    """
    nearest = None
    shortest_distance = None
    for s in sites:
        distance = haversine_distance(user_lat, user_lon, s["lat"], s["lon"])
        if shortest_distance is None or distance < shortest_distance:
            shortest_distance = distance
            nearest = s
    return nearest, shortest_distance


if __name__ == "__main__":
    user_lat, user_lon = 48.8583, 2.3470
    elements = fetch_culture_sites(user_lat, user_lon, radius_m=1500)
    print(f"Raw OSM elements returned: {len(elements)}")
    sites = normalize_culture_sites(elements)
    print(f"Normalized sites: {len(sites)}")
    nearest, distance = find_nearest_culture_site(sites, user_lat, user_lon)
    if nearest:
        print(f"Nearest: {nearest['name']} ({distance:.0f}m) — category: {nearest['state']['category']}")
        print(nearest)
    else:
        print("No culture sites found.")