from cachetools import TTLCache

movie_catalog_cache = TTLCache(maxsize=32, ttl=60 * 60)
showtime_cache = TTLCache(maxsize=256, ttl=60 * 60)
seat_layout_cache = {}
