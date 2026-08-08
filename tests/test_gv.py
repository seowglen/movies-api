from datetime import date, datetime

from providers.gv import GVSearchProvider, SINGAPORE_TZ
from models.seat_layout import Seat


class Response:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


class Session:
    def __init__(self, data):
        self.data = data

    def post(self, *args, **kwargs):
        return Response(self.data)


def test_gv_seat_layout_uses_non_null_grid_cells_as_valid_seats():
    payload = {"success": True, "errorMessage": None, "data": [[
        {"rowId": "A", "columnId": "01", "colNumber": 1, "status": "L", "type": "N"},
        {"rowId": None, "columnId": None, "colNumber": 2, "status": None},
        {"rowId": "A", "columnId": "02", "colNumber": 3, "status": "B", "type": "N"},
    ]]}
    provider = GVSearchProvider(session=Session(payload))

    layout = provider.get_seat_layout("114|1424|05-08-2026|1735|4")

    assert layout.valid
    assert layout.available
    assert layout.occupied
    assert Seat("A", 2) not in layout.valid


def test_gv_wheelchair_seat_is_not_recommended_even_when_available():
    payload = {"success": True, "errorMessage": None, "data": [[
        {"rowId": "A", "columnId": "01", "colNumber": 1, "status": "L", "type": "W"},
        {"rowId": "A", "columnId": "02", "colNumber": 2, "status": "L", "type": "N"},
    ]]}
    layout = GVSearchProvider(session=Session(payload)).get_seat_layout("114|1424|05-08-2026|1736|4")

    assert Seat("A", 1) not in layout.available
    assert Seat("A", 2) in layout.available


def test_gv_day_timestamp_is_interpreted_in_singapore_time():
    timestamp_ms = 1786377600000  # 2026-08-11 00:00 Singapore time

    assert datetime.fromtimestamp(timestamp_ms / 1000, SINGAPORE_TZ).date() == date(2026, 8, 11)
