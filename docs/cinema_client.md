# eMens Mobility — `cinema_client.py` Documentation

## Purpose

This module is the third eMens client, following `velib_client.py` (Vélib') 
and `restaurant_client.py` (restaurants). It fetches cinema data from 
OpenStreetMap's Overpass API and normalizes it into the same eMens entity 
schema, further confirming the schema generalizes across structurally 
different, community-mapped sources.

Where `restaurant_client.py` proved the schema survives a second source, 
`cinema_client.py` is the third data point — and the pattern holds with 
almost no new abstraction needed.

---

## What's Identical to `restaurant_client.py`

- Same three-step shape: **fetch → normalize → find nearest**
- Same Overpass POST pattern with the `around:` radius filter
- Same required `User-Agent` + `Referer` headers (still enforced by Overpass 
  as of 2026)
- `find_nearest_cinema()` is structurally identical to 
  `find_nearest_restaurant()` — same linear search, same 
  `(entity, distance)` return
- `haversine_distance()` imported from `velib_client.py`, not duplicated
- Missing OSM fields left as `None`, never faked or backfilled
- `provenance.source = "osm_overpass"`, `last_reported` / 
  `freshness_seconds` are `None` — no live-status equivalent exists for 
  either restaurants or cinemas

If a concept isn't listed below, assume it works exactly like the 
restaurant client.

---

## What's Different, and Why

### The OSM tag

```python
node["amenity"="cinema"](around:{radius_m},{lat},{lon});
```

Only the tag value changed — `restaurant` → `cinema`. The query structure, 
radius filter, and headers are unchanged.

### Larger default search radius

```python
def fetch_cinemas(lat, lon, radius_m=1000):
```

Restaurants default to 500m; cinemas default to **1000m**. Cinemas are far 
sparser per square kilometer than restaurants — a first live test at 
Châtelet returned only 13 cinemas within 1000m, versus 83 restaurants at 
half that radius. This is a judgment call based on observed density, not a 
proven optimal number — worth revisiting if outdoor testing shows too many 
or too few results in different areas.

### New state fields, specific to cinemas

```python
"state": {
    "operator": operator,       # Chain name, e.g. "Pathé", "UGC"
    "screens": screens,         # Screen count — string, not int (OSM tags 
                                 # are always strings)
    "wheelchair": wheelchair,   # "yes" / "no" / "limited"
    "address": address,
    "phone": phone,
    "website": website,
}
```

These map to OSM's standardized cinema tags (`operator`, `screen`, 
`wheelchair`). In practice, most of these are `None` for independent 
cinemas — chain cinemas are more likely to have `operator` filled in. 
Note `screens` comes back as a string (e.g. `"2"`), matching OSM's 
tag format; casting to int would be needed if this field is ever used 
for numeric filtering later.

### Confidence logic uses a different trigger

```python
confidence = "community_mapped"
if operator:
    confidence = "community_mapped_enriched"
```

Restaurants use `opening_hours` presence as the enrichment signal. 
Cinemas use `operator` presence instead — the reasoning is that a known 
chain (Pathé, UGC, Gaumont) is a stronger trust signal for a cinema than 
whether its hours happen to be tagged. This is a deliberate, source-specific 
choice: the *meaning* of "enriched" isn't fixed by the schema, it's decided 
per data source based on what actually indicates quality for that category.

### Entity namespace

```python
f"emens:leisure:cinema:{osm_id}"
```

New category prefix: `leisure`, distinct from `mobility` (Vélib') and 
`food` (restaurants). Confirms the `emens:<category>:<subtype>:<id>` 
pattern keeps generalizing cleanly to a third domain.

---

## The Result, in Practice

Running the module against Châtelet returned 13 cinemas within 1000m, with 
the nearest ("Luminor Hôtel de ville", 485m) returning a genuinely complete 
address and website, plus screen count and limited wheelchair access — 
richer data than the restaurant test case, showing OSM completeness varies 
significantly even within similar categories, not just across them.

A second live test near Saint-Denis correctly returned a 404 
("No cinemas found nearby") rather than crashing — confirming the 
empty-results edge case, first designed for restaurants but untested until 
now, works as intended for a genuinely sparse-data scenario.

---

## Known Debugging Trap (logged this session)

During initial testing, `/cinemas/nearest` returned a `500` error with the 
message `"No cinemas found nearby"` — which should only ever be a `404`. 
The code itself was correct (the `except HTTPException: raise` guard was 
in place). The actual cause was a **stale `uvicorn --reload` process** that 
hadn't fully picked up the latest edit to `main.py`. A full stop 
(Ctrl+C) and clean restart resolved it immediately.

Lesson: if a fix doesn't seem to take effect after editing a FastAPI route 
under `--reload`, restart the server fully before assuming the code is 
wrong.