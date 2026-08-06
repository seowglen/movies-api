import math

from rapidfuzz import fuzz, process

DEFAULT_RADIUS_KM = 5.0

# User-entered areas, malls, MRT stations, and districts. These are search
# anchors, not cinema coordinates.
LOCATION_ALIASES = {
    "aljunied": (1.3164, 103.8829),
    "ang mo kio": (1.3691, 103.8454),
    "bishan": (1.3508, 103.8485),
    "bedok": (1.3240, 103.9300),
    "bugis": (1.2992, 103.8553),
    "bukit batok": (1.3496, 103.7494),
    "bukit panjang": (1.3786, 103.7644),
    "bukit timah": (1.3294, 103.8021),
    "city hall": (1.2931, 103.8520),
    "city square": (1.3112, 103.8567),
    "changi": (1.3644, 103.9915),
    "choa chu kang": (1.3840, 103.7470),
    "chinatown": (1.2838, 103.8436),
    "cineleisure": (1.3025, 103.8360),
    "clementi": (1.3151, 103.7652),
    "dhoby ghaut": (1.2997, 103.8455),
    "downtown east": (1.3770, 103.9553),
    "eunos": (1.3198, 103.9036),
    "funan": (1.2925, 103.8509),
    "geylang": (1.3182, 103.8871),
    "great world": (1.2937, 103.8317),
    "harbourfront": (1.2644, 103.8222),
    "holland village": (1.3112, 103.7964),
    "hougang": (1.3612, 103.8863),
    "j8": (1.3508, 103.8485),
    "jcube": (1.3331, 103.7423),
    "jurong": (1.3343, 103.7422),
    "jurong east": (1.3331, 103.7423),
    "kallang": (1.3117, 103.8714),
    "katong": (1.3054, 103.9049),
    "kent ridge": (1.2936, 103.7800),
    "lido": (1.3048, 103.8318),
    "lot one": (1.3854, 103.7440),
    "marina bay": (1.2868, 103.8545),
    "marine parade": (1.3020, 103.9077),
    "marymount": (1.3483, 103.8391),
    "novena": (1.3201, 103.8439),
    "one north": (1.2997, 103.7875),
    "orchard": (1.3048, 103.8318),
    "pasir ris": (1.3721, 103.9474),
    "pasir panjang": (1.2760, 103.7910),
    "paya lebar": (1.3181, 103.8921),
    "punggol": (1.4052, 103.9020),
    "queenstown": (1.2942, 103.7861),
    "raffles place": (1.2840, 103.8510),
    "redhill": (1.2895, 103.8168),
    "sembawang": (1.4491, 103.8185),
    "sengkang": (1.3868, 103.8914),
    "serangoon": (1.3554, 103.8679),
    "seletar mall": (1.3925, 103.8767),
    "seletar": (1.3925, 103.8767),
    "suntec": (1.2959, 103.8586),
    "tampines": (1.3530, 103.9451),
    "tanjong pagar": (1.2762, 103.8458),
    "telok blangah": (1.2707, 103.8098),
    "toa payoh": (1.3343, 103.8563),
    "upper thomson": (1.3548, 103.8330),
    "vivocity": (1.2644, 103.8222),
    "woodlands": (1.4382, 103.7890),
    "yishun": (1.4291, 103.8354),
}


