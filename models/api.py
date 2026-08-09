from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from utils.location import LOCATION_ALIASES


LocationCode = Enum(
    "LocationCode",
    {alias.upper().replace(" ", "_"): alias.upper() for alias in LOCATION_ALIASES},
    type=str,
)


class Experience(str, Enum):
    STANDARD = "STANDARD"
    IMAX = "IMAX"
    PREMIERE = "PREMIERE"
    LUMIERE = "LUMIERE"
    GOLD_CLASS = "GOLD CLASS"
    GVMAX = "GVMAX"
    DELUXE = "DELUXE"
    GEMINI = "GEMINI"
    AURO = "AURO"


class SeatStatus(BaseModel):
    number: int = Field(..., description="Provider seat number")
    status: str = Field(..., description="AVAILABLE, OCCUPIED, NOT_A_SEAT, or UNKNOWN")


class SeatLayoutRow(BaseModel):
    row: str = Field(..., description="Row label in visual front-to-back order")
    seats: List[SeatStatus] = Field(..., description="Seats in visual left-to-right order")


class SearchPayload(BaseModel):
    title: str = Field(..., min_length=1, description="User movie title or search phrase", examples=["spiderman"])
    startTimeUTC: datetime = Field(..., description="Inclusive UTC start time", examples=["2026-08-07T11:00:00Z"])
    endTimeUTC: Optional[datetime] = Field(None, description="Inclusive UTC end time", examples=["2026-08-07T15:00:00Z"])
    paxCount: int = Field(2, ge=1, description="Number of adjacent seats required", examples=[4])
    location: Optional[LocationCode] = Field(None, description="Singapore location alias", examples=["ORCHARD"])
    experience: Optional[Experience] = Field(None, description="Requested cinema experience", examples=["IMAX"])
    radius_km: float = Field(5.0, gt=0, description="Search radius when location is set")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Exact user latitude")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Exact user longitude")


class ScreeningResponse(BaseModel):
    provider: str
    movie: str
    cinema: str
    hall: str
    startTimeUTC: str
    experience: str
    performanceId: str
    bookingUrl: str
    baselinePrice: Optional[float] = None
    seatQuality: Optional[float] = None
    recommendedSeats: List[str] = Field(default_factory=list)
    seatLayout: Optional[List[SeatLayoutRow]] = Field(
        None,
        description="Structured seat data in provider-correct visual order. Missing positions are UNKNOWN.",
    )
    seatStatus: str = "LOADING"


class SearchJobResponse(BaseModel):
    jobId: str = Field(..., description="Search job identifier used for polling")
    status: str = Field(..., description="QUEUED, PROCESSING, COMPLETED, PARTIAL, or FAILED")
    phase: str = Field(..., description="Current search phase")
    completed: int = Field(..., description="Completed seat-enrichment tasks")
    total: int = Field(..., description="Total candidate seat-enrichment tasks")
    screenings: List[ScreeningResponse]
    error: Optional[str] = None
    catalogs: Dict[str, List[str]] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    screenings: List[ScreeningResponse]


class HealthResponse(BaseModel):
    status: str
