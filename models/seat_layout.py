from dataclasses import dataclass, field
from typing import Dict, List, Set


@dataclass(frozen=True)
class Seat:
    row: str
    number: int

    @property
    def label(self):
        return "%s%s" % (self.row, self.number)


@dataclass
class SeatLayout:
    rows: Dict[str, List[int]] = field(default_factory=dict)
    valid: Set[Seat] = field(default_factory=set)
    occupied: Set[Seat] = field(default_factory=set)
    available: Set[Seat] = field(default_factory=set)
    enforce_no_single_seat: bool = False

    def is_available(self, seat):
        return seat in self.available
