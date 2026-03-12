# fmt: off
# ==============================================================================
#  BOOKMYSHOW SYSTEM — ASCII CLASS DIAGRAM
# ==============================================================================
#
#  ┌───────────────────────────────────────────────────────────────────────┐
#  │                      BOOKMYSHOW SYSTEM                                │
#  └───────────────────────────────────────────────────────────────────────┘
#
#  ┌──────────────────────┐         ┌─────────────────────────────┐
#  │     BMSService       │ 1    *  │          Theater            │
#  │      (Facade)        │────────>│─────────────────────────────│
#  ├──────────────────────┤         │ + id, name, city: str       │
#  │ + movies: Dict       │         │ + screens: List[Screen]     │
#  │ + theaters: List     │         │ + shows: List[Show]         │
#  ├──────────────────────┤         ├─────────────────────────────┤
#  │ + add_movie()        │         │ + add_screen()              │
#  │ + add_theater()      │         │ + add_show()                │
#  │ + get_movies_by_city()│        └──────────┬──────────────────┘
#  │ + book_ticket()      │                    │ 1     *
#  │ + confirm_booking()  │                    ▼
#  └──────────┬───────────┘         ┌─────────────────────────────┐
#             │                     │          Screen             │
#             │ 1    *              ├─────────────────────────────┤
#             ▼                     │ + id, name: str             │
#  ┌──────────────────────┐         │ + seats: List[Seat]         │
#  │       Movie          │         ├─────────────────────────────┤
#  ├──────────────────────┤         │ + add_seat()                │
#  │ + id, title: str     │         └──────────┬──────────────────┘
#  │ + duration_mins: int │                    │ 1     *
#  └──────────────────────┘                    ▼
#                               ┌─────────────────────────────┐
#  ┌──────────────────────┐     │            Seat             │
#  │        Show          │ *   ├─────────────────────────────┤
#  ├──────────────────────┤─────│ + id: str                   │
#  │ + show_id: str       │     │ + type: SeatType (enum)     │
#  │ + movie: Movie       │     └─────────────────────────────┘
#  │ + screen: Screen     │              ▲ 1
#  │ + start_time         │              │
#  │ + show_seats: Dict   │     ┌────────┴────────────────────┐
#  ├──────────────────────┤     │         ShowSeat            │
#  │ + get_show_seat()    │────>├─────────────────────────────┤
#  │ + print_available()  │  *  │ + seat: Seat                │
#  └──────────────────────┘     │ + price: float              │
#                               │ + status: SeatStatus(enum)  │
#  ┌──────────────────────┐     │ + lock: Lock                │
#  │       Booking        │     ├─────────────────────────────┤
#  ├──────────────────────┤     │ + is_available(): bool      │
#  │ + booking_id: str    │     │ + reserve(): bool           │
#  │ + user: User         │     │ + confirm()                 │
#  │ + show: Show         │     │ + release()                 │
#  │ + booked_seats[]     │     └─────────────────────────────┘
#  │ + status: Booking..  │
#  │ + total_amount: float│  ┌─────────────────┐
#  ├──────────────────────┤  │      User       │
#  │ + confirm()          │  ├─────────────────┤
#  │ + cancel()           │  │ + id: str       │
#  └──────────────────────┘  │ + name: str     │
#                            └─────────────────┘
#
#  RELATIONSHIPS:
#  BMSService ──*──> Theater       (aggregates theaters)
#  BMSService ──*──> Movie         (aggregates movies)
#  Theater    ──*──> Screen        (owns screens)
#  Theater    ──*──> Show          (schedules shows)
#  Screen     ──*──> Seat          (owns seats)
#  Show ──────────> ShowSeat{}     (wraps each Seat for a show instance)
#  ShowSeat   ──1──> Seat          (mirrors a physical seat)
#  Booking    ──*──> ShowSeat      (books specific show seats)
#  Booking    ──1──> User          (belongs to one user)
#  CONCURRENCY: ShowSeat.lock prevents double-booking (deadlock prevention: sorted order)
# ==============================================================================
# fmt: on
import threading
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

