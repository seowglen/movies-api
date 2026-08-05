from providers.gv import GVSearchProvider
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
        {"rowId": "A", "columnId": "01", "colNumber": 1, "status": "L"},
        {"rowId": None, "columnId": None, "colNumber": 2, "status": None},
        {"rowId": "A", "columnId": "02", "colNumber": 3, "status": "B"},
    ]]}
    provider = GVSearchProvider(session=Session(payload))

    layout = provider.get_seat_layout("114|1424|05-08-2026|1735|4")

    assert layout.valid
    assert layout.available
    assert layout.occupied
    assert Seat("A", 2) not in layout.valid
