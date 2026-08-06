from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class MovieCatalog:
    movie_id: object
    title: str
    data: object = None


@dataclass(frozen=True)
class CatalogMatch:
    movie_id: object
    score: float


class MovieSearchProvider(ABC):
    name = "provider"

    @abstractmethod
    def search(self, request, movie_ids=None, catalog=None):
        raise NotImplementedError

    @abstractmethod
    def get_seat_layout(self, performance_id):
        raise NotImplementedError

    @abstractmethod
    def get_ticket_price(self, performance_id):
        raise NotImplementedError

    def catalog(self, target_date):
        return []
