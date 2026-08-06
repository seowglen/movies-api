from engine.recommendation import GVRecommendationProvider, ShawRecommendationProvider
from models.seat_layout import Seat, SeatLayout

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
