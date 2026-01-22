import threading
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set

"""
==============================================================================================
BOOKMYSHOW LOW LEVEL DESIGN (PYTHON - PRODUCTION GRADE)
==============================================================================================

Key Requirements Implemented:
1. Search: Search movies by City.
2. Booking: Select City -> Movie -> Theater -> Show -> Seats.
3. Concurrency: Thread-safe booking with granular seat-level locks and deadlock prevention.
4. Extensibility: Different Seat Types (Silver, Gold, Platinum).
5. Robustness: Logging, custom exceptions, and type hinting.

Design Patterns:
- Singleton: BMSService (Facade).
- Lock/Synch: For concurrency control at the seat level.
"""

# ==========================================
# Exceptions
# ==========================================

class BMSException(Exception):
    """Base exception for BookMyShow System."""
    pass

class SeatUnavailableException(BMSException):
    """Raised when one or more seats are unavailable."""
    pass

class BookingFailedException(BMSException):
    """Raised when the booking transaction fails."""
    pass

# ==========================================
# Enums
# ==========================================

class SeatType(Enum):
    SILVER = "SILVER"
    GOLD = "GOLD"
    PLATINUM = "PLATINUM"

class SeatStatus(Enum):
    AVAILABLE = "AVAILABLE"
    BOOKED = "BOOKED"
    RESERVED = "RESERVED"

