from datetime import date, datetime
from engine.recommendation import ShawRecommendationProvider
from engine.search import SearchService
from models.search_request import SearchRequest
from models.screening import Screening
from models.seat_layout import Seat, SeatLayout
from providers.base import MovieSearchProvider

class FakeProvider(MovieSearchProvider):
    name = "fake"
    def search(self, request):
        return [Screening("fake", request.movie, "Test Cinema", "1", datetime(2026, 8, 6, 19), "STANDARD", "one", "https://example.test")]
    def get_seat_layout(self, performance_id):
        layout = SeatLayout(rows={"A": [1, 2, 3, 4]})
        layout.available = {Seat("A", number) for number in range(1, 5)}
        return layout
    def get_ticket_price(self, performance_id):
        return 12.5

def test_search_adds_recommended_seats():
    results = SearchService([FakeProvider()], {"fake": ShawRecommendationProvider()}).search(SearchRequest("Example", date(2026, 8, 6), pax=2))
    assert results[0].recommended_seats
    assert results[0].seat_quality is not None
    assert results[0].price == 12.5
