import re
from datetime import date, datetime, time, timedelta
import dateparser
from rapidfuzz import fuzz, process
from models.search_request import SearchRequest

class ParserService:
    def __init__(self, catalog_loader=None, today=None):
        self.catalog_loader = catalog_loader or (lambda target: [])
        self.today = today or date.today
    def parse(self, query):
        text = " ".join(query.split()); target_date = self._extract_date(text)
        titles = list(self.catalog_loader(target_date))
        return SearchRequest(self._match_title(self._movie_hint(text), titles), target_date, self._extract_time(text), self._extract_pax(text))
    def _extract_date(self, text):
        today = self.today()
        if "tomorrow" in text.casefold(): return today + timedelta(days=1)
        explicit = re.search(r"\b(?:on\s+)?(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*(?:\s+\d{4})?)\b", text, re.I)
        if explicit:
            parsed = dateparser.parse(explicit.group(1), settings={"RELATIVE_BASE": datetime.combine(today, time.min), "PREFER_DATES_FROM": "future"})
            if parsed:
                return parsed.date()
        parsed = dateparser.parse(text, settings={"RELATIVE_BASE": datetime.combine(today, time.min), "PREFER_DATES_FROM": "future"})
        return parsed.date() if parsed else today
    def _extract_time(self, text):
        match = re.search(r"\b(?:after|from)\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\b", text, re.I)
        parsed = dateparser.parse(match.group(1)) if match else None
        return parsed.time().replace(second=0, microsecond=0) if parsed else None
    def _extract_pax(self, text):
        match = re.search(r"\bfor\s+(\d+)\s*(?:people|pax|persons?|tickets?)?\b", text, re.I)
        return int(match.group(1)) if match else 2
    def _movie_hint(self, text):
        value = re.sub(r"^\s*(?:/movie|movie)\s+", "", text, flags=re.I)
        value = re.sub(r"^\s*(?:please\s+)?(?:show(?:\s+me)?|find|can\s+i\s+watch)\s+", "", value, flags=re.I)
        return re.sub(r"\b(?:today|tomorrow|(?:on\s+)?\d{1,2}\s+\w+(?:\s+\d{4})?|after|from|for)\b.*$", "", value, flags=re.I).strip(" ,.-") or text
    @staticmethod
    def _match_title(hint, titles):
        if not titles: return hint.title()
        match = process.extractOne(hint, titles, scorer=fuzz.WRatio, score_cutoff=55)
        return match[0] if match else hint.title()
