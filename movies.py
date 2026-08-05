import argparse
import requests
import re
from datetime import datetime, date as dt_date

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "priority": "u=1, i",
    "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
    "x-api-forward-to": "internal",
    "x-app": "PWSM"
}


def clean_string(text):
    """Removes non-breaking spaces (\xa0) and normalizes whitespace."""
    if not text:
        return ""
    # Replace unicode non-breaking space with regular space
    text = str(text).replace("\xa0", " ").replace("\u00a0", " ")
    return " ".join(text.split()).strip()


def parse_show_datetime(date_str, time_str):
    """Safely converts date and time strings into a datetime object."""
    if not time_str:
        return None

    for raw in [time_str, f"{date_str} {time_str}"]:
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            pass

    formats = [
        "%Y-%m-%d %I:%M %p",
        "%Y-%m-%d %I:%M%p",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%I:%M %p",
        "%I:%M%p",
        "%H:%M"
    ]

    full_str = f"{date_str} {time_str}".strip()
    for fmt in formats:
        try:
            return datetime.strptime(full_str, fmt)
        except ValueError:
            continue

    return None


def detect_experience_type(movie_brand, show_item):
    """Detects experience type from movie brand, hall, or title."""
    brand = str(movie_brand or "").upper()
    hall = str(show_item.get("hallName") or show_item.get("hall") or "").upper()

    combined = f"{brand} {hall}"

    if "IMAX" in combined:
        return "IMAX"
    elif "PREMIERE" in combined:
        return "PREMIERE"
    elif "LUMIERE" in combined:
        return "LUMIERE"

    return "STANDARD"


def search_showtimes(title, date=None, location=None, experience=None, time=None, debug=False):
    now = datetime.now()
    target_date = date if date else now.strftime("%Y-%m-%d")
    is_today = (target_date == now.strftime("%Y-%m-%d"))

    url = f"https://shaw.sg/internal/get_show_times?date={target_date}&movieId=0&locationId=0&promotionId=0&locationBrand=0"

    if debug:
        print(f"\n[DEBUG] Requesting URL: {url}")

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            print(f"⚠️ Shaw API returned HTTP status {response.status_code}.")
            return [], target_date

        res = response.json()
    except Exception as e:
        print(f"⚠️ Request failed: {e}")
        return [], target_date

    # Standardize response (can be direct list or wrapped object)
    if isinstance(res, dict):
        movies_list = res.get("showtimes") or res.get("data") or res.get("movies") or []
    elif isinstance(res, list):
        movies_list = res
    else:
        movies_list = []

    results = []
    search_keyword = clean_string(title).lower()

    for movie in movies_list:
        if not isinstance(movie, dict):
            continue

        raw_title = movie.get("primaryTitle") or movie.get("title") or ""
        movie_title = clean_string(raw_title)
        movie_brand = movie.get("movieBrand", "")

        if search_keyword not in movie_title.lower():
            continue

        raw_shows = movie.get("showTimes") or movie.get("showtimes") or []

        if debug:
            print(f"[DEBUG] Found {len(raw_shows)} raw showtime slot(s) for '{movie_title}'")

        for idx, show in enumerate(raw_shows):
            if not isinstance(show, dict):
                continue

            # Key extraction based on Shaw's JSON structure
            cinema_name = clean_string(
                show.get("locationVenueName") or 
                show.get("cinemaName") or 
                show.get("locationName") or 
                "Shaw Cinema"
            )

            show_time = clean_string(
                show.get("displayTime") or show.get("showTime") or ""
            )

            show_date = show.get("displayDate") or target_date
            perf_id = show.get("performanceId") or show.get("id")
            
            # Detect experience type (e.g., IMAX, Lumiere, 2D)
            exp_type = detect_experience_type(
                show.get("brandCode") or show.get("locationVenueBrandCode") or movie_brand, 
                show
            )

            show_dt = parse_show_datetime(target_date, show_time)

            if is_today and show_dt and show_dt < now:
                continue

            # Location filtering
            if location and clean_string(location).lower() not in cinema_name.lower():
                if debug and idx < 3:
                    print(f"[DEBUG] Filtered location: '{cinema_name}' does not match '{location}'")
                continue

            # Experience filtering
            if experience and experience.upper() != exp_type:
                if debug and idx < 3:
                    print(f"[DEBUG] Filtered experience: '{exp_type}' does not match '{experience}'")
                continue

            # Time filtering
            if time and not show_time.startswith(time):
                continue

            if not perf_id:
                continue

            results.append({
                "performanceId": perf_id,
                "movie": movie_title,
                "cinema": cinema_name,
                "hall": cinema_name,  # locationVenueName already contains hall/cinema info (e.g., 'Lido IMAX')
                "experience": exp_type,
                "time": show_time,
                "date": show_date,
                "datetime": show_dt
            })

    # Sort showtimes chronologically
    results.sort(key=lambda x: x["datetime"] if x["datetime"] else datetime.max)

    return results, target_date


