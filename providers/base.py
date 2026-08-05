from abc import ABC, abstractmethod


class MovieSearchProvider(ABC):
    name = "provider"

    @abstractmethod
    def search(self, request):
        raise NotImplementedError

    @abstractmethod
    def get_seat_layout(self, performance_id):
        raise NotImplementedError

    @abstractmethod
    def get_ticket_price(self, performance_id):
        raise NotImplementedError

    def catalog(self, target_date):
        return []
