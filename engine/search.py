from concurrent.futures import ThreadPoolExecutor
import logging
from threading import Lock

from cache import seat_layout_cache, showtime_cache, ticket_price_cache
from cache import movie_catalog_cache
from providers.base import CatalogMatch
from rapidfuzz import fuzz, process
from utils.location import DEFAULT_RADIUS_KM, cinema_coordinates, distance_km, resolve_location

logger = logging.getLogger(__name__)
MAX_SCREENINGS = 10


class SearchService:
    def __init__(self, providers, recommendation_providers):
        self.providers = {provider.name: provider for provider in providers}
        self.recommendation_providers = recommendation_providers
        self._catalog_cache_lock = Lock()
        self._price_cache_lock = Lock()
        self._seat_cache_lock = Lock()


    def search(self, request):
        cache_key = (request.movie.casefold(), request.date.isoformat(), request.after.isoformat() if request.after else None, request.pax, request.location, request.experience, request.radius_km)
        if cache_key in showtime_cache: return showtime_cache[cache_key]

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

        screenings = self._select_candidates(screenings)

        with ThreadPoolExecutor(max_workers=min(8, max(1, len(screenings)))) as executor:
            enrichments = [executor.submit(self._enrich_screening, screening, request) for screening in screenings]
            for enrichment in enrichments:
                enrichment.result()

        screenings = [screening for screening in screenings if screening.recommended_seats]
        screenings.sort(key=lambda item: (-1 if item.seat_quality is None else -item.seat_quality, item.datetime))
        showtime_cache[cache_key] = screenings
        return screenings

    @staticmethod
    def _select_candidates(screenings):
        if not screenings:
            return []
        if any(screening.distance_km is not None for screening in screenings):
            screenings.sort(key=lambda item: (float("inf") if item.distance_km is None else item.distance_km, item.datetime))
        else:
            screenings.sort(key=lambda item: item.datetime)
        return screenings[:MAX_SCREENINGS]

    def _enrich_screening(self, screening, request):
        provider = self.providers[screening.provider]
        price_key = (screening.provider, screening.performance_id)
        try:
            with self._price_cache_lock:
                cached_price = ticket_price_cache.get(price_key)
            if cached_price is None:
                price = provider.get_ticket_price(screening.performance_id)
                with self._price_cache_lock:
                    ticket_price_cache[price_key] = price
                cached_price = price
            screening.price = cached_price
        except Exception:
            logger.exception("Price lookup failed for %s %s", screening.provider, screening.performance_id)

        try:
            recommender = self.recommendation_providers[screening.provider]
            recommendation = recommender.recommend(self._layout(provider, screening.performance_id), request.pax, screening.experience)
            screening.recommended_seats, screening.seat_quality = recommendation.seats, recommendation.score
        except Exception:
            logger.exception("Seat recommendation failed for %s %s", screening.provider, screening.performance_id)

    def _search_provider(self, provider, request):
        catalog = self.catalog_for(provider, request.date)
        matches = self.resolve_movie_ids(provider, request.movie, request.date, catalog)
        movie_ids = {match.movie_id for match in matches}
        selected_catalog = [entry for entry in catalog if entry.movie_id in movie_ids]
        screenings = provider.search(request, movie_ids, selected_catalog)
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


    def _layout(self, provider, performance_id):
        key = (provider.name, performance_id)
        with self._seat_cache_lock:
            if key in seat_layout_cache:
                return seat_layout_cache[key]

        layout = provider.get_seat_layout(performance_id)
        with self._seat_cache_lock:
            if key not in seat_layout_cache:
                seat_layout_cache[key] = layout
            return seat_layout_cache[key]
