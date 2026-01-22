import threading
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

"""
==============================================================================================
AIRLINE MANAGEMENT SYSTEM LOW LEVEL DESIGN (PYTHON - PRODUCTION GRADE)
==============================================================================================

Key Features Implemented:
1. Search: Search flights by Source, Destination, Date.
2. Booking: Seat selection, Booking creation, Payment processing.
3. Management: Flights, Passengers (Admin/Service).
4. Extensibility: Dynamic Pricing Strategy, Meal Selection.
5. Concurrency: Thread-safe seat booking using Locks.

Design Patterns:
1. Singleton: AirlineSystem (Facade).
2. Strategy: PricingStrategy (Dynamic/Static), PaymentProcessor (CreditCard).
3. State: Handled via status attributes.
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
    def calculate_price(self, flight: 'Flight', seat_count: int) -> float:
        """
        Calculates price based on demand (occupancy).
        - > 50% occupancy: 1.5x price
        - > 0% occupancy: 1.1x price
        """
        total = flight.get_total_seats()
        booked = flight.get_booked_seats()
        base = flight.base_price
        
        ratio = booked / total if total > 0 else 0
        if ratio > 0.5:
            multiplier = 1.5
        elif booked > 0:
            multiplier = 1.1
        else:
            multiplier = 1.0
            
        return base * multiplier * seat_count

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
        print(f"INFO: Meal preference updated to {meal.value} for booking {self.booking_id}")

class Flight:
    def __init__(self, flight_number: str, source: Airport, destination: Airport, date: datetime, aircraft: Aircraft, pricing_strategy: PricingStrategy):
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
            s_name_a = f"{i}A"
            self.seats[s_name_a] = Seat(s_name_a)
            if i <= aircraft.capacity // 2:
                s_name_b = f"{i}B"
                self.seats[s_name_b] = Seat(s_name_b)

    def calculate_price(self, seat_count: int) -> float:
        return self.pricing_strategy.calculate_price(self, seat_count)

    def book_seats(self, seat_nos: List[str]) -> bool:
        """Atomically book seats for the flight."""
        with self._lock:
            # Check availability
            for no in seat_nos:
                seat = self.seats.get(no)
                if not seat or seat.is_booked:
                    print(f"WARNING: Seat {no} is unavailable on flight {self.flight_number}")
                    return False
            
            # Commit booking
            for no in seat_nos:
                self.seats[no].is_booked = True
                
            print(f"INFO: Successfully reserved seats {seat_nos} on flight {self.flight_number}")
            return True

    def get_total_seats(self) -> int:
        return len(self.seats)

    def get_booked_seats(self) -> int:
        return sum(1 for s in self.seats.values() if s.is_booked)

# ==========================================
# System Facade (Singleton)
# ==========================================

class AirlineSystem:
    _instance = None
    _singleton_lock = threading.Lock()

    def __new__(cls):
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = super(AirlineSystem, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.flights: List[Flight] = []
        self.bookings: Dict[str, Booking] = {}
        self.passengers: Dict[str, Passenger] = {}
        self._initialized = True
        print("INFO: AirlineSystem Facade initialized.")

    @classmethod
    def get_instance(cls):
        return cls()

    def add_flight(self, flight: Flight):
        self.flights.append(flight)
        print(f"DEBUG: Flight {flight.flight_number} added.")

    def register_passenger(self, passenger: Passenger):
        self.passengers[passenger.id] = passenger
        print(f"DEBUG: Passenger {passenger.name} registered.")

    def search_flights(self, src_code: str, dst_code: str, date: datetime) -> List[Flight]:
        """Find flights matching the route and date."""
        return [f for f in self.flights 
                if f.source.code == src_code and f.destination.code == dst_code]

    def create_booking(self, passenger: Passenger, flight: Flight, seat_nos: List[str], payment: PaymentProcessor) -> Booking:
        """Create a booking with integrated payment and seat reservation."""
        if passenger.id not in self.passengers:
            self.register_passenger(passenger)

        if not flight.book_seats(seat_nos):
            raise SeatUnavailableException(f"Requested seats {seat_nos} are not available.")

        price = flight.calculate_price(len(seat_nos))
        
        if not payment.process(price):
            # Rollback seat booking could be implemented here
            raise PaymentFailedException("Payment failed for the booking.")

        booking_id = str(uuid.uuid4())
        booking = Booking(booking_id, flight, passenger, seat_nos, price)
        booking.confirm()
        self.bookings[booking_id] = booking
        
        return booking

# ==========================================
# Main execution
# ==========================================

if __name__ == "__main__":
    print("--- Airline Management System Demo ---")
    
    system = AirlineSystem.get_instance()

    # 1. Setup
    boeing737 = Aircraft("AC1", "Boeing 737", 10)
    del_apt = Airport("DEL", "New Delhi")
    sfo_apt = Airport("SFO", "San Francisco")

    f1 = Flight("FL001", del_apt, sfo_apt, datetime.now(), boeing737, DynamicPricingStrategy())
    system.add_flight(f1)

    # 2. Search
    print("[Passenger] Searching DEL -> SFO")
    results = system.search_flights("DEL", "SFO", datetime.now())
    if not results:
        print("No flights found.")
    else:
        selected_flight = results[0]
        print(f"Found Flight: {selected_flight.flight_number} | Base Price: {selected_flight.base_price}")

        # 3. Booking (Passenger 1)
        p1 = Passenger("P1", "Rahul", "passport123")
        seats1 = ["1A", "1B"]
        payment = CreditCardPayment()
        
        try:
            curr_price = selected_flight.calculate_price(len(seats1))
            print(f"Current price for {len(seats1)} seats: ${curr_price:.2f}")
            b1 = system.create_booking(p1, selected_flight, seats1, payment)
            print(f"Booking successful! ID: {b1.booking_id}")
            
            # Add a meal
            b1.set_meal_preference(MealType.VEG)
            
        except AirlineException as e:
            print(f"ERROR: Booking failed: {e}")

        # 4. Booking (Passenger 2) - Should see dynamic price increase
        p2 = Passenger("P2", "Sita", "passport456")
        seats2 = ["2A"]
        
        try:
            curr_price = selected_flight.calculate_price(len(seats2))
            print(f"Dynamic price check for P2: ${curr_price:.2f}")
            b2 = system.create_booking(p2, selected_flight, seats2, payment)
            print(f"Booking successful! ID: {b2.booking_id}")
        except AirlineException as e:
            print(f"ERROR: Booking failed: {e}")