class BookingStatus(Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"

# ==========================================
# Domain Models
# ==========================================

class User:
    def __init__(self, user_id: str, name: str):
        self.id = user_id
        self.name = name

class Movie:
    def __init__(self, movie_id: str, title: str, duration_mins: int):
        self.id = movie_id
        self.title = title
        self.duration_mins = duration_mins

    def __repr__(self):
        return f"Movie({self.title})"

class Seat:
    def __init__(self, seat_id: str, seat_type: SeatType):
        self.id = seat_id
        self.type = seat_type

class Screen:
    def __init__(self, screen_id: str, name: str):
        self.id = screen_id
        self.name = name
        self.seats: List[Seat] = []

    def add_seat(self, seat: Seat):
        self.seats.append(seat)

class ShowSeat:
    """Represents a specific seat instance for a show."""
    def __init__(self, seat: Seat, price: float):
        self.seat = seat
        self.price = price
        self.status = SeatStatus.AVAILABLE
        self.lock = threading.Lock()

    def is_available(self) -> bool:
        return self.status == SeatStatus.AVAILABLE

    def reserve(self) -> bool:
        if self.status == SeatStatus.AVAILABLE:
            self.status = SeatStatus.RESERVED
            return True
        return False

    def confirm(self):
        if self.status == SeatStatus.RESERVED:
            self.status = SeatStatus.BOOKED

    def release(self):
        if self.status == SeatStatus.RESERVED:
            self.status = SeatStatus.AVAILABLE

class Show:
    def __init__(self, show_id: str, movie: Movie, screen: Screen, start_time: datetime):
        self.show_id = show_id
        self.movie = movie
        self.screen = screen
        self.start_time = start_time
        self.show_seats: Dict[str, ShowSeat] = {}
        self._initialize_seats()

    def _initialize_seats(self):
        for seat in self.screen.seats:
            price = 200.0 if seat.type == SeatType.GOLD else 100.0
            self.show_seats[seat.id] = ShowSeat(seat, price)

    def get_show_seat(self, seat_id: str) -> Optional[ShowSeat]:
        return self.show_seats.get(seat_id)

    def print_available_seats(self):
        print(f"INFO: Checking available seats for {self.movie.title}:")
        available = [f"{ss.seat.id}(${ss.price})" for ss in self.show_seats.values() if ss.is_available()]
        print("INFO: Available: " + " ".join(available))

class Theater:
    def __init__(self, theater_id: str, name: str, city: str):
        self.id = theater_id
        self.name = name
        self.city = city
        self.screens: List[Screen] = []
        self.shows: List[Show] = []

    def add_screen(self, screen: Screen):
        self.screens.append(screen)

    def add_show(self, show: Show):
        self.shows.append(show)

class Booking:
    def __init__(self, user: User, show: Show, booked_seats: List[ShowSeat]):
        self.booking_id = str(uuid.uuid4())
        self.user = user
        self.show = show
        self.booked_seats = booked_seats
        self.status = BookingStatus.PENDING
        self.total_amount = sum(s.price for s in booked_seats)

    def confirm(self):
        self.status = BookingStatus.CONFIRMED
        for seat in self.booked_seats:
            seat.confirm()
        print(f"INFO: Booking {self.booking_id} confirmed for {self.user.name}")

    def cancel(self):
        self.status = BookingStatus.CANCELLED
        for seat in self.booked_seats:
            seat.release()
        print(f"INFO: Booking {self.booking_id} cancelled.")

# ==========================================
# Service Layer (Singleton)
# ==========================================

class BMSService:
    _instance = None
    _singleton_lock = threading.Lock()

    def __new__(cls):
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = super(BMSService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.movies: Dict[str, Movie] = {}
        self.theaters: List[Theater] = []
        self._initialized = True
        print("INFO: BookMyShow Service Facade initialized.")

    @classmethod
    def get_instance(cls):
        return cls()

    def add_movie(self, movie: Movie):
        self.movies[movie.id] = movie

    def add_theater(self, theater: Theater):
        self.theaters.append(theater)

    def get_movies_by_city(self, city: str) -> List[Movie]:
        movies = set()
        for t in self.theaters:
            if t.city.lower() == city.lower():
                for s in t.shows:
                    movies.add(s.movie)
        return list(movies)

    def book_ticket(self, user: User, show: Show, seat_ids: List[str]) -> Booking:
        """
        Transactional seat booking with deadlock prevention.
        Seats are sorted by ID to ensure consistent lock acquisition order.
        """
        seats_to_book: List[ShowSeat] = []
        for sid in seat_ids:
            s_seat = show.get_show_seat(sid)
            if not s_seat:
                raise BMSException(f"Seat {sid} does not exist for this show.")
            seats_to_book.append(s_seat)

        # DEADLOCK PREVENTION: Sort seats by ID to maintain consistent locking order
        seats_to_book.sort(key=lambda s: s.seat.id)

        acquired_locks = []
        try:
            # Phase 1: Acquire Locks
            for sseat in seats_to_book:
                if not sseat.lock.acquire(timeout=5):
                    print(f"ERROR: Failed to acquire lock for seat {sseat.seat.id}")
                    raise BookingFailedException("System busy, please try again.")
                acquired_locks.append(sseat.lock)

            # Phase 2: Check Availability
            for sseat in seats_to_book:
                if not sseat.is_available():
                    print(f"WARNING: Seat {sseat.seat.id} is no longer available.")
                    raise SeatUnavailableException(f"Seat {sseat.seat.id} is already taken.")

            # Phase 3: Selection/Reservation
            for sseat in seats_to_book:
                sseat.reserve()

            booking = Booking(user, show, seats_to_book)
            print(f"INFO: Booking {booking.booking_id} created in PENDING state.")
            return booking

        finally:
            # Phase 4: Release Locks
            for lock in reversed(acquired_locks):
                lock.release()

    def confirm_payment_and_booking(self, booking: Booking):
        """Simulate payment success and confirm the booking."""
        # In a real system, verify payment status here
        booking.confirm()

# ==========================================
# Main Execution
# ==========================================

if __name__ == "__main__":
    print("--- BookMyShow System Design Demo ---")

    bms = BMSService.get_instance()

    # 1. Setup Data
    m1 = Movie("M1", "Inception", 148)
    bms.add_movie(m1)

    t1 = Theater("T1", "PVR Cinemas", "Bangalore")
    screen1 = Screen("S1", "Screen 1")
    for i in range(1, 6):
        screen1.add_seat(Seat(f"A{i}", SeatType.SILVER))
    for i in range(1, 6):
        screen1.add_seat(Seat(f"B{i}", SeatType.GOLD))
    t1.add_screen(screen1)
    bms.add_theater(t1)

    show1 = Show("SHOW1", m1, screen1, datetime.now())
    t1.add_show(show1)

    # 2. Search
    print("[User] Searching movies in Bangalore...")
    movies_found = bms.get_movies_by_city("Bangalore")
    print(f"INFO: Movies found: {movies_found}")

    # 3. View Seats
    show1.print_available_seats()

    # 4. Concurrent Booking Simulation
    user_a = User("U1", "Alice")
    user_b = User("U2", "Bob")

    def alice_task():
        try:
            print("INFO: Alice attempting to book A1, A2")
            booking = bms.book_ticket(user_a, show1, ["A1", "A2"])
            bms.confirm_payment_and_booking(booking)
        except BMSException as e:
            print(f"ERROR: Alice's booking failed: {e}")

    def bob_task():
        try:
            print("INFO: Bob attempting to book A1, B1")
            booking = bms.book_ticket(user_b, show1, ["A1", "B1"])
            bms.confirm_payment_and_booking(booking)
        except BMSException as e:
            print(f"ERROR: Bob's booking failed: {e}")

    t_alice = threading.Thread(target=alice_task)
    t_bob = threading.Thread(target=bob_task)

    t_alice.start()
    t_bob.start()

    t_alice.join()
    t_bob.join()

    # 5. Final State
    show1.print_available_seats()
