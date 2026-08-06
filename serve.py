"""FastAPI application entry point for the movie recommendation API."""
from dataclasses import asdict
from datetime import date, time
from typing import Any, Dict

from fastapi import FastAPI, HTTPException

from engine.parser import ParserService
from engine.recommendation import GVRecommendationProvider, ShawRecommendationProvider
from engine.search import SearchService
from models.search_request import SearchRequest
from providers import GVSearchProvider, ShawSearchProvider

app = FastAPI(title="Movie Recommendation Engine", version="0.1.0")
providers = [ShawSearchProvider(), GVSearchProvider()]
recommendation_providers = {
    "shaw": ShawRecommendationProvider(),
    "gv": GVRecommendationProvider(),
}


search_service = SearchService(providers, recommendation_providers)


def catalog_for(target_date):
    movies = []
    for provider in providers:
        try:
            catalog = search_service.catalog_for(provider, target_date)
            movies.extend({"provider": provider.name, "movie_id": item.movie_id, "title": item.title} for item in catalog)
        except Exception:
            continue
    return movies


parser_service = ParserService()


def request_from_payload(payload):
    try:
        return SearchRequest(
            movie=str(payload["movie"]),
            date=date.fromisoformat(payload["date"]),
            after=time.fromisoformat(payload["after"]) if payload.get("after") else None,
            pax=int(payload.get("pax", 2)),
            location=payload.get("location"),
            experience=payload.get("experience"),
            radius_km=float(payload["radius_km"]) if payload.get("radius_km") is not None else None,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid search request: %s" % exc)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/movies", deprecated=True)
def movies(target_date: str = None):
    try:
        requested_date = date.fromisoformat(target_date) if target_date else date.today()
    except ValueError:
        raise HTTPException(status_code=422, detail="target_date must be YYYY-MM-DD")
    return {"date": requested_date.isoformat(), "movies": catalog_for(requested_date)}


@app.post("/parse", deprecated=True)
def parse(payload: Dict[str, Any]):
    query = str(payload.get("query", "")).strip()
    if not query:
        raise HTTPException(status_code=422, detail="query is required")
    try:
        return asdict(parser_service.parse(query))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/search")
def search(payload: Dict[str, Any]):
    if payload.get("query"):
        try:
            request = parser_service.parse(str(payload["query"]))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
    else:
        request = request_from_payload(payload)
    return {"request": asdict(request), "screenings": [asdict(item) for item in search_service.search(request)]}
