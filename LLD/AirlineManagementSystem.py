# fmt: off
# ==============================================================================
#  AIRLINE MANAGEMENT SYSTEM — ASCII CLASS DIAGRAM
# ==============================================================================
#
#  ┌──────────────────────────────────────────────────────────────────────────┐
#  │                   AIRLINE MANAGEMENT SYSTEM                              │
#  └──────────────────────────────────────────────────────────────────────────┘
#
#  ┌─────────────────┐    1    ┌─────────────────────────────────────────────┐
#  │  AirlineSystem  │────────>│                  Flight                     │
#  │   (Facade)      │  *      ├─────────────────────────────────────────────┤
#  ├─────────────────┤         │ + flight_number: str                        │
#  │ + flights[]     │         │ + source: Airport                           │
#  │ + bookings{}    │         │ + destination: Airport                      │
#  │ + passengers{}  │         │ + date: datetime                            │
#  ├─────────────────┤         │ + aircraft: Aircraft                        │
#  │ + add_flight()  │         │ + base_price: float                         │
#  │ + search()      │         │ + seats: Dict[str, Seat]                    │
#  │+create_booking()│         │ - _lock: Lock                               │
#  └─────────────────┘         ├─────────────────────────────────────────────┤
#           │                  │ + calculate_price(n) : float                │
#           │                  │ + book_seats(nos[]) : bool                  │
#           │ creates          │ + get_total_seats() : int                   │
#           ▼                  │ + get_booked_seats() : int                  │
#  ┌─────────────────┐         └──────────────┬──────────────────────────────┘
#  │    Booking      │                        │ 1                  │ 1
#  ├─────────────────┤         uses           ▼                    ▼
#  │ + booking_id    │  ──────────────> ┌──────────────┐  ┌────────────────┐
#  │ + flight        │                  │ PricingStrat.│  │   Aircraft     │
#  │ + passenger     │                  │  (ABC/Iface) │  ├────────────────┤
#  │ + seats[]       │                  ├──────────────┤  │ + tail_number  │
#  │ + amount        │                  │+calc_price() │  │ + model        │
#  │ + meal_pref     │                  └──────┬───────┘  │ + capacity     │
#  ├─────────────────┤                         │          └────────────────┘
#  │ + confirm()     │                  ┌──────┴──────┐
#  │+set_meal_pref() │                  │             │
#  └────────┬────────┘          ┌───────┴──┐  ┌──────┴──────────┐
#           │ 1                 │  Static  │  │    Dynamic      │
#           ▼                   │  Pricing │  │    Pricing      │
#  ┌─────────────────┐          │ (1.0x)   │  │(1.0/1.1/1.5x)  │
#  │  Passenger      │          └──────────┘  └─────────────────┘
#  │   (User)        │
#  ├─────────────────┤  ┌──────────────────────┐   ┌──────────────────┐
#  │ + id: str       │  │   PaymentProcessor   │   │   MealType       │
#  │ + name: str     │  │   (ABC/Interface)    │   │   (Enum)         │
#  │ + passport: str │  ├──────────────────────┤   ├──────────────────┤
#  └─────────────────┘  │ + process(amt): bool │   │  STANDARD / VEG  │
#          ▲            └──────────┬───────────┘   │  NON_VEG/KOSHER  │
#          │                       │               │  HALAL           │
#  ┌───────┴──────┐       ┌────────┴────────┐      └──────────────────┘
#  │    User      │       │CreditCardPayment│
#  ├──────────────┤       └─────────────────┘
#  │ + id: str    │
#  │ + name: str  │     ┌──────────────┐  ┌─────────────────────┐
#  └──────────────┘     │   Airport    │  │       Seat          │
#                       ├──────────────┤  ├─────────────────────┤
#                       │ + code: str  │  │ + seat_number: str  │
#                       │ + city: str  │  │ + is_booked: bool   │
#                       └──────────────┘  └─────────────────────┘
#
#  RELATIONSHIPS:
#  AirlineSystem ──*──> Flight         (aggregation, manages many flights)
#  Flight        ──1──> Aircraft       (composition, owns one aircraft)
#  Flight        ──*──> Seat           (composition, owns many seats)
#  Flight        ──1──> PricingStrategy(uses strategy for pricing)
#  Booking       ──1──> Flight         (references a flight)
#  Booking       ──1──> Passenger      (belongs to one passenger)
#  Passenger     ──▷──  User           (inheritance)
#  AirlineSystem ──> PaymentProcessor  (uses via createBooking)
#  StaticPricing ──▷── PricingStrategy (implements)
#  DynamicPricing──▷── PricingStrategy (implements)
# ==============================================================================
# fmt: on
import threading
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

