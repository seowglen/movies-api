# Architecture Decisions

This document records the important design decisions behind the Movie
Recommendation Engine and the tradeoffs they represent.

## 1. Structured Search API

The public search API accepts a structured request instead of natural-language
text:

```json
{
  "title": "spiderman",
  "startTimeUTC": "2026-08-14T00:00:00Z",
  "endTimeUTC": "2026-08-14T15:59:00Z",
  "paxCount": 2,
  "location": "ORCHARD",
  "experience": "IMAX"
}
```

Natural-language parsing was intentionally kept outside the core search API.
This keeps the API deterministic, easy to validate, and usable by any client.

## 2. Provider-Local Movie Resolution

Movie titles are resolved independently against each provider's catalog.
The parser or client never receives provider-specific titles such as Atmos or
premium variants.

The flow is:

```text
user title -> provider catalog -> provider movie IDs -> showtimes
```

This avoids incorrectly sharing GV titles with Shaw or selecting only one
provider's version of a movie.

## 3. Asynchronous Search Jobs

`POST /search` creates a job and returns a job ID. Clients poll
`GET /search/{jobId}` for progress and results.

Seat-plan calls are slow and rate-limited, so blocking the initial HTTP request
would create poor user experience and tie up server workers. The job model lets
the frontend show candidate screenings while seat recommendations are loading.

The current implementation uses in-process workers for the MVP. A durable
Redis-backed queue is the natural next step for multiple machines or restart
survival.

## 4. Independent Provider Workers

GV and Shaw use separate worker queues and policies.

GV is configured conservatively because its seat-plan API is more sensitive to
request bursts. Shaw has an independent queue so a GV outage cannot block Shaw
results.

Each worker owns provider-specific rate limits, delays, and failure handling.

Before a candidate is queued, the job manager checks the processed seat-layout
cache. Cache hits avoid provider traffic entirely. Cache misses are deduplicated
by `(provider, performance_id)` so concurrent users share one in-flight task.
This protects provider APIs from duplicate requests while preserving the same
single ranked result flow for clients.

## 5. Bounded Candidate Enrichment

Showtimes are cheap compared with seat-plan requests. The service selects a
bounded candidate pool before fetching layouts.

Current policy:

```text
candidate screenings: up to 20
returned screenings: all successful candidates, up to 20
```

This prevents hundreds of seat-plan calls for a broad date range while still
allowing the frontend to filter by experience, cinema, quality, or time.

## 6. Location Resolution

The API supports both named Singapore aliases and exact latitude/longitude
coordinates. Exact coordinates take precedence when both are supplied. Cinema
coordinates are keyed by provider and provider cinema ID; names are only a
fallback for unmapped records.

The frontend may use browser geolocation, but users can always choose a default
Singapore alias instead. A five-kilometre radius is used by default.

## 7. Seat Layout Caching

Catalogs and provider showtimes are cached for one hour. Processed seat layouts
use a dynamic TTL based on time to showtime:

```text
less than 2 hours: 30 seconds
2–24 hours:       3 minutes
more than 24h:    15 minutes
```

The service is advisory rather than transactional, so short-lived seat
staleness is acceptable in exchange for lower provider traffic.

The cache uses monotonic expiry values so system clock changes do not corrupt
TTL calculations.

## 8. Baseline Pricing

The service does not call provider ticket-price APIs during search. Instead, it
returns an indicative adult `baselinePrice` from a local Singapore pricing
matrix.

This avoids expensive and promotion-dependent price calls. The baseline is not
presented as a guaranteed checkout price because final pricing can depend on
demographics, payment methods, promotions, and booking fees.

## 9. Seat Recommendation Scoring

Recommendations use explainable geometry rather than a black-box model:

- 60% horizontal center position.
- 40% row position.
- Dynamic buffer-seat contribution based on occupancy.
- Experience-specific ideal row depth.
- Experience-specific penalties for front rows.

Large-screen formats such as IMAX and GVMAX penalize front rows more heavily.
Premium recliner formats use lighter penalties.

The provider-specific row orientation is explicit: GV and Shaw label front rows
differently.

## 10. Frontend Seat Layout Contract

The backend returns canonical seat facts rather than a UI-specific grid:

```text
AVAILABLE
OCCUPIED
NOT_A_SEAT
UNKNOWN
```

Rows and seats are ordered in visual order for the provider. The frontend owns
rendering, previews, filtering, and the full seat-layout modal.

## 11. Partial Provider Failure

Provider failures are isolated. A GV catalog or seat-plan failure must not
remove valid Shaw results.

Jobs can finish as `PARTIAL` when some candidates fail enrichment. Individual
screenings expose `seatStatus` so clients can distinguish loading, ready, and
failed seat data.

## 12. Deployment Tradeoffs

The MVP can run as one always-on machine with in-memory state. This keeps the
system simple and preserves cache locality.

The tradeoff is that jobs, queues, and caches disappear on restart. A scaled
deployment should use Redis for shared caches, job state, and provider queues.

Provider APIs may also treat cloud-hosted IPs differently from residential
networks. This is an upstream integration risk, not something that can be
fully solved through application retries.

## 13. Rejected Alternatives

### Calling an LLM for every search

Rejected because it adds latency, quota dependence, and unpredictable parsing
to a deterministic API. Natural-language parsing can remain a separate client
feature.

### Calculating exact ticket prices

Rejected because provider pricing includes promotions, payment methods,
demographics, and channel fees that the search request does not contain.

### Prefetching every movie and screening

Rejected because it wastes provider requests and increases rate-limit risk.
Prefetching should be demand-driven or limited to popular candidates.

### Returning the entire raw provider response

Rejected because it couples the frontend to provider schemas and exposes
unstable implementation details. The API returns normalized data instead.
