"""FastAPI application entry point for the movie recommendation API."""
from dataclasses import asdict
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from engine.recommendation import GVRecommendationProvider, ShawRecommendationProvider
from engine.search import SearchService
from models.search_request import SearchRequest
from models.api import HealthResponse, SearchJobResponse, SearchPayload
from engine.search_jobs import SearchJobManager, WorkerConfig
from providers import GVSearchProvider, ShawSearchProvider
from utils.location import LOCATION_ALIASES

app = FastAPI(title="Movie Recommendation Engine", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://cinema-screener-c39588.gitlab.io",
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
providers = [ShawSearchProvider(), GVSearchProvider()]
recommendation_providers = {
    "shaw": ShawRecommendationProvider(),
    "gv": GVRecommendationProvider(),
}


search_service = SearchService(providers, recommendation_providers)
search_jobs = SearchJobManager(
    search_service,
    {
        "gv": WorkerConfig(max_concurrency=1, min_delay_seconds=1.5, max_delay_seconds=2.0),
        "shaw": WorkerConfig(max_concurrency=1),
    },
)


def catalog_for(target_date):
    movies = []
    for provider in providers:
        try:
            catalog = search_service.catalog_for(provider, target_date)
            movies.extend({"provider": provider.name, "movie_id": item.movie_id, "title": item.title} for item in catalog)
        except Exception:
            continue
    return movies


def request_from_payload(payload):
    try:
        start = _utc_to_singapore(payload["startTimeUTC"])
        end = _utc_to_singapore(payload["endTimeUTC"]) if payload.get("endTimeUTC") else None
        location = payload.get("location")
        if location is not None:
            location = str(location).strip().upper()
            if location.casefold() not in LOCATION_ALIASES:
                raise ValueError("location must be a supported Singapore location alias")
        experience = payload.get("experience")
        if experience is not None:
            experience = str(experience).strip().upper().replace("_", " ")
            if experience not in SUPPORTED_EXPERIENCES:
                raise ValueError("experience must be one of: %s" % ", ".join(sorted(SUPPORTED_EXPERIENCES)))
        return SearchRequest(
            movie=str(payload["title"]),
            date=start.date(),
            after=start.time(),
            until=end.time() if end else None,
            end_date=end.date() if end else start.date(),
            pax=int(payload.get("paxCount", 2)),
            location=location,
            experience=experience,
            radius_km=float(payload.get("radius_km", 5.0)),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid search request: %s" % exc)


SUPPORTED_EXPERIENCES = {"STANDARD", "IMAX", "PREMIERE", "LUMIERE", "GOLD CLASS", "GVMAX", "DELUXE", "GEMINI", "AURO"}
SINGAPORE_TZ = timezone(timedelta(hours=8))


def _utc_to_singapore(value):
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("UTC timestamps must include a timezone")
    if parsed.utcoffset() != timedelta(0):
        raise ValueError("timestamps must be UTC")
    return parsed.astimezone(SINGAPORE_TZ)


@app.get("/health", response_model=HealthResponse)
def health():
    return {"status": "ok"}


@app.get("/movies", include_in_schema=False)
def movies(target_date: str = None):
    try:
        requested_date = date.fromisoformat(target_date) if target_date else date.today()
    except ValueError:
        raise HTTPException(status_code=422, detail="target_date must be YYYY-MM-DD")
    return {"date": requested_date.isoformat(), "movies": catalog_for(requested_date)}


@app.post("/search", response_model=SearchJobResponse, status_code=status.HTTP_202_ACCEPTED, summary="Start a screening search")
def search(payload: SearchPayload):
    request = request_from_payload(payload.model_dump(mode="json"))
    return job_response(search_jobs.submit(request))


@app.get("/search/{job_id}", response_model=SearchJobResponse, summary="Get screening search status")
def search_status(job_id: str):
    response = job_response(job_id)
    if response is None:
        raise HTTPException(status_code=404, detail="search job not found")
    return response


def job_response(job_id):
    response = search_jobs.get(job_id)
    if response is not None:
        response["screenings"] = [screening_response(item) for item in response["screenings"]]
    return response


def screening_response(screening):
    start_time = screening.datetime
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=SINGAPORE_TZ)
    else:
        start_time = start_time.astimezone(SINGAPORE_TZ)
    start_time_utc = start_time.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "provider": screening.provider.upper(),
        "movie": screening.movie,
        "cinema": screening.cinema,
        "hall": screening.hall,
        "startTimeUTC": start_time_utc,
        "experience": screening.experience,
        "performanceId": screening.performance_id,
        "bookingUrl": screening.booking_url,
        "baselinePrice": screening.baseline_price,
        "seatQuality": screening.seat_quality,
        "recommendedSeats": screening.recommended_seats,
        "seatLayout": screening.seat_layout,
        "seatStatus": screening.seat_status,
    }
