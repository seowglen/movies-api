from dataclasses import dataclass
from datetime import date, time, timedelta
from typing import Optional


@dataclass(frozen=True)
class SearchRequest:
    movie: str
    date: date
    after: Optional[time] = None
    pax: int = 2
    location: Optional[str] = None
    experience: Optional[str] = None
    until: Optional[time] = None
    end_date: Optional[date] = None
    radius_km: Optional[float] = 5.0

    def __post_init__(self):
        if not self.movie.strip():
            raise ValueError("movie is required")
        if self.pax < 1:
            raise ValueError("pax must be at least 1")
        if self.end_date and self.end_date < self.date:
            raise ValueError("end_date must not be before date")
        if self.date == (self.end_date or self.date) and self.after and self.until and self.until <= self.after:
            raise ValueError("until must be later than after")

    @property
    def search_dates(self):
        end_date = self.end_date or self.date
        return [self.date + timedelta(days=offset) for offset in range((end_date - self.date).days + 1)]

    def for_date(self, target_date):
        from dataclasses import replace

        return replace(
            self,
            date=target_date,
            end_date=target_date,
            after=self.after if target_date == self.date else None,
            until=self.until if target_date == (self.end_date or self.date) else None,
        )
        if self.radius_km is not None and self.radius_km <= 0:
            raise ValueError("radius_km must be greater than 0")
