import threading
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

"""
==============================================================================================
HOTEL MANAGEMENT SYSTEM LOW LEVEL DESIGN (PYTHON - PRODUCTION GRADE)
==============================================================================================

Key Features:
1. Room Management: Types (Standard, Deluxe, Suite) and Status (Available, Occupied).
2. Reservation: Booking flow, Check-In, Check-Out.
3. Concurrency: Synchronized booking using threading locks.
4. Robustness: Logging, custom exceptions, and type hinting.

Design Patterns:
1. Singleton: HotelManager (Facade).
2. Factory: RoomFactory (Creating appropriate Room subclasses).
3. Strategy: PaymentStrategy.
"""

# ==========================================
# Exceptions
# ==========================================

class HotelException(Exception):
    """Base exception for Hotel Management System."""
    pass

class RoomUnavailableException(HotelException):
    """Raised when a requested room is already booked or occupied."""
    pass

class ReservationNotFoundException(HotelException):
    """Raised when a reservation cannot be found."""
    pass

# ==========================================
# Enums & Interfaces
# ==========================================

class RoomType(Enum):
    STANDARD = "STANDARD"
    DELUXE = "DELUXE"
    SUITE = "SUITE"

class RoomStatus(Enum):
    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"
    MAINTENANCE = "MAINTENANCE"

class ReservationStatus(Enum):
    CONFIRMED = "CONFIRMED"
    CHECKED_IN = "CHECKED_IN"
    CHECKED_OUT = "CHECKED_OUT"
    CANCELLED = "CANCELLED"

class PaymentStrategy(ABC):
    """Interface for payment methods."""
    @abstractmethod
    def pay(self, amount: float) -> bool:
        pass

class CreditCardPayment(PaymentStrategy):
    """Credit card payment implementation."""
    def pay(self, amount: float) -> bool:
        print(f"INFO: Processing credit card payment of ${amount:.2f}")
        return True

# ==========================================
# Domain Models
# ==========================================

class Guest:
    """Represents a hotel guest."""
    def __init__(self, guest_id: str, name: str, email: str = ""):
        self.id = guest_id
        self.name = name
        self.email = email

class Room(ABC):
    """Base abstract class for all room types."""
    def __init__(self, room_id: str, room_type: RoomType, price: float):
        self.id = room_id
        self.type = room_type
        self.price = price
        self.status = RoomStatus.AVAILABLE
        self._lock = threading.Lock()

    def __repr__(self):
        return f"Room({self.id}, {self.type.value}, {self.status.value})"

class StandardRoom(Room):
    def __init__(self, room_id: str):
        super().__init__(room_id, RoomType.STANDARD, 100.0)

class DeluxeRoom(Room):
    def __init__(self, room_id: str):
        super().__init__(room_id, RoomType.DELUXE, 200.0)

class SuiteRoom(Room):
    def __init__(self, room_id: str):
        super().__init__(room_id, RoomType.SUITE, 500.0)

class RoomFactory:
    """Factory to create room instances."""
    @staticmethod
    def create_room(room_type: RoomType, room_id: str) -> Room:
        if room_type == RoomType.STANDARD:
            return StandardRoom(room_id)
        elif room_type == RoomType.DELUXE:
            return DeluxeRoom(room_id)
        elif room_type == RoomType.SUITE:
            return SuiteRoom(room_id)
        raise ValueError(f"Unknown room type: {room_type}")

class Reservation:
    """Represents a successful room booking."""
    def __init__(self, guest: Guest, room: Room, check_in_date: datetime, nights: int):
        self.id = str(uuid.uuid4())
        self.guest = guest
        self.room = room
        self.check_in_date = check_in_date
        self.nights = nights
        self.status = ReservationStatus.CONFIRMED
        self.total_amount = room.price * nights

    def process_payment(self, method: PaymentStrategy) -> bool:
        """Process the payment for this reservation."""
        if method.pay(self.total_amount):
            print(f"INFO: Payment successful for reservation {self.id}")
            return True
        return False

# ==========================================
# Manager (Singleton)
# ==========================================

