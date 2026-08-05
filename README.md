# Movie Recommendation Engine

FastAPI service that parses natural-language movie requests, searches providers, and ranks available seat groups. Shaw is the live provider. GV is deliberately an adapter placeholder until a supported integration is added.

## Run

```powershell
.\venv\Scripts\python -m uvicorn serve:app --reload
```

Open `http://127.0.0.1:8000/docs`, or call:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/parse -ContentType 'application/json' -Body '{"query":"/movie fantastic four tomorrow after 7pm for 2 people"}'
```

## Test

```powershell
.\venv\Scripts\python -m pytest
```

The legacy `movies.py` prototype remains untouched.

## Caching

The API uses in-memory TTL caches: movie catalogues (1 hour), search results and
ticket prices (5 minutes), and seat layouts (30 seconds).