"""
==============================================================================================
AIRLINE MANAGEMENT SYSTEM LOW LEVEL DESIGN (INTERVIEW OPTIMIZED)
==============================================================================================

Key Features Implemented:
1. Search: Search flights by Source, Destination, Date.
2. Booking: Seat seection, Booking creation, Payment processing.
3. Management: Flights, Passengers (Admin/Service).
4. Extensibility: Dynamic Pricing Strategy, Meal Selection.
5. Concurrency: Thread-safe seat booking using Locks.

Design Patterns:
1. Facade: AirlineSystem (Central Controller).
2. Strategy: PricingStrategy (Dynamic/Static), PaymentProcessor (CreditCard).
3. State: Handled via status attributes.

Class Design Diagram:
---------------------
[AirlineSystem] "1" *-- "*" [Airline]
[Airline] "1" *-- "*" [Flight]
[Flight] "1" *-- "1" [Aircraft]
[Flight] "1" *-- "*" [Seat]
[Flight] "1" *-- "1" [PricingStrategy]
[Booking] "1" *-- "1" [Flight]
[Booking] "1" *-- "*" [Seat]
[Booking] "1" *-- "1" [Passenger]
[Booking] ..> [PaymentProcessor] : Uses
[Booking] ..> [MealType] : Has
[User] <|-- [Passenger]

Class Details:
---------------------
1. AirlineSystem (Facade)
   - Role: Main controller.
   - Methods: searchFlights(), createBooking().

2. Flight
   - Role: Represents a scheduled journey.
   - Attributes: flightNumber, source, dest, date, seats, pricingStrategy.
   - Methods: calculatePrice(), bookSeats().

3. Seat
   - Attributes: seatNumber, isBooked.

4. PricingStrategy (Interface)
   - Role: Calculate price based on demand/time.
   - Impls: StaticPricing, DynamicPricing.

5. PaymentProcessor (Interface)
   - Role: Handle payments.
"""

# ==========================================
# Exceptions
# ==========================================

class AirlineException(Exception):
    """Base exception for Airline System."""
    pass

class SeatUnavailableException(AirlineException):
    """Raised when selected seats are not available."""
    pass

class PaymentFailedException(AirlineException):
    """Raised when payment processing fails."""
    pass

# ==========================================
# Enums & Interfaces
# ==========================================

class MealType(Enum):
    STANDARD = "STANDARD"
    VEG = "VEG"
    NON_VEG = "NON_VEG"
    KOSHER = "KOSHER"
    HALAL = "HALAL"

class PricingStrategy(ABC):
    """Strategy for calculating flight prices."""
    @abstractmethod
    def calculate_price(self, flight: 'Flight', seat_count: int) -> float:
        pass

class PaymentProcessor(ABC):
    """Interface for payment processing."""
    @abstractmethod
    def process(self, amount: float) -> bool:
        pass

# ==========================================
# Domain Models
# ==========================================

class User:
    def __init__(self, user_id: str, name: str):
        self.id = user_id
        self.name = name

class Passenger(User):
    def __init__(self, user_id: str, name: str, passport_number: str):
        super().__init__(user_id, name)
        self.passport_number = passport_number

class Airport:
    def __init__(self, code: str, city: str):
        self.code = code
        self.city = city

class Aircraft:
    def __init__(self, tail_number: str, model: str, capacity: int):
        self.tail_number = tail_number
        self.model = model
        self.capacity = capacity

class Seat:
    def __init__(self, seat_number: str):
        self.seat_number = seat_number
        self.is_booked = False

class StaticPricingStrategy(PricingStrategy):
    def calculate_price(self, flight: 'Flight', seat_count: int) -> float:
        return flight.base_price * seat_count

class DynamicPricingStrategy(PricingStrategy):
    """
    Calculates price based on demand (occupancy).
    - > 50% occupancy: 1.5x price
    - > 0% occupancy: 1.1x price
    """
    def calculate_price(self, flight: 'Flight', seat_count: int) -> float:
        total = flight.get_total_seats()
        booked = flight.get_booked_seats()
        ratio = booked / total if total > 0 else 0
        multiplier = 1.5 if ratio > 0.5 else (1.1 if booked > 0 else 1.0)
        return flight.base_price * multiplier * seat_count

class CreditCardPayment(PaymentProcessor):
    def process(self, amount: float) -> bool:
        print(f"INFO: Processing Credit Card Payment: ${amount:.2f}")
        return True

class Booking:
    def __init__(self, booking_id: str, flight: 'Flight', passenger: Passenger, seats: List[str], amount: float):
        self.booking_id = booking_id
        self.flight = flight
        self.passenger = passenger
        self.seats = seats
        self.amount = amount
        self.status = "PENDING"
        self.meal_preference = MealType.STANDARD

    def confirm(self):
        self.status = "CONFIRMED"
        print(f"INFO: Booking {self.booking_id} confirmed for {self.passenger.name}")

    def set_meal_preference(self, meal: MealType):
        self.meal_preference = meal
        print(f"INFO: Meal set to {meal.value} for booking {self.booking_id}")

