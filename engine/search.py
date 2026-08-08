from concurrent.futures import ThreadPoolExecutor
import logging
import random
import time
from threading import Lock
from time import monotonic

from cache import movie_catalog_cache, seat_layout_cache
from providers.base import CatalogMatch
from rapidfuzz import fuzz, process
from utils.location import DEFAULT_RADIUS_KM, cinema_coordinates, distance_km, resolve_location
from utils.pricing import resolve_baseline_price
from utils.seat_map import structured_seat_layout
from utils.seat_cache import seat_layout_ttl

logger = logging.getLogger(__name__)
MAX_CANDIDATES = 25
MAX_RESULTS = 10
ENRICHMENT_BATCH_SIZE = 4
ENRICHMENT_BATCH_DELAY_SECONDS = 1.0
ENRICHMENT_DELAY_JITTER_SECONDS = 0.25


class SearchService:
    def __init__(self, providers, recommendation_providers):
        self.providers = {provider.name: provider for provider in providers}
        self.recommendation_providers = recommendation_providers
        self._catalog_cache_lock = Lock()
        self._seat_cache_lock = Lock()


    def search(self, request):
        screenings = []
        providers = list(self.providers.values())
        with ThreadPoolExecutor(max_workers=max(1, len(providers))) as executor:
            searches = {
                provider.name: executor.submit(self._search_provider, provider, request)
                for provider in providers
            }
            for provider in providers:
                try:
                    screenings.extend(searches[provider.name].result())
                except Exception:
                    logger.exception("Movie search failed for provider %s", provider.name)

        screenings = self._select_candidates(screenings, request)

        for start in range(0, len(screenings), ENRICHMENT_BATCH_SIZE):
            batch = screenings[start:start + ENRICHMENT_BATCH_SIZE]
            with ThreadPoolExecutor(max_workers=len(batch)) as executor:
                enrichments = [executor.submit(self._enrich_screening, screening, request) for screening in batch]
                for enrichment in enrichments:
                    enrichment.result()
            if start + ENRICHMENT_BATCH_SIZE < len(screenings):
                delay = ENRICHMENT_BATCH_DELAY_SECONDS + random.uniform(
                    -ENRICHMENT_DELAY_JITTER_SECONDS,
                    ENRICHMENT_DELAY_JITTER_SECONDS,
                )
                time.sleep(delay)

        screenings = [screening for screening in screenings if screening.recommended_seats]
        screenings.sort(key=lambda item: (-1 if item.seat_quality is None else -item.seat_quality, item.datetime))
        screenings = screenings[:MAX_RESULTS]
        return screenings

    @staticmethod
    def _select_candidates(screenings, request=None):
        if not screenings:
            return []
        if any(screening.distance_km is not None for screening in screenings):
            screenings.sort(key=lambda item: (float("inf") if item.distance_km is None else item.distance_km, item.datetime))
            return screenings[:MAX_CANDIDATES]

        screenings.sort(key=lambda item: item.datetime)
        dates = sorted({screening.datetime.date() for screening in screenings})
        if request and len(dates) > 1:
            slots_per_date = max(1, MAX_CANDIDATES // len(dates))
            selected = []
            for target_date in dates:
                date_screenings = [screening for screening in screenings if screening.datetime.date() == target_date]
                selected.extend(date_screenings[:slots_per_date])
            selected_ids = {id(screening) for screening in selected}
            selected.extend(screening for screening in screenings if id(screening) not in selected_ids)
            return selected[:MAX_CANDIDATES]
        return screenings[:MAX_CANDIDATES]

    def _enrich_screening(self, screening, request):
        provider = self.providers[screening.provider]
        try:
            screening.baseline_price = resolve_baseline_price(screening.provider, screening.experience, screening.datetime)
        except Exception:
            logger.exception("Baseline price lookup failed for %s %s", screening.provider, screening.performance_id)

        try:
            recommender = self.recommendation_providers[screening.provider]
            layout = self._layout(provider, screening.performance_id, screening.datetime)
            screening.seat_layout = structured_seat_layout(layout, screening.provider)
            recommendation = recommender.recommend(layout, request.pax, screening.experience)
            screening.recommended_seats, screening.seat_quality = recommendation.seats, recommendation.score
        except Exception as exc:
            response = getattr(exc, "response", None)
            status_code = getattr(response, "status_code", None)
            logger.warning(
                "seat_recommendation_failed provider=%s performance_id=%s status=%s error=%s",
                screening.provider,
                screening.performance_id,
                status_code or "unknown",
                str(exc),
            )

    def _search_provider(self, provider, request):
        screenings = []
        for target_date in request.search_dates:
            daily_request = request.for_date(target_date)
            catalog = self.catalog_for(provider, target_date)
            matches = self.resolve_movie_ids(provider, daily_request.movie, target_date, catalog)
            movie_ids = {match.movie_id for match in matches}
            selected_catalog = [entry for entry in catalog if entry.movie_id in movie_ids]
            screenings.extend(provider.search(daily_request, movie_ids, selected_catalog))
        return self._filter_by_location(screenings, request)

    @staticmethod
    def _filter_by_location(screenings, request):
        target = resolve_location(request.location)
        if target is None:
            if not request.location:
                return screenings
            return [screening for screening in screenings if request.location.casefold() in screening.cinema.casefold()]

        radius = request.radius_km or DEFAULT_RADIUS_KM
        filtered = []
        for screening in screenings:
            coordinates = cinema_coordinates(screening.provider, screening.cinema, screening.cinema_id)
            if coordinates is None:
                continue
            distance = distance_km(target, coordinates)
            if distance <= radius:
                screening.distance_km = round(distance, 2)
                filtered.append(screening)
        return filtered

    def catalog_for(self, provider, target_date):
        key = (provider.name, target_date.isoformat())
        with self._catalog_cache_lock:
            if key in movie_catalog_cache:
                return movie_catalog_cache[key]

        catalog = list(provider.catalog(target_date))
        with self._catalog_cache_lock:
            if key not in movie_catalog_cache:
                movie_catalog_cache[key] = catalog
            return movie_catalog_cache[key]

    def resolve_movie_ids(self, provider, query, target_date, catalog=None):
        catalog = catalog if catalog is not None else self.catalog_for(provider, target_date)
        if not catalog:
            return []
        matches = process.extract(query, [entry.title for entry in catalog], scorer=fuzz.WRatio, limit=2)
        best_score = matches[0][1] if matches else 0
        return [
            CatalogMatch(catalog[index].movie_id, score)
            for _, score, index in matches
            if score >= 80 and score >= best_score - 5
        ]


    def _layout(self, provider, performance_id, showtime):
        key = (provider.name, performance_id)
        with self._seat_cache_lock:
            cached = seat_layout_cache.get(key)
            if cached and cached[1] > monotonic():
                return cached[0]
            seat_layout_cache.pop(key, None)

        layout = provider.get_seat_layout(performance_id)
        with self._seat_cache_lock:
            seat_layout_cache[key] = (layout, monotonic() + seat_layout_ttl(showtime))
            if len(seat_layout_cache) > 512:
                seat_layout_cache.pop(next(iter(seat_layout_cache)))
            return layout
