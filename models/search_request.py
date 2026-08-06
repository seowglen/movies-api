from dataclasses import dataclass
from datetime import date, time
from typing import Optional


@dataclass(frozen=True)
class SearchRequest:
    movie: str
    date: date
    after: Optional[time] = None
    pax: int = 2
    location: Optional[str] = None
    experience: Optional[str] = None
    radius_km: Optional[float] = 5.0

    def __post_init__(self):
        if not self.movie.strip():
            raise ValueError("movie is required")
        if self.pax < 1:
            raise ValueError("pax must be at least 1")
        if self.radius_km is not None and self.radius_km <= 0:
            raise ValueError("radius_km must be greater than 0")
