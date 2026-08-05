from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Screening:
    provider: str
    movie: str
    cinema: str
    hall: str
    datetime: datetime
    experience: str
    performance_id: str
    booking_url: str
    price: Optional[float] = None
    seat_quality: Optional[float] = None
    recommended_seats: List[str] = field(default_factory=list)
