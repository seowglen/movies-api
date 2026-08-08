from engine.recommendation import GVRecommendationProvider, ShawRecommendationProvider
from models.seat_layout import Seat, SeatLayout
from utils.seat_map import structured_seat_layout

def test_recommendation_prefers_a_centered_contiguous_group():
    layout = SeatLayout(rows={"A": list(range(1, 11)), "B": list(range(1, 11)), "C": list(range(1, 11)), "D": list(range(1, 11)), "E": list(range(1, 11))})
    layout.available = {Seat(row, number) for row in layout.rows for number in layout.rows[row]}
    layout.available.remove(Seat("C", 5))
    recommendation = ShawRecommendationProvider().recommend(layout, pax=2, experience="IMAX")
    assert len(recommendation.seats) == 2
    assert recommendation.score > 0
    assert all(seat != "C5" for seat in recommendation.seats)


def test_recommendation_does_not_leave_one_valid_seat_between_bookings():
    layout = SeatLayout(rows={"A": [1, 2, 3, 4]})
    layout.valid = {Seat("A", number) for number in range(1, 5)}
    layout.enforce_no_single_seat = True
    layout.available = {Seat("A", 1), Seat("A", 2), Seat("A", 3)}
    layout.occupied = {Seat("A", 4)}

    # Selecting A1-A2 would strand the only available valid seat A3 beside A4.
    recommendation = GVRecommendationProvider().recommend(layout, pax=2, experience="STANDARD")

    assert recommendation.seats == ["A2", "A3"]


def test_front_rows_receive_a_strong_penalty():
    layout = SeatLayout(rows={row: list(range(1, 11)) for row in "ABCDE"})
    layout.available = {Seat(row, number) for row in layout.rows for number in layout.rows[row]}
    provider = ShawRecommendationProvider()
    rows = list(layout.rows)
    group = [Seat("A", 5), Seat("A", 6)]

    front_score = provider._score(0, rows, layout.rows["A"], group, layout, "STANDARD")
    middle_score = provider._score(3, rows, layout.rows["D"], [Seat("D", 5), Seat("D", 6)], layout, "STANDARD")

    assert front_score < middle_score - 15


def test_horizontal_center_uses_screening_seat_span():
    layout = SeatLayout(rows={"A": [1, 2, 3, 4, 5]})
    layout.valid = {Seat("A", number) for number in range(1, 6)}
    layout.available = {Seat("A", 3), Seat("A", 4), Seat("A", 5)}
    provider = ShawRecommendationProvider()

    score = provider._score(0, ["A"], [3, 4, 5], [Seat("A", 3), Seat("A", 4)], layout, "STANDARD")

    assert score < 100


def test_premium_experience_has_lighter_front_row_penalty():
    provider = ShawRecommendationProvider()
    rows = ["A", "B", "C", "D", "E"]
    layout = SeatLayout(rows={row: list(range(1, 11)) for row in rows})
    layout.valid = {Seat(row, number) for row in rows for number in range(1, 11)}
    layout.available = set(layout.valid)
    group = [Seat("A", 5), Seat("A", 6)]

    imax = provider._score(0, rows, layout.rows["A"], group, layout, "IMAX")
    premiere = provider._score(0, rows, layout.rows["A"], group, layout, "PREMIERE")

    assert premiere > imax


def test_structured_seat_layout_preserves_seat_statuses():
    layout = SeatLayout(rows={"B": [3, 4, 5, 6]})
    layout.available = {Seat("B", 3), Seat("B", 5)}
    layout.occupied = {Seat("B", 4)}

    assert structured_seat_layout(layout, "gv") == {
        "rows": [{
            "row": "B",
            "seats": [
                {"number": 1, "status": "NOT_A_SEAT"},
                {"number": 2, "status": "NOT_A_SEAT"},
                {"number": 3, "status": "AVAILABLE"},
                {"number": 4, "status": "OCCUPIED"},
                {"number": 5, "status": "AVAILABLE"},
                {"number": 6, "status": "NOT_A_SEAT"},
            ],
        }],
    }["rows"]
