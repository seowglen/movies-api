"""Shaw Cinema API adapter."""
from datetime import datetime

import requests

from models.screening import Screening
from models.seat_layout import Seat, SeatLayout
from providers.base import MovieSearchProvider


HEADERS = {
    "accept": "application/json, text/plain, */*",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/150.0.0.0 Safari/537.36",
    "x-api-forward-to": "internal",
    "x-app": "PWSM",
}


class ShawSearchProvider(MovieSearchProvider):
    name = "shaw"
    base_url = "https://shaw.sg/internal"

    def __init__(self, session=None):
        self.session = session or requests.Session()

    def catalog(self, target_date):
        return [movie["primaryTitle"] for movie in self._movies(target_date)]

    def search(self, request):
        results = []
        now = datetime.now()

        for movie in self._movies(request.date):
            title = movie["primaryTitle"]
            if request.movie.casefold() not in title.casefold():
                continue

            for show in movie["showTimes"]:
                starts_at = datetime.strptime(
                    "%s %s" % (show["displayDate"], show["displayTime"]),
                    "%Y-%m-%d %I:%M %p",
                )
                cinema = show["locationVenueName"]
                experience = self._experience(show["brandCode"], cinema)

                if starts_at < now or (request.after and starts_at.time() < request.after):
                    continue
                if request.location and request.location.casefold() not in cinema.casefold():
                    continue
                if request.experience and request.experience.upper() != experience:
                    continue

                performance_id = str(show["performanceId"])
                results.append(Screening(
                    provider=self.name,
                    movie=title,
                    cinema=cinema,
                    hall=cinema,
                    datetime=starts_at,
                    experience=experience,
                    performance_id=performance_id,
                    booking_url="https://shaw.sg/showtimes/%s" % performance_id,
                ))
        return results

    def get_seat_layout(self, performance_id):
        response = self.session.get(
            self.base_url + "/get_layouts",
            params={"performanceId": performance_id},
            headers=HEADERS,
            timeout=15,
        )
        response.raise_for_status()

        layout = SeatLayout()
        for element in response.json():
            if element["elementCategoryCode"] != "SEAT" or element["elementCode"] == "EL_HDS":
                continue

            seat = Seat(element["rowReference"], int(element["columnReference"]))
            layout.rows.setdefault(seat.row, []).append(seat.number)
            layout.valid.add(seat)
            if element["elementStatusCodeCurrent"] == "AV":
                layout.available.add(seat)
            else:
                layout.occupied.add(seat)
        return layout

    def get_ticket_price(self, performance_id):
        response = self.session.get(
            self.base_url + "/api/v2/performances/%s/ticket_types" % performance_id,
            headers=dict(HEADERS, referer="https://shaw.sg/showtimes/%s" % performance_id),
            timeout=15,
        )
        response.raise_for_status()
        adult = next((ticket for ticket in response.json() if ticket.get("ticketType", "").casefold() == "adult"), None)
        return float(adult["salesAmount"]) if adult else None

    def _movies(self, target_date):
        response = self.session.get(
            self.base_url + "/get_show_times",
            params={
                "date": target_date.isoformat(),
                "movieId": 0,
                "locationId": 0,
                "promotionId": 0,
                "locationBrand": 0,
            },
            headers=HEADERS,
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _experience(brand_code, cinema):
        text = "%s %s" % (brand_code, cinema)
        for name in ("IMAX", "PREMIERE", "LUMIERE"):
            if name in text.upper():
                return name
        return "STANDARD"