"""
==============================================================================================
BOOKMYSHOW LOW LEVEL DESIGN (INTERVIEW OPTIMIZED)
==============================================================================================

Key Requirements Implemented:
1. Search: Search movies by City.
2. Booking: Select City -> Movie -> Theater -> Show -> Seats.
3. Concurrency: Thread-safe booking with seat-level locks and deadlock prevention.
4. Extensibility: Different Seat Types (Silver, Gold, Platinum).

Design Patterns:
- Facade: BMSService (Central Controller).
- Lock/Synch: For concurrency control at the seat level.

Class Design Diagram:
---------------------
[BMSService] "1" o-- "*" [Theater]
[BMSService] "1" o-- "*" [Movie]
[Theater] "1" *-- "*" [Screen]
[Theater] "1" *-- "*" [Show]
[Screen] "1" *-- "*" [Seat]
[Show] ..> [ShowSeat] : Maps Seat to Status
[ShowSeat] "1" *-- "1" [Seat]
[Booking] "1" *-- "*" [ShowSeat]
[Booking] "1" *-- "1" [User]

Class Details:
---------------------
1. BMSService (Facade)
   - Role: Main controller for the application.
   - Attributes: theaters, movies.
   - Methods: getMoviesByCity(), bookTicket(), confirmBooking().

2. Theater
   - Role: Physical cinema facility.
   - Attributes: id, name, city, screens, shows.

3. Show
   - Role: A specific movie playing at a specific time on a screen.
   - Attributes: movie, screen, startTime, showSeats (Map).

4. ShowSeat
   - Role: Represents a seat instance for a show with status and price.
   - Attributes: seat, status (AVAILABLE/RESERVED/BOOKED), price, lock.
   - Methods: reserve(), confirm(), release().
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
        available = [f"{ss.seat.id}(${ss.price})" for ss in self.show_seats.values() if ss.is_available()]
        print(f"INFO: Available seats for {self.movie.title}: {' '.join(available)}")

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
        print(f"INFO: Booking {self.booking_id} confirmed for {self.user.name}. Total: ${self.total_amount}")

    def cancel(self):
        self.status = BookingStatus.CANCELLED
        for seat in self.booked_seats:
            seat.release()
        print(f"INFO: Booking {self.booking_id} cancelled.")

# ==========================================
# Service Layer (Facade)
# ==========================================

class BMSService:
    def __init__(self):
        self.movies: Dict[str, Movie] = {}
        self.theaters: List[Theater] = []
        print("INFO: BookMyShow Service initialized.")

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
                raise BMSException(f"Seat {sid} does not exist.")
            seats_to_book.append(s_seat)

        # DEADLOCK PREVENTION: Sort by ID for consistent lock order
        seats_to_book.sort(key=lambda s: s.seat.id)

        acquired_locks = []
        try:
            # Phase 1: Acquire Locks
            for sseat in seats_to_book:
                if not sseat.lock.acquire(timeout=5):
                    raise BookingFailedException("System busy, please try again.")
                acquired_locks.append(sseat.lock)

            # Phase 2: Check Availability
            for sseat in seats_to_book:
                if not sseat.is_available():
                    print(f"WARNING: Seat {sseat.seat.id} is no longer available.")
                    raise SeatUnavailableException(f"Seat {sseat.seat.id} is taken.")

            # Phase 3: Reserve
            for sseat in seats_to_book:
                sseat.reserve()

            booking = Booking(user, show, seats_to_book)
            print(f"INFO: Booking {booking.booking_id} created (PENDING).")
            return booking

        finally:
            for lock in reversed(acquired_locks):
                lock.release()

    def confirm_payment_and_booking(self, booking: Booking):
        """Simulate payment and confirm the booking."""
        booking.confirm()

# ==========================================
# Main Execution / Demo
# ==========================================

if __name__ == "__main__":
    print("--- BookMyShow System Design Demo ---")

    bms = BMSService()

    # 1. Setup
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
    print(f"INFO: Movies found: {bms.get_movies_by_city('Bangalore')}")
    show1.print_available_seats()

    # 3. Concurrent Booking Simulation
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

    # 4. Final State
    show1.print_available_seats()
