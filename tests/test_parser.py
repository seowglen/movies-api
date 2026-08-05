from datetime import date, time
from engine.parser import ParserService

def test_parser_extracts_request_and_fuzzy_matches_title():
    parser = ParserService(catalog_loader=lambda _: ["The Fantastic Four: First Steps"], today=lambda: date(2026, 8, 5))
    request = parser.parse("/movie please show me fantastic four tomorrow after 7pm for 3 people")
    assert request.movie == "The Fantastic Four: First Steps"
    assert request.date == date(2026, 8, 6)
    assert request.after == time(19, 0)
    assert request.pax == 3
