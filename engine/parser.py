import re
from datetime import date, datetime, time, timedelta
import dateparser
from models.search_request import SearchRequest

class ParserService:
    def __init__(self, today=None):
        self.today = today or date.today
    def parse(self, query):
        text = " ".join(query.split()); target_date = self._extract_date(text)
        location = self._extract_location(text)
        movie_text = self._without_location(text)
        return SearchRequest(
            self._movie_hint(movie_text), target_date, self._extract_time(text), self._extract_pax(text),
            location=location, experience=self._extract_experience(text),
        )
    def _extract_date(self, text):
        today = self.today()
        if re.search(r"\bday after tomorrow\b", text, re.I): return today + timedelta(days=2)
        in_days = re.search(r"\bin\s+(\d+)\s+days?\b", text, re.I)
        if in_days: return today + timedelta(days=int(in_days.group(1)))
        weekday = re.search(r"\b(next|this)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", text, re.I)
        if weekday:
            target = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday").index(weekday.group(2).casefold())
            days_ahead = (target - today.weekday()) % 7
            if weekday.group(1).casefold() == "next": days_ahead += 7
            return today + timedelta(days=days_ahead)
        if re.search(r"\b(?:tomorrow|tmr|tmrw)\b", text, re.I): return today + timedelta(days=1)
        explicit = re.search(r"\b(?:on\s+)?(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*(?:\s+\d{4})?)\b", text, re.I)
        if explicit:
            parsed = dateparser.parse(explicit.group(1), settings={"RELATIVE_BASE": datetime.combine(today, time.min), "PREFER_DATES_FROM": "future"})
            if parsed:
                return parsed.date()
        parsed = dateparser.parse(text, settings={"RELATIVE_BASE": datetime.combine(today, time.min), "PREFER_DATES_FROM": "future"})
        return parsed.date() if parsed else today
    def _extract_time(self, text):
        match = re.search(r"\b(?:after|from|at)\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\b|\b(\d{1,2}:\d{2}|\d{1,2}\s*(?:am|pm))\s*(?:onwards|and\s+later)?\b", text, re.I)
        value = (match.group(1) or match.group(2)) if match else None
        parsed = dateparser.parse(value) if value else None
        return parsed.time().replace(second=0, microsecond=0) if parsed else None
    def _extract_pax(self, text):
        match = re.search(r"\bfor\s+(\d+)\b|\b(\d+)\s*(?:pax|people|persons?|tickets?)\b", text, re.I)
        return int(match.group(1) or match.group(2)) if match else 2
    def _extract_location(self, text):
        match = re.search(self._location_pattern(), text, re.I)
        return match.group(1).strip(" ,.-") if match else None
    def _without_location(self, text):
        return re.sub(self._location_pattern(), "", text, flags=re.I).strip()
    def _extract_experience(self, text):
        match = re.search(r"\b(?:in\s+)?(imax|atmos|premiere|lumiere|gold\s*class|gv\s*max|gvm?ax|standard)\b", text, re.I)
        if not match:
            return None
        value = re.sub(r"\s+", " ", match.group(1).casefold())
        return {"goldclass": "GOLD CLASS", "gv max": "GVMAX", "gvmax": "GVMAX", "gmax": "GVMAX"}.get(value, value.upper())
    @staticmethod
    def _location_pattern():
        stop = r"day\s+after\s+tomorrow|in\s+\d+\s+days?|(?:next|this)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|today|tomorrow|tmr|tmrw|(?:after|from|at)\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?|\d{1,2}:\d{2}\s*(?:onwards|and\s+later)?|\d{1,2}\s*(?:am|pm)\s*(?:onwards|and\s+later)?|after|from|for|(?:in\s+)?(?:imax|atmos|premiere|lumiere|gold\s*class|gv\s*max|gvm?ax|standard)"
        location = r"(?:near|around|at)\s+(?!\d{1,2}(?::\d{2})?\s*(?:am|pm)\b)"
        return r"\b%s(.+?)(?=\s+\b(?:%s)\b|$)" % (location, stop)
    def _movie_hint(self, text):
        value = re.sub(r"^\s*(?:/movie|movie)\s+", "", text, flags=re.I)
        value = re.sub(r"^\s*(?:please\s+)?(?:show(?:\s+me)?|find|can\s+i\s+watch)\s+", "", value, flags=re.I)
        value = re.sub(r"\b(?:after|from|at)\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?\b|\b\d{1,2}:\d{2}\s*(?:onwards|and\s+later)?\b|\b\d{1,2}\s*(?:am|pm)\s*(?:onwards|and\s+later)?\b", "", value, flags=re.I)
        value = re.sub(r"\bfor\s+\d+\s*(?:pax|people|persons?|tickets?)?\b", "", value, flags=re.I)
        value = re.sub(r"\b(?:in\s+)?(?:imax|atmos|premiere|lumiere|gold\s*class|gv\s*max|gvm?ax|standard)\b", "", value, flags=re.I)
        value = re.sub(r"\b(?:day\s+after\s+tomorrow|in\s+\d+\s+days?|(?:next|this)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|today|tomorrow|tmr|tmrw|(?:on\s+)?\d{1,2}\s+\w+(?:\s+\d{4})?)\b", "", value, flags=re.I)
        return re.sub(r"\s+", " ", value).strip(" ,.-") or text