# Actual cinema coordinates keyed by provider and provider cinema ID.
CINEMA_COORDINATES = {
    ("gv", "01"): (1.4291, 103.8354),
    ("gv", "02"): (1.3508, 103.8485),
    ("gv", "04"): (1.3399, 103.7068),
    ("gv", "05"): (1.2644, 103.8222),
    ("gv", "07"): (1.2937, 103.8317),
    ("gv", "08"): (1.3350, 103.8698),
    ("gv", "09"): (1.3530, 103.9451),
    ("gv", "10"): (1.3054, 103.9049),
    ("gv", "11"): (1.3112, 103.8567),
    ("gv", "12"): (1.2959, 103.8586),
    ("gv", "13"): (1.3181, 103.8921),
    ("gv", "14"): (1.3240, 103.9300),
    ("gv", "15"): (1.2925, 103.8509),
    ("gv", "15C"): (1.2925, 103.8509),
    ("gv", "15E"): (1.2925, 103.8509),
    ("gv", "17"): (1.2992, 103.8553),
    ("gv", "18"): (1.3025, 103.8360),
    ("gv", "19"): (1.3770, 103.9553),
    ("gv", "22"): (1.3530, 103.9451),
    ("gv", "40"): (1.2992, 103.8553),
    ("gv", "50"): (1.2644, 103.8222),
    ("gv", "051"): (1.2644, 103.8222),
    ("gv", "051*"): (1.2644, 103.8222),
    ("gv", "60"): (1.3054, 103.9049),
    ("gv", "70"): (1.2937, 103.8317),
    ("gv", "80"): (1.2959, 103.8586),
    ("gv", "114"): (1.3112, 103.8567),
    ("gv", "122"): (1.2959, 103.8586),
    ("gv", "131"): (1.3181, 103.8921),
    ("shaw", "1"): (1.3048, 103.8318),
    ("shaw", "3"): (1.3260, 103.8500),
    ("shaw", "4"): (1.3854, 103.7440),
    ("shaw", "5"): (1.3535, 103.8675),
    ("shaw", "7"): (1.4052, 103.9020),
    ("shaw", "8"): (1.3600, 103.9890),
    ("shaw", "9"): (1.3181, 103.8921),
    ("shaw", "13"): (1.3331, 103.7423),
}


# Temporary fallback for providers whose API record has no stable cinema ID.
# Replace entries with provider IDs as those IDs are confirmed.
CINEMA_NAME_COORDINATES = {
    "bedok": (1.3240, 103.9300),
    "bishan": (1.3508, 103.8485),
    "bugis": (1.2992, 103.8553),
    "city square": (1.3112, 103.8567),
    "cineleisure": (1.3025, 103.8360),
    "downtown east": (1.3770, 103.9553),
    "funan": (1.2925, 103.8509),
    "great world": (1.2937, 103.8317),
    "j8": (1.3508, 103.8485),
    "jcube": (1.3331, 103.7423),
    "jurong point": (1.3399, 103.7068),
    "katong": (1.3054, 103.9049),
    "lido": (1.3048, 103.8318),
    "lot one": (1.3854, 103.7440),
    "paya lebar": (1.3181, 103.8921),
    "plaza": (1.2997, 103.8455),
    "seletar": (1.3925, 103.8767),
    "suntec": (1.2959, 103.8586),
    "tampines": (1.3530, 103.9451),
    "vivocity": (1.2644, 103.8222),
    "waterway": (1.4052, 103.9020),
    "yishun": (1.4291, 103.8354),
}


def resolve_location(value):
    if not value:
        return None
    normalized = " ".join(value.casefold().split())
    if normalized in LOCATION_ALIASES:
        return LOCATION_ALIASES[normalized]
    for alias, coordinates in LOCATION_ALIASES.items():
        if alias in normalized:
            return coordinates
    match = process.extractOne(normalized, LOCATION_ALIASES.keys(), scorer=fuzz.WRatio, score_cutoff=78)
    if match:
        return LOCATION_ALIASES[match[0]]
    return None


def cinema_coordinates(provider, name, cinema_id=None):
    if cinema_id is not None:
        coordinates = CINEMA_COORDINATES.get((provider.casefold(), str(cinema_id)))
        if coordinates:
            return coordinates
    normalized = name.casefold()
    for alias, coordinates in CINEMA_NAME_COORDINATES.items():
        if alias in normalized:
            return coordinates
    return None


def distance_km(first, second):
    latitude1, longitude1 = map(math.radians, first)
    latitude2, longitude2 = map(math.radians, second)
    delta_latitude = latitude2 - latitude1
    delta_longitude = longitude2 - longitude1
    value = (
        math.sin(delta_latitude / 2) ** 2
        + math.cos(latitude1) * math.cos(latitude2) * math.sin(delta_longitude / 2) ** 2
    )
    return 6371.0 * 2 * math.asin(math.sqrt(value))
