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

    def __post_init__(self):
        if not self.movie.strip():
            raise ValueError("movie is required")
        if self.pax < 1:
            raise ValueError("pax must be at least 1")
