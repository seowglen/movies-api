from datetime import timedelta, timezone


SG_TZ = timezone(timedelta(hours=8))

CINEMA_PRICING_MATRIX = {
    "GV": {
        "STANDARD": {"weekday_mon_wed": 10.00, "weekday_thu": 10.50, "weekend_fri_sun_ph": 14.50},
        "DELUXE": {"weekday_mon_wed": 13.00, "weekday_thu": 13.00, "weekend_fri_sun_ph": 18.00},
        "GEMINI": {"weekday_mon_wed": 13.00, "weekday_thu": 13.00, "weekend_fri_sun_ph": 18.00},
        "GVMAX": {"weekday_mon_wed": 12.00, "weekday_thu": 12.00, "weekend_fri_sun_ph": 16.50},
        "GOLD_CLASS": {"weekday_mon_wed": 35.00, "weekday_thu": 35.00, "weekend_fri_sun_ph": 45.00},
        "AURO": {"weekday_mon_wed": 12.00, "weekday_thu": 12.00, "weekend_fri_sun_ph": 16.50},
    },
    "SHAW": {
        "STANDARD": {"weekday_mon_wed": 11.00, "weekday_thu": 11.50, "weekend_fri_sun_ph": 15.50},
        "IMAX": {"weekday_mon_wed": 22.00, "weekday_thu": 22.00, "weekend_fri_sun_ph": 25.00},
        "LUMIERE": {"weekday_mon_wed": 25.00, "weekday_thu": 25.00, "weekend_fri_sun_ph": 30.00},
        "PREMIERE": {"weekday_mon_wed": 30.00, "weekday_thu": 30.00, "weekend_fri_sun_ph": 35.00},
    },
}

SINGAPORE_PUBLIC_HOLIDAYS = {
    "2026-01-01", "2026-02-17", "2026-02-18", "2026-03-21", "2026-04-03", "2026-05-01",
    "2026-05-27", "2026-05-31", "2026-06-01", "2026-08-09", "2026-08-10", "2026-11-08",
    "2026-11-09", "2026-12-25", "2027-01-01", "2027-02-06", "2027-02-07", "2027-02-08",
    "2027-03-10", "2027-03-26", "2027-05-01", "2027-05-17", "2027-05-20", "2027-08-09",
    "2027-10-28", "2027-12-25", "2028-01-01", "2028-01-26", "2028-01-27", "2028-02-27",
    "2028-02-28", "2028-04-14", "2028-05-01", "2028-05-05", "2028-05-09", "2028-08-09",
    "2028-10-17", "2028-12-25",
}


def resolve_baseline_price(cinema_chain, experience_type, showtime):
    chain = cinema_chain.upper()
    experience = experience_type.upper().replace(" ", "_")
    if chain not in CINEMA_PRICING_MATRIX:
        raise ValueError("Unsupported cinema chain: %s" % cinema_chain)
    if experience not in CINEMA_PRICING_MATRIX[chain]:
        raise ValueError("Experience %s is not supported by %s" % (experience_type, cinema_chain))

    if showtime.tzinfo is None:
        showtime = showtime.replace(tzinfo=SG_TZ)
    else:
        showtime = showtime.astimezone(SG_TZ)
    date_key = showtime.strftime("%Y-%m-%d")
    weekday = showtime.weekday()
    if date_key in SINGAPORE_PUBLIC_HOLIDAYS or weekday in (5, 6):
        bracket = "weekend_fri_sun_ph"
    elif weekday == 4:
        bracket = "weekend_fri_sun_ph" if showtime.hour >= 18 else "weekday_thu"
    elif weekday == 3:
        bracket = "weekday_thu"
    else:
        bracket = "weekday_mon_wed"
    return CINEMA_PRICING_MATRIX[chain][experience][bracket]
