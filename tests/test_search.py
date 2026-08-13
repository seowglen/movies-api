from datetime import date, datetime
from engine.recommendation import ShawRecommendationProvider
from engine.search import SearchService
from models.search_request import SearchRequest
from models.screening import Screening
from models.seat_layout import Seat, SeatLayout
from providers.base import MovieCatalog, MovieSearchProvider
from utils.location import cinema_coordinates, resolve_location

class FakeProvider(MovieSearchProvider):
    name = "fake"
    def __init__(self):
        self.catalog_calls = 0
    def catalog(self, target_date):
        self.catalog_calls += 1
        return [MovieCatalog("example-id", "Example")]
    def search(self, request, movie_ids, catalog):
        assert movie_ids == {"example-id"}
        assert [entry.movie_id for entry in catalog] == ["example-id"]
        return [Screening("fake", request.movie, "Test Cinema", "1", datetime(2026, 8, 6, 19), "STANDARD", "one", "https://example.test")]
    def get_seat_layout(self, performance_id):
        layout = SeatLayout(rows={"A": [1, 2, 3, 4]})
        layout.available = {Seat("A", number) for number in range(1, 5)}
        return layout
    def get_ticket_price(self, performance_id):
        return 12.5

def test_search_adds_recommended_seats():
    provider = FakeProvider()
    results = SearchService([provider], {"fake": ShawRecommendationProvider()}).search(SearchRequest("Example", date(2026, 8, 6), pax=2))
    assert results[0].recommended_seats
    assert results[0].seat_quality is not None
    assert results[0].baseline_price is None
    assert provider.catalog_calls == 1


def test_resolver_keeps_close_movie_variants_from_one_provider():
    provider = FakeCatalogProvider()
    matches = SearchService([provider], {}).resolve_movie_ids(provider, "spider man", date(2026, 8, 6))
    assert [match.movie_id for match in matches] == ["standard", "atmos"]


def test_provider_failure_does_not_hide_other_results():
    provider = FakeProvider()
    results = SearchService([FailingProvider(), provider], {"fake": ShawRecommendationProvider()}).search(
        SearchRequest("Example", date(2026, 8, 7), pax=2)
    )
    assert results


def test_location_filter_adds_distance_and_excludes_far_screenings():
    screenings = [
        Screening("gv", "Example", "GV VivoCity", "1", datetime(2026, 8, 7, 19), "STANDARD", "near", "url", cinema_id="05"),
        Screening("gv", "Example", "GV Yishun", "1", datetime(2026, 8, 7, 20), "STANDARD", "far", "url", cinema_id="01"),
    ]
    request = SearchRequest("Example", date(2026, 8, 7), location="Orchard", radius_km=5)

    results = SearchService._filter_by_location(screenings, request)

    assert [item.performance_id for item in results] == ["near"]
    assert results[0].distance_km is not None


def test_current_location_expands_from_three_to_five_kilometres_when_empty():
    screening = Screening("gv", "Example", "GV VivoCity", "1", datetime(2026, 8, 7, 19), "STANDARD", "near", "url", cinema_id="05")
    request = SearchRequest(
        "Example", date(2026, 8, 7), location_scope="CURRENT", latitude=1.3048, longitude=103.8318
    )

    results = SearchService._filter_by_location([screening], request)

    assert results == [screening]


def test_candidate_cap_prioritizes_distance_before_enrichment():
    screenings = [
        Screening("gv", "Example", "GV VivoCity", "1", datetime(2026, 8, 7, 20), "STANDARD", "far", "url", distance_km=4.0),
        Screening("gv", "Example", "GV VivoCity", "1", datetime(2026, 8, 7, 19), "STANDARD", "near", "url", distance_km=1.0),
    ]

    results = SearchService._select_candidates(screenings)

    assert [item.performance_id for item in results] == ["near", "far"]


def test_multi_day_candidate_cap_keeps_each_date_represented():
    screenings = [
        Screening("fake", "Example", "Test", "1", datetime(2026, 8, 7, 19), "STANDARD", "d1", "url"),
        Screening("fake", "Example", "Test", "1", datetime(2026, 8, 8, 19), "STANDARD", "d2", "url"),
        Screening("fake", "Example", "Test", "1", datetime(2026, 8, 9, 19), "STANDARD", "d3", "url"),
    ]
    request = SearchRequest("Example", date(2026, 8, 7), end_date=date(2026, 8, 9))

    results = SearchService._select_candidates(screenings, request)

    assert {item.datetime.date() for item in results} == {
        date(2026, 8, 7), date(2026, 8, 8), date(2026, 8, 9)
    }


def test_search_removes_screenings_without_recommended_seats():
    provider = EmptySeatsProvider()
    results = SearchService([provider], {"fake": ShawRecommendationProvider()}).search(
        SearchRequest("Example", date(2026, 8, 8))
    )

    assert results == []


def test_location_defaults_to_five_kilometres_and_handles_typos():
    request = SearchRequest("Example", date(2026, 8, 7), location="orchad")

    assert request.radius_km == 5.0
    assert resolve_location(request.location) == resolve_location("Orchard")


def test_user_aliases_and_cinema_coordinates_are_separate():
    assert resolve_location("Marina Bay") is not None
    assert cinema_coordinates("shaw", "Lido Hall 2", "1") == resolve_location("Orchard")
    assert cinema_coordinates("gv", "Unknown Cinema", "05") == resolve_location("VivoCity")


class FakeCatalogProvider(MovieSearchProvider):
    name = "catalog"

    def catalog(self, target_date):
        return [
            MovieCatalog("standard", "Spider-Man: Brand New Day"),
            MovieCatalog("atmos", "(Atmos) Spider-Man: Brand New Day"),
            MovieCatalog("unrelated", "Spider-Verse"),
        ]

    def search(self, request, movie_ids=None):
        return []

    def get_seat_layout(self, performance_id):
        return SeatLayout()

    def get_ticket_price(self, performance_id):
        return None


class FailingProvider(MovieSearchProvider):
    name = "failing"

    def catalog(self, target_date):
        raise RuntimeError("provider unavailable")

    def search(self, request, movie_ids=None, catalog=None):
        raise AssertionError("search should not run after catalog failure")

    def get_seat_layout(self, performance_id):
        return SeatLayout()

    def get_ticket_price(self, performance_id):
        return None


class EmptySeatsProvider(FakeProvider):
    def search(self, request, movie_ids, catalog):
        return [Screening("fake", request.movie, "Test Cinema", "1", datetime(2026, 8, 8, 19), "STANDARD", "empty-one", "https://example.test")]

    def get_seat_layout(self, performance_id):
        return SeatLayout(rows={"A": [1, 2]}, available=set())
