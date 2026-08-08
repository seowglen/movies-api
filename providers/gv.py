"""Golden Village API adapter, using curl_cffi for its browser TLS fingerprint."""
from datetime import datetime, timedelta, timezone
import logging

from curl_cffi import requests

from cache import showtime_cache
from models.screening import Screening
from models.seat_layout import Seat, SeatLayout
from providers.base import MovieCatalog, MovieSearchProvider
from utils.constants import GV_CINEMAS


BASE_URL = "https://www.gv.com.sg/.gv-api"
SINGAPORE_TZ = timezone(timedelta(hours=8))
logger = logging.getLogger(__name__)
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
        return [MovieCatalog(film["filmCd"], film["filmTitle"], film) for film in self._films()]

    def search(self, request, movie_ids=None, catalog=None):
        results = []
        films = [entry.data for entry in catalog] if catalog is not None else self._films()
        for film in films:
            if movie_ids is not None and film["filmCd"] not in movie_ids:
                continue
            try:
                results.extend(self._screenings(film, request))
            except Exception:
                logger.exception("GV screening lookup failed for film %s", film.get("filmCd"))
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
                if item["status"] == "L" and item.get("type") == "N":
                    layout.available.add(seat)
                else:
                    layout.occupied.add(seat)
        return layout

    def _films(self):
        # TODO: put homeadvancesales if necessary
        films = {}
        for film in self._post("homenowshowing", None, referer="https://www.gv.com.sg/")["data"]:
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
        session_data = self._session_for_film(film["filmCd"])
        if not session_data or not isinstance(session_data, dict):
            logger.warning("GV returned no session data for film %s", film.get("filmCd"))
            return []
        screenings = []
        now = datetime.now()
        for location in session_data.get("locations") or []:
            cinema = self.cinemas.get(location["id"], location["name"])
            for day in location["dates"]:
                show_date = datetime.fromtimestamp(day["date"] / 1000, SINGAPORE_TZ).date()
                if show_date != request.date:
                    continue
                for show in day["times"]:
                    time24 = str(show["time24"]).zfill(4)
                    starts_at = datetime.combine(show_date, datetime.strptime(time24, "%H%M").time())
                    experience = self._experience(cinema)
                    if starts_at < now:
                        continue
                    if request.after and starts_at.time() < request.after:
                        continue
                    if request.until and starts_at.time() > request.until:
                        continue
                    if request.experience and request.experience.upper() != experience:
                        continue
                    performance_id = "|".join((location["id"], film["filmCd"], starts_at.strftime("%d-%m-%Y"), show["time24"], show["hallNumber"]))
                    booking_url = (
                        "https://www.gv.com.sg/GVSeatSelection#/cinemaId/%s/filmCode/%s/"
                        "showDate/%s/showTime/%s/hallNumber/%s"
                    ) % (location["id"], film["filmCd"], starts_at.strftime("%d-%m-%Y"), show["time24"], show["hallNumber"])
                    screenings.append(Screening(self.name, film["filmTitle"], cinema, "Hall %s" % show["hallNumber"], starts_at, experience, performance_id, booking_url, cinema_id=location["id"]))
        return screenings

    def _session_for_film(self, film_code):
        key = (self.name, "film", film_code)
        if key in showtime_cache:
            return showtime_cache[key]
        session_data = self._post(
            "sessionforfilm",
            {"filmCode": film_code},
            referer="https://www.gv.com.sg/GVMovieDetails",
        )["data"]
        showtime_cache[key] = session_data
        return session_data

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
