# main.py — API & Frontend Serving

## Purpose
Wraps velib_client.py's pipeline in a FastAPI app, and serves the static 
frontend (index.html) directly from the same server. One server, one port, 
one origin — no separate static file server needed.

## Endpoints

### GET /
Serves index.html directly via FileResponse. This is the entry point for 
the frontend — visiting the root URL in a browser loads the full UI.

### GET /stations/nearest?lat=<float>&lon=<float>
Runs the full pipeline on every request:
1. fetch_stations() + fetch_status() — pull live GBFS data
2. merge_station_data() — join into eMens entity schema
3. find_nearest_station() — resolve nearest station to given lat/lon

Returns a single flat JSON object (station fields + distance_meters at the 
top level — NOT nested under a "station" key). Example:

{
  "entity_id": "emens:mobility:velib:station:1559700274",
  "name": "Square Gilbert Thomain",
  "lat": 48.90717373809284,
  "lon": 2.2695400938391685,
  "state": { "mechanical_bikes": 6, "electric_bikes": 4, "free_docks": 10, "is_renting": true },
  "provenance": { "source": "velib_gbfs", "last_reported": 1783794213, "freshness_seconds": 2777, "confidence": "official_live" },
  "actions": ["navigate", "open_official_app"],
  "distance_meters": 127.4
}

Errors surface as HTTP 500 with the exception message in `detail`.

## CORS
Currently wide open (allow_origins=["*"], allow_credentials=False). 
This is intentional for local/ngrok testing convenience. 
MUST be tightened to specific origin(s) before any real deployment.

## Frontend (index.html)
Vanilla HTML/JS, no framework, no build step. Flow:
1. Button click triggers navigator.geolocation.getCurrentPosition()
2. On success, fetch("/stations/nearest?lat=...&lon=...") — relative path, 
   same-origin, no CORS complexity since FastAPI now serves this file too
3. Renders station name, distance, live bike/dock counts, and the 
   provenance/freshness block (source, last updated, confidence)

Note: fetch uses a relative path, not a full URL — this only works because 
main.py serves index.html from the same origin as the API. If frontend and 
backend are ever split onto different servers/ports again, this must 
change back to an absolute URL, and CORS origins must be updated accordingly.

## Outdoor / mobile testing setup (temporary, dev-only)
Geolocation requires a secure context (HTTPS) or localhost — plain HTTP 
over a LAN IP (e.g. http://192.168.x.x) silently blocks the geolocation 
prompt on most browsers, including mobile.

Workaround used: ngrok tunnel to expose the local server over HTTPS.

    uvicorn app.main:app --reload --host 0.0.0.0
    ngrok http 8000

Visit the ngrok HTTPS URL on any device (same or different network) — 
geolocation prompts correctly, and the full pipeline runs against real GPS.

Known ngrok free-tier constraints:
- Reserved domain is session/account-based, not freshly random each run
- Only one tunnel per URL at a time (ERR_NGROK_334 if you try to reuse 
  an already-online endpoint for a second tunnel)
- Tunnel URLs are ephemeral — expect to reconfigure if ngrok restarts

This setup is NOT a deployment strategy — it's a local dev testing shortcut. 
Revisit real hosting when ready for Day 7+ / actual deployment.

## Known debugging traps (learned the hard way tonight)
- Double-clicking index.html loads it as file://, which breaks both CORS 
  and geolocation. Always serve it through an actual HTTP server.
- "File not found" 404 from Python's http.server almost always means wrong 
  working directory when the server was launched — cd into the repo root first.
- Browser caching can mask fixes — hard refresh (Ctrl+Shift+R) before 
  assuming a code change didn't work.