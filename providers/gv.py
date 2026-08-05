"""Golden Village API adapter, using curl_cffi for its browser TLS fingerprint."""
from datetime import datetime

from curl_cffi import requests

from models.screening import Screening
from models.seat_layout import Seat, SeatLayout
from providers.base import MovieSearchProvider
from utils.constants import GV_CINEMAS


BASE_URL = "https://www.gv.com.sg/.gv-api"
HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json; charset=UTF-8",
    "x_developer": "ENOVAX",
}


class GVSearchProvider(MovieSearchProvider):
    name = "gv"

    def __init__(self, session=None):
        self.session = session or requests.Session(impersonate="chrome120")
        self.cinemas = GV_CINEMAS

    def catalog(self, target_date):
        return [film["filmTitle"] for film in self._films()]

    def search(self, request):
        results = []
        for film in self._films():
            if request.movie.casefold() not in film["filmTitle"].casefold():
                continue
            results.extend(self._screenings(film, request))
        return results

    def get_seat_layout(self, performance_id):
        data = self._seatplan(performance_id)

        layout = SeatLayout(enforce_no_single_seat=True)
        for row in data:
            for item in row:
                if item["rowId"] is None or item["columnId"] is None:
                    continue
                seat = Seat(item["rowId"], item["colNumber"])
                layout.rows.setdefault(seat.row, []).append(seat.number)
                layout.valid.add(seat)
                if item["status"] == "L":
                    layout.available.add(seat)
                else:
                    layout.occupied.add(seat)
        return layout

    def get_ticket_price(self, performance_id):
        cinema_id, film_code, show_date, show_time, hall_number = performance_id.split("|")
        seat = next(
            item for row in self._seatplan(performance_id) for item in row
            if item["rowId"] is not None and item["columnId"] is not None and item["status"] == "L"
        )
        data = self._post("getticketprice", {
            "cinemaId": cinema_id,
            "filmCode": film_code,
            "showDate": show_date,
            "showTime": show_time,
            "hallNumber": hall_number,
            "sectionId": seat["sectionId"],
            "seatType": seat["type"],
            "sms": False,
        }, referer="https://www.gv.com.sg/GVSeatSelection")["data"]
        adult = next((ticket for ticket in data["tickets"] if ticket["type"] == "ADULT"), None)
        return float(adult["discountPrice"]) if adult else None

    def _films(self):
        films = {}
        for endpoint in ("homenowshowing", "homeadvancesales"):
            for film in self._post(endpoint, None, referer="https://www.gv.com.sg/")["data"]:
                films[film["filmCd"]] = film
        return list(films.values())

    def _seatplan(self, performance_id):
        cinema_id, film_code, show_date, show_time, hall_number = performance_id.split("|")
        return self._post("seatplan", {
            "cinemaId": cinema_id,
            "filmCode": film_code,
            "showDate": show_date,
            "showTime": show_time,
            "hallNumber": hall_number,
        }, referer="https://www.gv.com.sg/GVSeatSelection")["data"]

    def _screenings(self, film, request):
        session_data = self._post(
            "sessionforfilm",
            {"filmCode": film["filmCd"]},
            referer="https://www.gv.com.sg/GVMovieDetails",
        )["data"]
        screenings = []
        for location in session_data["locations"]:
            cinema = self.cinemas.get(location["id"], location["name"])
            if request.location and request.location.casefold() not in cinema.casefold():
                continue
            for day in location["dates"]:
                show_date = datetime.fromtimestamp(day["date"] / 1000).date()
                if show_date != request.date:
                    continue
                for show in day["times"]:
                    starts_at = datetime.combine(show_date, datetime.strptime(show["time24"], "%H%M").time())
                    experience = self._experience(cinema)
                    if request.after and starts_at.time() < request.after:
                        continue
                    if request.experience and request.experience.upper() != experience:
                        continue
                    performance_id = "|".join((location["id"], film["filmCd"], starts_at.strftime("%d-%m-%Y"), show["time24"], show["hallNumber"]))
                    booking_url = (
                        "https://www.gv.com.sg/GVSeatSelection#/cinemaId/%s/filmCode/%s/"
                        "showDate/%s/showTime/%s/hallNumber/%s"
                    ) % (location["id"], film["filmCd"], starts_at.strftime("%d-%m-%Y"), show["time24"], show["hallNumber"])
                    screenings.append(Screening(self.name, film["filmTitle"], cinema, "Hall %s" % show["hallNumber"], starts_at, experience, performance_id, booking_url))
        return screenings

    def _post(self, endpoint, payload, referer):
        response = self.session.post(
            BASE_URL + "/" + endpoint,
            headers=dict(HEADERS, referer=referer),
            json=payload,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        if not data["success"]:
            raise RuntimeError(data["errorMessage"] or "GV API request failed")
        return data

    @staticmethod
    def _experience(cinema):
        cinema = cinema.upper()
        for name in ("GOLD CLASS", "GVMAX", "DELUXE", "GEMINI", "AURO"):
            if name in cinema:
                return name
        return "STANDARD"
