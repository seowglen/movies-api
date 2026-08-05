from dataclasses import dataclass

from models.seat_layout import Seat


@dataclass
class Recommendation:
    seats: list
    score: float
    stars: int


class SeatRecommendationProvider:
    """Shared seat-scoring mechanics; each cinema supplies its own preferences."""

    experience_scores = {"STANDARD": 0.5}
    preferred_row = 0.6
    blocks_single_seat = False

    def recommend(self, layout, pax, experience):
        candidates = []
        rows = sorted(layout.rows)
        for row_index, row in enumerate(rows):
            numbers = sorted(set(layout.rows[row]))
            for start in numbers:
                group = [Seat(row, start + offset) for offset in range(pax)]
                if not all(seat in layout.available for seat in group):
                    continue
                if self.blocks_single_seat and self._strands_single_seat(layout, group):
                    continue
                candidates.append((self._score(row_index, rows, numbers, group, layout, experience), [seat.label for seat in group]))
        if not candidates:
            return Recommendation([], 0.0, 0)
        score, seats = max(candidates, key=lambda item: item[0])
        return Recommendation(seats, round(score, 1), max(1, min(5, round(score / 20))))

    def _score(self, row_index, rows, numbers, group, layout, experience):
        center = (min(numbers) + max(numbers)) / 2.0
        group_center = (group[0].number + group[-1].number) / 2.0
        horizontal = max(0.0, 1.0 - abs(group_center - center) / max(1.0, center))
        ideal_row = (len(rows) - 1) * self.preferred_row
        row_score = max(0.0, 1.0 - abs(row_index - ideal_row) / max(1.0, len(rows)))
        buffer_score = sum(1 for seat in (Seat(group[0].row, group[0].number - 1), Seat(group[-1].row, group[-1].number + 1)) if seat in layout.available) / 2.0
        experience_score = self.experience_scores.get(experience.upper(), self.experience_scores["STANDARD"])
        return 100 * (0.45 * row_score + 0.30 * horizontal + 0.15 * experience_score + 0.10 * buffer_score)

    @staticmethod
    def _strands_single_seat(layout, selected):
        selected = set(selected)
        for seat in layout.available - selected:
            left, right = Seat(seat.row, seat.number - 1), Seat(seat.row, seat.number + 1)
            left_booked = left in selected or (left in layout.valid and left not in layout.available)
            right_booked = right in selected or (right in layout.valid and right not in layout.available)
            if (left in selected and right_booked) or (right in selected and left_booked):
                return True
        return False


class ShawRecommendationProvider(SeatRecommendationProvider):
    experience_scores = {"IMAX": 1.0, "PREMIERE": 0.9, "LUMIERE": 0.85, "STANDARD": 0.5}
    preferred_row = 0.6


class GVRecommendationProvider(SeatRecommendationProvider):
    experience_scores = {"GOLD CLASS": 1.0, "GVMAX": 0.9, "DELUXE": 0.85, "GEMINI": 0.8, "AURO": 0.75, "STANDARD": 0.5}
    preferred_row = 0.55
    blocks_single_seat = True
