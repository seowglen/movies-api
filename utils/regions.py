REGIONS = {
    "CENTRAL": {
        "name": "Central", "latitude": 1.3117, "longitude": 103.8414,
        "areas": {
            "ORCHARD": ("Orchard", 1.3048, 103.8318), "SOMERSET": ("Somerset", 1.3005, 103.8392),
            "DHOBY_GHAUT": ("Dhoby Ghaut", 1.2990, 103.8457), "BUGIS": ("Bugis", 1.3007, 103.8557),
            "CITY_HALL": ("City Hall", 1.2931, 103.8520), "MARINA_BAY": ("Marina Bay", 1.2834, 103.8607),
            "TANJONG_PAGAR": ("Tanjong Pagar", 1.2763, 103.8437), "CHINATOWN": ("Chinatown", 1.2839, 103.8447),
            "TIONG_BAHRU": ("Tiong Bahru", 1.2868, 103.8274), "GREAT_WORLD": ("Great World", 1.2935, 103.8335),
            "HOLLAND_VILLAGE": ("Holland Village", 1.3121, 103.7964), "QUEENSTOWN": ("Queenstown", 1.2940, 103.8060),
            "NOVENA": ("Novena", 1.3201, 103.8439), "TOA_PAYOH": ("Toa Payoh", 1.3340, 103.8560),
            "BISHAN": ("Bishan", 1.3509, 103.8485), "HARBOURFRONT": ("HarbourFront", 1.2645, 103.8223),
            "SENTOSA": ("Sentosa", 1.2494, 103.8303),
        },
    },
    "EAST": {
        "name": "East", "latitude": 1.3496, "longitude": 103.9444,
        "areas": {
            "PAYA_LEBAR": ("Paya Lebar", 1.3186, 103.8920), "KALLANG": ("Kallang", 1.3115, 103.8717),
            "KATONG": ("Katong", 1.3045, 103.9017), "EAST_COAST": ("East Coast", 1.3036, 103.9105),
            "MARINE_PARADE": ("Marine Parade", 1.3027, 103.9074), "BEDOK": ("Bedok", 1.3236, 103.9273),
            "SIMEI": ("Simei", 1.3437, 103.9534), "TAMPINES": ("Tampines", 1.3530, 103.9451),
            "PASIR_RIS": ("Pasir Ris", 1.3730, 103.9493), "CHANGI": ("Changi", 1.3570, 103.9870),
        },
    },
    "NORTH_EAST": {
        "name": "North-East", "latitude": 1.3850, "longitude": 103.8870,
        "areas": {
            "ANG_MO_KIO": ("Ang Mo Kio", 1.3691, 103.8454), "SERANGOON": ("Serangoon", 1.3496, 103.8737),
            "KOVAN": ("Kovan", 1.3602, 103.8851), "HOUGANG": ("Hougang", 1.3736, 103.8867),
            "BUANGKOK": ("Buangkok", 1.3828, 103.8930), "SENGKANG": ("Sengkang", 1.3917, 103.8955),
            "PUNGGOL": ("Punggol", 1.4051, 103.9023), "SELETAR": ("Seletar", 1.4044, 103.8670),
        },
    },
    "NORTH": {
        "name": "North", "latitude": 1.4300, "longitude": 103.8250,
        "areas": {
            "YISHUN": ("Yishun", 1.4294, 103.8354), "KHATIB": ("Khatib", 1.4174, 103.8329),
            "CANBERRA": ("Canberra", 1.4431, 103.8299), "SEMBAWANG": ("Sembawang", 1.4450, 103.8185),
            "WOODLANDS": ("Woodlands", 1.4360, 103.7865), "MARSILING": ("Marsiling", 1.4322, 103.7744),
            "MANDAI": ("Mandai", 1.4043, 103.7909),
        },
    },
    "WEST": {
        "name": "West", "latitude": 1.3400, "longitude": 103.7500,
        "areas": {
            "BUONA_VISTA": ("Buona Vista", 1.3075, 103.7900), "BEAUTY_WORLD": ("Beauty World", 1.3412, 103.7758),
            "BUKIT_PANJANG": ("Bukit Panjang", 1.3774, 103.7719), "CHOA_CHU_KANG": ("Choa Chu Kang", 1.3840, 103.7440),
            "BUKIT_BATOK": ("Bukit Batok", 1.3490, 103.7490), "TENGAH": ("Tengah", 1.3618, 103.7380),
            "CLEMENTI": ("Clementi", 1.3151, 103.7650), "WEST_COAST": ("West Coast", 1.3048, 103.7640),
            "JURONG_EAST": ("Jurong East", 1.3331, 103.7420), "JURONG_WEST": ("Jurong West", 1.3500, 103.6990),
            "BOON_LAY": ("Boon Lay", 1.3386, 103.7066),
        },
    },
}


def location_codes():
    codes = {}
    for region, data in REGIONS.items():
        codes["SG_%s" % region] = (data["name"], data["latitude"], data["longitude"], "REGION")
        for area, (name, latitude, longitude) in data["areas"].items():
            codes["SG_%s_%s" % (region, area)] = (name, latitude, longitude, "AREA")
    return codes
