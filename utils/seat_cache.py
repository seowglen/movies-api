from datetime import datetime, timedelta, timezone


SINGAPORE_TZ = timezone(timedelta(hours=8))


def seat_layout_ttl(showtime, now=None):
    if showtime.tzinfo is None:
        showtime = showtime.replace(tzinfo=SINGAPORE_TZ)
    else:
        showtime = showtime.astimezone(SINGAPORE_TZ)
    now = now or datetime.now(SINGAPORE_TZ)
    hours_until_showtime = (showtime - now).total_seconds() / 3600.0
    if hours_until_showtime <= 2:
        return 30
    if hours_until_showtime <= 24:
        return 3 * 60
    return 15 * 60
