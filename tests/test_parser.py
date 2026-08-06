from datetime import date, time
from engine.parser import ParserService

def test_parser_extracts_request_without_resolving_title():
    parser = ParserService(today=lambda: date(2026, 8, 5))
    request = parser.parse("/movie please show me fantastic four tomorrow after 7pm for 3 people")
    assert request.movie == "fantastic four"
    assert request.date == date(2026, 8, 6)
    assert request.after == time(19, 0)
    assert request.pax == 3


def test_parser_extracts_natural_language_location():
    parser = ParserService(today=lambda: date(2026, 8, 5))
    request = parser.parse("show me spiderman near orchad tomorrow after 7pm")

    assert request.movie == "spiderman"
    assert request.location == "orchad"
    assert request.radius_km == 5.0


def test_parser_supports_short_dates_experience_and_pax():
    parser = ParserService(today=lambda: date(2026, 8, 5))
    request = parser.parse("spiderman tmr after 2pm near orchard imax 3 pax")

    assert request.movie == "spiderman"
    assert request.date == date(2026, 8, 6)
    assert request.after == time(14, 0)
    assert request.location == "orchard"
    assert request.experience == "IMAX"
    assert request.pax == 3


def test_parser_accepts_options_before_and_after_movie():
    parser = ParserService(today=lambda: date(2026, 8, 5))
    request = parser.parse("for 3, spiderman, after 7pm tomorrow")

    assert request.movie == "spiderman"
    assert request.pax == 3
    assert request.after == time(19, 0)
    assert request.date == date(2026, 8, 6)


def test_parser_supports_at_location_and_flexible_time_phrases():
    parser = ParserService(today=lambda: date(2026, 8, 5))

    request = parser.parse("spiderman at orchard at 7pm tomorrow")
    assert request.movie == "spiderman"
    assert request.location == "orchard"
    assert request.after == time(19, 0)

    assert parser.parse("spiderman near vivo 19:00 onwards").after == time(19, 0)


def test_parser_supports_relative_and_weekday_dates():
    parser = ParserService(today=lambda: date(2026, 8, 5))  # Wednesday

    assert parser.parse("odyssey day after tomorrow").date == date(2026, 8, 7)
    assert parser.parse("odyssey in 2 days").date == date(2026, 8, 7)
    assert parser.parse("odyssey next Monday").date == date(2026, 8, 17)
    assert parser.parse("odyssey this Friday").date == date(2026, 8, 7)
    assert parser.parse("odyssey next Friday").date == date(2026, 8, 14)
