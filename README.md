# eMens Mobility v0.1

## Mission
eMens is the trusted layer between physical reality and the digital world for the human eye. It will enable native digital semantic that'll make interactions with AR world simpler.Today, at best, you get directions to a location. Tomorrow, you get information about locations around you in real time and can act upon it. 

## First user / Sample Scenario
A Paris cyclist looking for a Vélib' in the next 2 minutes.

## Physical entity
A Vélib' station.

## Trigger
The user is close to, or points their phone toward, a station (Tomorrow, looks towards the velib station).

## Digital context
Live mechanical-bike count, e-bike count, free docks, timestamp, source, and confidence.

## User action
Navigate to the station or see the nearest viable alternativ (Tomorrow, fetches subscription page to pay for a subscription in none are active. Means integrated authentication layer).

## Trust rule
Never imply live certainty without showing source and freshness.
If data is stale or unavailable, say so clearly.

## Date source
https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole

## Entity resolution logic
Using station_id parameters. Requires querying the user's current location and comparing it with nearest station_id. 

## Success criteria
User identifies live availability of the correct nearest station in under 5 seconds, 3/3 real-world tests

## Out-of-scope as-is
Comparison with other providers than just velib, offline mode, notifications...

## Tech Stack
Backend: Python + FastAPI
Data Fetching: Requests library
Storage: none, in memory (tomorrow, database that could be seen as user memory, similar to ai assistants)
Frontend: HTML + JavaScript fetch()
Hosting: Local
Version control: Github

## Non-goals
No AR glasses, contact lenses, computer vision, payments, ads, accounts, social layer,
or full Paris mapping in v0.1.