class HotelManager:
    """Central controller for the Hotel Management System (Singleton)."""
    _instance = None
    _singleton_lock = threading.Lock()

    def __new__(cls):
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = super(HotelManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.rooms: Dict[str, Room] = {}
        self.reservations: Dict[str, Reservation] = {}
        self._initialized = True
        print("INFO: HotelManager initialized.")

    @classmethod
    def get_instance(cls):
        return cls()

    def add_room(self, room: Room):
        """Add a room to the system."""
        self.rooms[room.id] = room
        print(f"DEBUG: Added room {room.id} to system.")

    def find_available_room(self, room_type: RoomType) -> Optional[Room]:
        """Search for an available room of the specified type."""
        for room in self.rooms.values():
            if room.type == room_type and room.status == RoomStatus.AVAILABLE:
                return room
        return None

    def create_reservation(self, guest: Guest, room: Room, date: datetime, nights: int) -> Reservation:
        """Create a new reservation with thread safety."""
        with room._lock:
            if room.status != RoomStatus.AVAILABLE:
                print(f"WARNING: Attempted to book unavailable room {room.id}")
                raise RoomUnavailableException(f"Room {room.id} is not available.")
            
            # Reservation occupies the room for this simple simulation
            room.status = RoomStatus.OCCUPIED
            res = Reservation(guest, room, date, nights)
            self.reservations[res.id] = res
            print(f"INFO: Reservation {res.id} created for {guest.name} in Room {room.id}")
            return res

    def check_in(self, reservation_id: str):
        """Perform guest check-in."""
        res = self.reservations.get(reservation_id)
        if not res:
            raise ReservationNotFoundException(f"Reservation {reservation_id} not found.")
        
        if res.status == ReservationStatus.CONFIRMED:
            res.status = ReservationStatus.CHECKED_IN
            res.room.status = RoomStatus.OCCUPIED
            print(f"INFO: Guest {res.guest.name} checked into Room {res.room.id}")

    def check_out(self, reservation_id: str):
        """Perform guest check-out and free the room."""
        res = self.reservations.get(reservation_id)
        if not res:
            raise ReservationNotFoundException(f"Reservation {reservation_id} not found.")
        
        res.status = ReservationStatus.CHECKED_OUT
        res.room.status = RoomStatus.AVAILABLE
        print(f"INFO: Guest {res.guest.name} checked out from Room {res.room.id}")

# ==========================================
# Main execution
# ==========================================

if __name__ == "__main__":
    print("--- Starting Hotel Management System Demo ---")
    
    hotel = HotelManager.get_instance()

    # 1. Setup
    hotel.add_room(RoomFactory.create_room(RoomType.STANDARD, "101"))
    hotel.add_room(RoomFactory.create_room(RoomType.DELUXE, "201"))
    hotel.add_room(RoomFactory.create_room(RoomType.SUITE, "301"))

    # 2. Guests
    guest1 = Guest("G1", "John Doe", "john@example.com")
    guest2 = Guest("G2", "Jane Smith", "jane@example.com")

    # 3. Operations
    print("[Action] John searches for DELUXE room.")
    available_room = hotel.find_available_room(RoomType.DELUXE)
    
    if available_room:
        try:
            # Create Reservation
            reservation = hotel.create_reservation(guest1, available_room, datetime.now(), 3)
            
            # Payment
            if reservation.process_payment(CreditCardPayment()):
                # Check-In
                hotel.check_in(reservation.id)
                
                # Check-Out (normally later)
                # hotel.check_out(reservation.id)
                
        except HotelException as e:
            print(f"ERROR: Operation failed: {e}")

    # 4. Jane tries to find a DELUXE room (none left)
    print("[Action] Jane searches for DELUXE room.")
    jane_room = hotel.find_available_room(RoomType.DELUXE)
    if not jane_room:
        print("No Deluxe rooms available for Jane.")

    # 5. Jane books SUITE
    suite = hotel.find_available_room(RoomType.SUITE)
    if suite:
        res2 = hotel.create_reservation(guest2, suite, datetime.now(), 1)
        hotel.check_in(res2.id)
        hotel.check_out(res2.id)
