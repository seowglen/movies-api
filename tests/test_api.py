from datetime import date, datetime, time

import pytest
from fastapi import HTTPException

from models.screening import Screening
from serve import request_from_payload, screening_response
from serve import app
from utils.pricing import resolve_baseline_price


def test_structured_payload_converts_utc_window_to_singapore_time():
    request = request_from_payload({
        "title": "spiderman",
        "startTimeUTC": "2026-08-07T11:00:00Z",
        "endTimeUTC": "2026-08-07T15:00:00Z",
        "paxCount": 4,
        "location": "ORCHARD",
        "experience": "GOLD_CLASS",
    })

    assert request.movie == "spiderman"
    assert request.date == date(2026, 8, 7)
    assert request.after == time(19, 0)
    assert request.until == time(23, 0)
    assert request.end_date == date(2026, 8, 7)
    assert request.pax == 4
    assert request.location == "ORCHARD"
    assert request.experience == "GOLD CLASS"


def test_structured_payload_rejects_unknown_location():
    with pytest.raises(HTTPException) as error:
        request_from_payload({
            "title": "spiderman",
            "startTimeUTC": "2026-08-07T11:00:00Z",
            "location": "MARS",
        })

    assert error.value.status_code == 422


def test_structured_payload_supports_multiple_dates_without_location():
    request = request_from_payload({
        "title": "spiderman",
        "startTimeUTC": "2026-08-07T11:00:00Z",
        "endTimeUTC": "2026-08-09T15:00:00Z",
        "paxCount": 2,
        "location": None,
    })

    assert request.search_dates == [date(2026, 8, 7), date(2026, 8, 8), date(2026, 8, 9)]


def test_baseline_price_uses_singapore_calendar_bracket():
    assert resolve_baseline_price("shaw", "STANDARD", datetime(2026, 8, 7, 19)) == 15.50


def test_screening_response_uses_explicit_camel_case_and_singapore_time():
    response = screening_response(Screening(
        "shaw", "spiderman", "Lido", "1", datetime(2026, 8, 7, 19), "IMAX", "performance", "url",
        baseline_price=22.0, seat_quality=80.0, recommended_seats=["H10", "H11"], distance_km=1.2, cinema_id="1",
    ))

    assert response["startTimeUTC"] == "2026-08-07T11:00:00Z"
    assert response["provider"] == "SHAW"
    assert response["performanceId"] == "performance"
    assert response["baselinePrice"] == 22.0
    assert response["recommendedSeats"] == ["H10", "H11"]
    assert response["seatLayout"] is None
    assert "cinemaId" not in response
    assert "distanceKm" not in response


def test_openapi_documents_structured_search_contract():
    schema = app.openapi()
    search = schema["paths"]["/search"]["post"]
    payload = schema["components"]["schemas"]["SearchPayload"]
    response = schema["components"]["schemas"]["SearchJobResponse"]

    assert "title" in payload["properties"]
    assert "startTimeUTC" in payload["properties"]
    assert "paxCount" in payload["properties"]
    assert "screenings" in response["properties"]
    assert search["responses"]["202"]["content"]["application/json"]
