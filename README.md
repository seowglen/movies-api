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

## Architecture

The search API accepts a structured request and does not parse natural language.
`POST /search` creates a job and returns immediately. The frontend polls
`GET /search/{jobId}` while provider workers fetch seat layouts.

```mermaid
flowchart TD
    Client[Frontend] -->|POST /search| API[FastAPI API]
    API --> Job[Search Job Manager]
    API -->|jobId immediately| Client
    Job --> Catalog[Catalog and showtime caches]
    Job --> Select[Filter and select up to 20 candidates]
    Select --> GVQ[GV seat queue]
    Select --> ShawQ[Shaw seat queue]
    GVQ --> GV[GV worker: serial and jittered]
    ShawQ --> Shaw[Shaw worker: independent]
    GV --> Seats[Seat-layout cache]
    Shaw --> Seats
    Seats --> Rank[Recommendation and baseline pricing]
    Rank --> Job
    Client -->|GET /search/{jobId}| API
    API --> Client
```

Plain-text flow:

```text
Frontend -> POST /search -> jobId
                 |
                 v
        Search Job Manager
          |            |
       GV queue     Shaw queue
       (serial)    (independent)
          |            |
       Seat cache and recommendation
                 |
                 v
Frontend <- GET /search/{jobId} <- partial/final results
```

`POST /search` returns HTTP `202` immediately:

```json
{
  "jobId": "...",
  "status": "QUEUED",
  "phase": "QUEUED",
  "completed": 0,
  "total": 0,
  "screenings": []
}
```

Poll the result with:

```text
GET /search/{jobId}
```

While seat layouts are being fetched, candidate screenings are returned with
`seatStatus: "LOADING"`. Completed candidates use `READY`; provider failures
use `FAILED`. Stop polling when the job status is `COMPLETED`, `PARTIAL`, or
`FAILED`.

Each provider resolves the title against its own catalog. Provider-specific
movie titles are never returned to the parser or shared between providers.

The response exposes only public screening data. Provider cinema IDs and
distance calculations remain internal implementation details.

Job statuses are `QUEUED`, `PROCESSING`, `COMPLETED`, `PARTIAL`, and `FAILED`.
Screenings expose `seatStatus` as `LOADING`, `READY`, or `FAILED` so clients
can render partial results while workers are still running.

## Seat Layout

Each screening includes an optional `seatLayout` array:

```json
{
  "seatLayout": [
    {
      "row": "H",
      "seats": [
        {"number": 24, "status": "AVAILABLE"},
        {"number": 23, "status": "OCCUPIED"},
        {"number": 22, "status": "UNKNOWN"}
      ]
    }
  ]
}
```

Status values are:

- `AVAILABLE`: a valid seat currently available for selection.
- `OCCUPIED`: a valid seat currently occupied or unavailable.
- `NOT_A_SEAT`: the position is outside the provider's valid-seat set.
- `UNKNOWN`: a valid seat whose provider status was not classified.

For GV, a seat is marked `AVAILABLE` only when both `status` is `L` and
`type` is `N`. Other seat types, including reserved wheelchair seats, are
treated as unavailable for general recommendations.

Every row contains seat numbers from `1` through the maximum seat number
observed for that screening. The rows and seats are already ordered for visual rendering:

- GV: rows from the lowest letter to the highest, seats from low to high.
- Shaw: rows from the highest letter to the lowest, seats from high to low.

The frontend can render the arrays directly without knowing provider-specific
orientation rules. `recommendedSeats` and `seatQuality` identify the backend's
best adjacent group.

## Recommendation Algorithm

The backend first selects up to 20 bounded candidates, then
fetches seat layouts and removes screenings without a valid adjacent seat
group. The final response contains the successful candidates in their
selected chronological/distance order. The frontend can apply preference
filters and ranking.

Seat scoring uses:

- 60% horizontal center position.
- 40% row position.
- A dynamic buffer-seat component, up to 20% in low-occupancy rooms and 0%
  when the room is more than 70% occupied.
- Experience-specific ideal row targets, such as IMAX at 55% depth,
  Standard at 66%, and Gold Class at 75%.
- Experience-specific penalties for the first three rows. IMAX and GVMAX
  are penalized more heavily, while premium recliner formats are penalized
  less.

Baseline pricing is calculated locally from the provider, experience,
Singapore calendar day, and public-holiday matrix. It is returned as
`baselinePrice` and is an indicative adult price, not a guaranteed checkout
price.

## Caching

The API uses in-memory TTL caches: movie catalogues and provider showtimes
(1 hour), and processed seat layouts with dynamic TTLs. Seat layouts are
cached for 30 seconds when a show starts within 2 hours, 3 minutes when it
starts within 24 hours, and 15 minutes for later shows. Ticket prices are
represented by a local adult baseline matrix and do not call provider price
APIs.