class Flight:
    def __init__(self, flight_number: str, source: Airport, destination: Airport,
                 date: datetime, aircraft: Aircraft, pricing_strategy: PricingStrategy):
        self.flight_number = flight_number
        self.source = source
        self.destination = destination
        self.date = date
        self.aircraft = aircraft
        self.pricing_strategy = pricing_strategy
        self.base_price = 1000.0
        self.seats: Dict[str, Seat] = {}
        self._lock = threading.Lock()

        # Initialize seats based on aircraft capacity
        for i in range(1, aircraft.capacity + 1):
            self.seats[f"{i}A"] = Seat(f"{i}A")
            if i <= aircraft.capacity // 2:
                self.seats[f"{i}B"] = Seat(f"{i}B")

    def calculate_price(self, seat_count: int) -> float:
        return self.pricing_strategy.calculate_price(self, seat_count)

    def book_seats(self, seat_nos: List[str]) -> bool:
        """Atomically book a list of seats."""
        with self._lock:
            for no in seat_nos:
                seat = self.seats.get(no)
                if not seat or seat.is_booked:
                    print(f"WARNING: Seat {no} unavailable on {self.flight_number}")
                    return False
            for no in seat_nos:
                self.seats[no].is_booked = True
            print(f"INFO: Seats {seat_nos} reserved on {self.flight_number}")
            return True

    def get_total_seats(self) -> int:
        return len(self.seats)

    def get_booked_seats(self) -> int:
        return sum(1 for s in self.seats.values() if s.is_booked)

# ==========================================
# System Facade
# ==========================================

class AirlineSystem:
    def __init__(self):
        self.flights: List[Flight] = []
        self.bookings: Dict[str, Booking] = {}
        self.passengers: Dict[str, Passenger] = {}
        print("INFO: AirlineSystem initialized.")

    def add_flight(self, flight: Flight):
        self.flights.append(flight)
        print(f"INFO: Flight {flight.flight_number} added.")

    def register_passenger(self, passenger: Passenger):
        self.passengers[passenger.id] = passenger

    def search_flights(self, src_code: str, dst_code: str) -> List[Flight]:
        return [f for f in self.flights
                if f.source.code == src_code and f.destination.code == dst_code]

    def create_booking(self, passenger: Passenger, flight: Flight,
                       seat_nos: List[str], payment: PaymentProcessor) -> Booking:
        """Books seats, processes payment, and confirms the booking."""
        if passenger.id not in self.passengers:
            self.register_passenger(passenger)

        if not flight.book_seats(seat_nos):
            raise SeatUnavailableException(f"Seats {seat_nos} are unavailable.")

        price = flight.calculate_price(len(seat_nos))
        if not payment.process(price):
            raise PaymentFailedException("Payment failed.")

        booking = Booking(str(uuid.uuid4()), flight, passenger, seat_nos, price)
        booking.confirm()
        self.bookings[booking.booking_id] = booking
        return booking

# ==========================================
# Main Execution / Demo
# ==========================================

if __name__ == "__main__":
    print("--- Airline Management System Demo ---")

    system = AirlineSystem()

    # 1. Setup
    boeing = Aircraft("AC1", "Boeing 737", 10)
    del_apt = Airport("DEL", "New Delhi")
    sfo_apt = Airport("SFO", "San Francisco")
    f1 = Flight("FL001", del_apt, sfo_apt, datetime.now(), boeing, DynamicPricingStrategy())
    system.add_flight(f1)

    # 2. Search
    print("[Passenger] Searching DEL -> SFO")
    results = system.search_flights("DEL", "SFO")
    if not results:
        print("No flights found.")
    else:
        flight = results[0]
        print(f"Found: {flight.flight_number} | Base Price: ${flight.base_price}")

        # 3. Booking (Passenger 1)
        p1 = Passenger("P1", "Rahul", "passport123")
        payment = CreditCardPayment()
        try:
            price = flight.calculate_price(2)
            print(f"Dynamic price for 2 seats: ${price:.2f}")
            b1 = system.create_booking(p1, flight, ["1A", "1B"], payment)
            print(f"Booking ID: {b1.booking_id}")
            b1.set_meal_preference(MealType.VEG)
        except AirlineException as e:
            print(f"ERROR: {e}")

        # 4. Booking (Passenger 2) - Dynamic price should increase
        p2 = Passenger("P2", "Sita", "passport456")
        try:
            price = flight.calculate_price(1)
            print(f"Dynamic price for 1 seat (P2): ${price:.2f}")
            b2 = system.create_booking(p2, flight, ["2A"], payment)
            print(f"Booking ID: {b2.booking_id}")
        except AirlineException as e:
            print(f"ERROR: {e}")
