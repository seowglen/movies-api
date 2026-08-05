from cache import seat_layout_cache, showtime_cache, ticket_price_cache


class SearchService:
    def __init__(self, providers, recommendation_providers):
        self.providers = {provider.name: provider for provider in providers}
        self.recommendation_providers = recommendation_providers


    def search(self, request):
        cache_key = (request.movie.casefold(), request.date.isoformat(), request.after.isoformat() if request.after else None, request.pax, request.location, request.experience)
        if cache_key in showtime_cache: return showtime_cache[cache_key]

        screenings = []
        for provider in self.providers.values():
            try: screenings.extend(provider.search(request))
            except Exception: continue

        for screening in screenings:
            provider = self.providers[screening.provider]
            try:
                price_key = (screening.provider, screening.performance_id)
                if price_key not in ticket_price_cache:
                    ticket_price_cache[price_key] = provider.get_ticket_price(screening.performance_id)
                screening.price = ticket_price_cache[price_key]
            except Exception:
                pass
            try:
                recommender = self.recommendation_providers[screening.provider]
                recommendation = recommender.recommend(self._layout(provider, screening.performance_id), request.pax, screening.experience)
                screening.recommended_seats, screening.seat_quality = recommendation.seats, recommendation.score
            # A seat-plan outage should not hide an otherwise valid showtime.
            except Exception:
                pass

        screenings.sort(key=lambda item: (-1 if item.seat_quality is None else -item.seat_quality, item.datetime))
        showtime_cache[cache_key] = screenings
        return screenings


    @staticmethod
    def _layout(provider, performance_id):
        key = (provider.name, performance_id)
        if key not in seat_layout_cache:
            seat_layout_cache[key] = provider.get_seat_layout(performance_id)
        return seat_layout_cache[key]
