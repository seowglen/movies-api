from dataclasses import dataclass

from models.seat_layout import Seat


@dataclass
class Recommendation:
    seats: list
    score: float
    stars: int


class SeatRecommendationProvider:
    """Shared seat-scoring mechanics; each cinema supplies its own preferences."""

    preferred_row = 0.6
    blocks_single_seat = False
    front_rows_high_letters = False
    experience_row_targets = {"STANDARD": 0.66}
    experience_front_penalties = {
        "STANDARD": {0: 36.0, 1: 26.0, 2: 15.0},
        "DELUXE": {0: 36.0, 1: 26.0, 2: 15.0},
        "GEMINI": {0: 30.0, 1: 22.0, 2: 12.0},
        "LUMIERE": {0: 25.0, 1: 16.0, 2: 8.0},
        "PREMIERE": {0: 25.0, 1: 16.0, 2: 8.0},
        "AURO": {0: 36.0, 1: 26.0, 2: 15.0},
        "GOLD CLASS": {0: 15.0, 1: 8.0, 2: 2.0},
        "IMAX": {0: 55.0, 1: 42.0, 2: 30.0, 3: 18.0, 4: 8.0},
        "GVMAX": {0: 48.0, 1: 36.0, 2: 24.0, 3: 14.0, 4: 6.0},
    }

    def recommend(self, layout, pax, experience):
        candidates = []
        rows = sorted(layout.rows, reverse=self.front_rows_high_letters)
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
        max_seat_number = max((max(row_numbers) for row_numbers in layout.rows.values() if row_numbers), default=max(numbers))
        center = (1 + max_seat_number) / 2.0
        group_center = (group[0].number + group[-1].number) / 2.0
        horizontal = max(0.0, 1.0 - abs(group_center - center) / max(1.0, center))
        ideal_row = (len(rows) - 1) * self.experience_row_targets.get(experience.upper(), self.preferred_row)
        row_score = max(0.0, 1.0 - abs(row_index - ideal_row) / max(1.0, len(rows)))
        buffer_score = sum(1 for seat in (Seat(group[0].row, group[0].number - 1), Seat(group[-1].row, group[-1].number + 1)) if seat in layout.available) / 2.0
        penalties = self.experience_front_penalties.get(experience.upper(), self.experience_front_penalties["STANDARD"])
        front_penalty = penalties.get(row_index, 0.0)
        valid_count = len(layout.valid)
        occupancy = len(layout.occupied & layout.valid) / float(valid_count) if valid_count else 0.0
        buffer_weight = max(0.0, min(0.20, 0.20 * (0.70 - occupancy) / 0.30))
        geometry_weight = 1.0 - buffer_weight
        weighted_score = 100 * (
            geometry_weight * (0.60 * horizontal + 0.40 * row_score)
            + buffer_weight * buffer_score
        )
        return max(0.0, weighted_score - front_penalty)

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
    preferred_row = 0.6
    front_rows_high_letters = True
    experience_row_targets = {"STANDARD": 0.66, "IMAX": 0.55, "PREMIERE": 0.72, "LUMIERE": 0.72}


class GVRecommendationProvider(SeatRecommendationProvider):
    preferred_row = 0.55
    blocks_single_seat = True
    experience_row_targets = {
        "STANDARD": 0.66,
        "GVMAX": 0.60,
        "GOLD CLASS": 0.75,
        "DELUXE": 0.66,
        "GEMINI": 0.70,
        "AURO": 0.75,
    }
