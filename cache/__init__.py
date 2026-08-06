from cachetools import TTLCache

movie_catalog_cache = TTLCache(maxsize=32, ttl=60 * 60)
showtime_cache = TTLCache(maxsize=256, ttl=5 * 60)
seat_layout_cache = TTLCache(maxsize=512, ttl=30)
ticket_price_cache = TTLCache(maxsize=512, ttl=5 * 60)
gv_seatplan_cache = TTLCache(maxsize=512, ttl=30)
