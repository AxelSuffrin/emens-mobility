# eMens Mobility — `restaurant_client.py` Documentation

## Purpose

This module proves the eMens entity schema generalizes beyond Vélib'. It fetches restaurant data from OpenStreetMap's Overpass API and normalizes it into the same `entity_id` / `state` / `provenance` / `actions` shape already used for bike stations.

Where `velib_client.py` established the pattern, this file is the first real test of whether that pattern holds up against a structurally different, lower-quality data source.

---

## What's Identical to `velib_client.py`

- Overall three-step shape: **fetch → normalize → find nearest**
- `find_nearest_restaurant()` is structurally identical to `find_nearest_station()` — same linear search, same `(entity, distance)` return
- The `if __name__ == "__main__"` test block, same Châtelet test coordinates
- `timeout=` on all HTTP calls, `raise_for_status()` for defensive failure

If a concept isn't listed below, assume it works exactly like the Vélib' version.

---

## What's Different, and Why

### One fetch function instead of two

Vélib' has separate `stations` (static) and `status` (live) feeds that need merging by ID. Overpass returns everything — name, coordinates, tags — in a single response for a single query, so there's no `merge_station_data()` equivalent. `normalize_restaurants()` does the schema-mapping that `merge_station_data()` did, but without the join step.

```python
def fetch_restaurants(lat, lon, radius_m=500):
```

Also notice this takes `lat`, `lon`, `radius_m` as arguments. Vélib's fetch functions take nothing — they always pull the entire city's dataset, since there are only ~1,500 stations. Overpass would happily return every restaurant in Paris if asked, which is wasteful and slow, so we query a radius around the user directly instead of fetching-then-filtering.

### The Overpass query itself

```python
query = f"""
[out:json];
node["amenity"="restaurant"](around:{radius_m},{lat},{lon});
out body;
"""
```

This is Overpass's own query language (`Overpass QL`), sent as a POST body — not a URL with query parameters like Vélib's GET requests. `around:{radius_m},{lat},{lon}` is Overpass's built-in "give me nodes within this radius" filter, so no bounding-box math is needed on our side.

### Headers are required, and this matters

```python
headers = {
    "User-Agent": "eMens/0.1 (personal project; ...)",
    "Referer": "https://emens-mobility.onrender.com",
}
```

Vélib's GBFS feed accepts anonymous requests. Overpass, as of 2026, rejects requests without a proper `User-Agent` (406 error). This is a real-world signal about the difference between an official live API and community infrastructure — worth remembering if other free data sources are added later, since this class of failure will likely recur.

### `haversine_distance` is imported, not duplicated

```python
from app.velib_client import haversine_distance
```

Same formula, same reasoning as documented for Vélib' — Earth's curvature means degrees of longitude aren't constant-distance. The only change here is *where it lives*: rather than copy the function, `restaurant_client.py` imports it directly from `velib_client.py`, proving it's genuinely shared infrastructure rather than Vélib'-specific code. If a third data source needs it too, that's the trigger to move it into its own `app/utils.py`.

### `normalize_restaurants()` does not fake missing data

```python
name = tags.get("name")
opening_hours = tags.get("opening_hours")
```

Unlike Vélib's feed, where every field is always present, OSM data is community-edited and often incomplete. Rather than defaulting missing fields to `""` or `"Unknown"`, they're left as `None`. This is intentional — an eMens entity should honestly represent what it doesn't know, not manufacture false completeness.

### `provenance.confidence` is no longer a single fixed value

Vélib' always reports `"official_live"` — every station has fresh, authoritative status. Restaurants get one of two values:

```python
confidence = "community_mapped"
if opening_hours:
    confidence = "community_mapped_enriched"
```

This is the field actually doing its job for the first time: a restaurant with more complete tagging is marked as slightly more trustworthy than one with just a name and coordinates. There's also no live "last updated" equivalent, so `last_reported` and `freshness_seconds` are simply `None` — OSM tracks edit history, not real-time state, and pretending otherwise would misrepresent the source.

---

## The Result, in Practice

Running the module against Châtelet returned 83 restaurants, with the nearest ("Tao", 42m) missing address, phone, and hours — a realistic OSM result, not a bug. This is the expected shape of a `community_mapped` entity: real, usable, but visibly less complete than a Vélib' station entity.