def render_terminal_seat_map(performance_id, use_emojis=True, debug=False):
    url = f"https://shaw.sg/internal/get_layouts?performanceId={performance_id}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            print(f"⚠️ Could not fetch layout (HTTP Status {response.status_code})")
            return
        res = response.json()
    except Exception as e:
        print(f"⚠️ Error fetching layout for performanceId {performance_id}: {e}")
        return

    seats_data = res
    if not seats_data:
        print(f"⚠️ No seat layout available for ID: {performance_id}\n")
        return

    rows = {}
    available_count = 0
    total_seats = 0
    max_seat_number = 0

    for idx, seat in enumerate(seats_data):
        row_label = clean_string(seat.get("rowReference") or seat.get("row") or "").upper()
        col_label = clean_string(seat.get("columnReference") or seat.get("col") or "")
        if not row_label or not col_label:
            continue
        if row_label not in rows:
            rows[row_label] = {}

        cat_code = str(seat.get("elementCategoryCode") or "").upper()
        if not cat_code or cat_code != "SEAT":
            continue

        total_seats += 1
        
        # Ignore wheelchair seats
        elem_code = seat.get("elementCode")
        if elem_code == "EL_HDS":
            continue

        col_idx = int(col_label)
        max_seat_number = max(max_seat_number, col_idx)
        is_available = str(seat.get("elementStatusCodeCurrent")) == "AV"
        if is_available:
            available_count += 1
        rows[row_label][col_idx] = is_available

    avail_symbol = "🟩" if use_emojis else "[ ]"
    taken_symbol = "🟥" if use_emojis else "[X]"
    gap_symbol   = "  " if use_emojis else "   "

    print("  [ S C R E E N ]")
    print("  " + "-" * max_seat_number * 2)
    for row_name in sorted(rows.keys(), reverse=True):
        cols = rows[row_name]
        row_str = f"{row_name:>2} | "

        for col in range(max_seat_number, 0, -1):
            if col in cols:
                row_str += avail_symbol if cols[col] else taken_symbol
            else:
                row_str += gap_symbol

        print(row_str)

    print(f"\n📊 Available Seats: {available_count} / {total_seats}")
    print(f"🔑 Legend: {avail_symbol} Open | {taken_symbol} Occupied/Held")
    print(f"Book now: https://shaw.sg/showtimes/{performance_id}")
    print("=" * 100 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Search Shaw Cinema showtimes and display live seat maps.")

    parser.add_argument("title", type=str, help="Movie title keyword (e.g. 'odyssey')")
    parser.add_argument("-d", "--date", type=str, help="Date YYYY-MM-DD (defaults to today)")
    parser.add_argument("-l", "--location", type=str, help="Cinema location filter (e.g. 'lido')")
    parser.add_argument("-e", "--experience", type=str, choices=["IMAX", "PREMIERE", "LUMIERE", "STANDARD"])
    parser.add_argument("-t", "--time", type=str, help="Showtime prefix")
    parser.add_argument("--no-emoji", action="store_true", help="Use ASCII symbols instead of emojis")
    parser.add_argument("--debug", "-db", action="store_true", help="Enable debug prints")

    args = parser.parse_args()

    print(f"🔍 Searching showtimes for '{args.title}'...")

    shows, target_date = search_showtimes(
        title=args.title,
        date=args.date,
        location=args.location,
        experience=args.experience,
        time=args.time,
        debug=args.debug
    )

    if not shows:
        print(f"❌ No matching showtimes found for '{args.title}' on {target_date}.")
        return

    print(f"\n🎬 Found {len(shows)} upcoming showtime(s) on {target_date}:\n")

    for i, s in enumerate(shows, 1):
        print("=" * 100)
        print(f" SHOW {i}/{len(shows)}: {s['movie']} [{s['experience']}]")
        print(f" 📍 {s['cinema']} ({s['hall']})")
        print(f" ⏰ {s['time']} | Date: {s['date']} | ID: {s['performanceId']}")
        print("=" * 100)

        render_terminal_seat_map(s["performanceId"], use_emojis=not args.no_emoji, debug=args.debug)


if __name__ == "__main__":
    main()