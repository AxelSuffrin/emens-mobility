# eMens Mobility — `velib_client.py` Documentation

## Purpose

This module is the first working piece of **eMens**. It proves that eMens can take a real-world physical entity (a Vélib' station), fetch its live state from an external system, and resolve which one is relevant to a given user location.

Everything else in **eMens Mobility v0.1** builds on top of this file.

---

# Repository Context

```text
emens-mobility/
├── .venv/              ← virtual environment (never committed to git)
├── .gitignore          ← tells git to ignore .venv/, __pycache__/, .env
├── README.md
├── requirements.txt    ← pinned package versions (requests, fastapi, uvicorn)
├── app/
│   ├── __init__.py     ← marks 'app' as a Python package
│   ├── main.py         ← FastAPI entry point (next step, not built yet)
│   └── velib_client.py ← this file — fetches, merges, and resolves station data
└── docs/
    ├── emens-mobility-v0.1.md
    └── velib_client.md
```

---

# Why the Virtual Environment Matters

`.venv/` is a self-contained Python installation that lives only inside this project folder.

Without it, any package you install using `pip` would go into your global Python installation and could silently break other projects or scripts on your machine.

Activating it:

```powershell
.venv\Scripts\Activate.ps1
```

tells your terminal:

> Use this isolated Python installation and its packages instead of the system-wide one.

When active, your terminal prompt begins with:

```text
(.venv)
```

This is your confirmation that you're using the correct environment.

## `requirements.txt`

`requirements.txt` records the exact package versions used by the project.

To recreate the environment:

```bash
pip install -r requirements.txt
```

---

# Why `__init__.py` Matters

An empty `__init__.py` file tells Python that `app/` is a package rather than a folder of unrelated scripts.

This allows commands like:

```bash
python -m app.velib_client
```

Python treats `app` as an importable package and executes `velib_client.py` as a module.

This also enables `main.py` to import functions from `velib_client.py`.

---

# The Script, Function by Function

## Imports

```python
import requests
from math import radians, sin, cos, sqrt, atan2
```

### `requests`

A third-party HTTP library used for making API calls.

This is how the script communicates with the Vélib' servers.

### Math Functions

The imported functions are later used by the Haversine formula to calculate the real-world distance between two GPS coordinates.

---

# Constants: The Data Source

```python
STATIONS_URL = "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/station_information.json"

STATUS_URL = "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/station_status.json"
```

Vélib' Métropole exposes two GBFS feeds:

- **station_information**
  - Station name
  - Coordinates
  - Capacity
  - Station ID

- **station_status**
  - Live bike availability
  - Available docks
  - Rental status
  - Last update timestamp

Keeping the URLs as constants means they only need to be changed in one place if the API changes.

---

# `fetch_stations()`

```python
def fetch_stations():
    response = requests.get(STATIONS_URL, timeout=10)
    response.raise_for_status()
    return response.json()["data"]["stations"]
```

## What happens?

1. Sends an HTTP GET request.
2. Waits up to **10 seconds**.
3. Raises an exception if the server returned an error.
4. Converts the JSON into Python objects.
5. Returns the list of stations.

### Why `raise_for_status()`?

Instead of silently continuing after a 404 or 500 response, the script immediately fails with a useful error.

This is defensive programming.

---

# `fetch_status()`

```python
def fetch_status():
    response = requests.get(STATUS_URL, timeout=10)
    response.raise_for_status()
    return response.json()["data"]["stations"]
```

This function is structurally identical to `fetch_stations()`, except it retrieves the live station status feed.

It intentionally performs only one responsibility:

- Fetch
- Validate
- Return

No filtering or transformations occur here.

---

# `merge_station_data(stations, statuses)`

```python
def merge_station_data(stations, statuses):
    status_by_id = {s["station_id"]: s for s in statuses}
    merged = []

    for station in stations:
        status = status_by_id.get(station["station_id"])

        if status is None:
            continue

        merged.append({
            ...
        })

    return merged
```

This function performs the actual **entity resolution**.

It combines the static station information with the corresponding live status into a single, unified eMens entity.

## Dictionary Index

```python
status_by_id = {s["station_id"]: s for s in statuses}
```

Instead of searching through over 1,500 status objects every time, the code builds a dictionary keyed by station ID.

Lookup becomes:

```python
status_by_id[some_station_id]
```

instead of scanning the entire list.

This is a common performance optimization.

## Missing Status

```python
status = status_by_id.get(station["station_id"])
```

Using `.get()` returns `None` if the station doesn't exist rather than crashing.

```python
if status is None:
    continue
```

Stations missing live data are skipped.

## Output Entity

Each merged dictionary becomes the stable eMens entity:

- station ID
- name
- coordinates
- mechanical bikes
- electric bikes
- free docks
- timestamp
- rental status

This abstraction protects the rest of the application from future API changes.

---

# `haversine_distance()`

```python
def haversine_distance(lat1, lon1, lat2, lon2):
    ...
```

This calculates the real-world distance between two GPS coordinates.

## Why not subtract latitude and longitude?

Because the Earth is spherical.

One degree of longitude represents different distances depending on your latitude.

The Haversine formula accounts for Earth's curvature using trigonometry.

It is the standard approach used by:

- Google Maps
- Ride-sharing apps
- Delivery services
- Navigation software

---

# `find_nearest_station()`

```python
def find_nearest_station(
    merged_stations,
    user_lat,
    user_lon
):
```

This function performs a simple linear search.

For every station:

1. Compute the distance.
2. Compare it to the current shortest distance.
3. Replace the nearest station if closer.

Finally, it returns:

```python
(nearest_station, shortest_distance)
```

Since there are only about 1,500 stations, this approach is both simple and sufficiently fast.

---

# The `if __name__ == "__main__":` Block

```python
if __name__ == "__main__":
    stations = fetch_stations()
    statuses = fetch_status()

    merged = merge_station_data(
        stations,
        statuses
    )

    user_lat, user_lon = 48.8583, 2.3470

    nearest, distance = find_nearest_station(
        merged,
        user_lat,
        user_lon
    )

    print(f"Nearest station: {nearest['name']} ({distance:.0f}m away)")
    print(nearest)
```

This block only executes when the file is run directly:

```bash
python -m app.velib_client
```

It **does not execute** when the module is imported elsewhere.

This allows the file to contain both:

- reusable functions
- a standalone test program

The coordinates:

```text
48.8583, 2.3470
```

represent a test location near **Châtelet**.

Later, these values will come from a real user request instead of being hardcoded.

The formatting:

```python
{distance:.0f}
```

prints the distance as a whole number with no decimal places.