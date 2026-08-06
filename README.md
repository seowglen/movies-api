# Movie Recommendation Engine

FastAPI service that parses natural-language movie requests, searches providers, and ranks available seat groups. Shaw is the live provider. GV is deliberately an adapter placeholder until a supported integration is added.

## Run

```powershell
.\venv\Scripts\python -m uvicorn serve:app --reload
```

Open `http://127.0.0.1:8000/docs`, or call:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/search -ContentType 'application/json' -Body '{"title":"spiderman","startTimeUTC":"2026-08-07T11:00:00Z","endTimeUTC":"2026-08-07T15:00:00Z","paxCount":4,"location":"ORCHARD","experience":"IMAX"}'
```

`startTimeUTC` is required and `endTimeUTC` is optional. If the window spans
multiple dates, each Singapore-local date is searched and the results are
merged. Set `location` to `null` to search all cinemas. Supported locations
and experiences are validated before provider calls.

## Test

```powershell
.\venv\Scripts\python -m pytest
```

The legacy `movies.py` prototype remains untouched.

## Caching

The API uses in-memory TTL caches: movie catalogues (1 hour), search results
(5 minutes), GV seat plans (30 seconds), and seat layouts (30 seconds). Ticket
prices are represented by a local adult baseline matrix and do not call provider
price APIs.
