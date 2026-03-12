# fmt: off
# ==============================================================================
#  HOTEL MANAGEMENT SYSTEM — ASCII CLASS DIAGRAM
# ==============================================================================
#
#  ┌──────────────────────────────────────────────────────────────────────────┐
#  │                     HOTEL MANAGEMENT SYSTEM                              │
#  └──────────────────────────────────────────────────────────────────────────┘
#
#  ┌─────────────────────────┐           ┌──────────────────────────────┐
#  │      HotelManager       │  1    *   │             Room             │
#  │       (Facade)          │──────────>│            (ABC)             │
#  ├─────────────────────────┤           ├──────────────────────────────┤
#  │ + rooms: Dict           │           │ + id: str                    │
#  │ + reservations: Dict    │           │ + type: RoomType (enum)      │
#  ├─────────────────────────┤           │ + price: float               │
#  │ + add_room()            │           │ + status: RoomStatus (enum)  │
#  │ + find_available_room() │           │ - _lock: Lock                │
#  │ + create_reservation()  │           └──────────────┬───────────────┘
#  │ + check_in()            │                          │
#  │ + check_out()           │             ┌────────────┼────────────┐
#  └─────────────────────────┘             │            │            │
#                                          ▼            ▼            ▼
#  ┌──────────────────────┐     ┌──────────────┐ ┌──────────┐ ┌──────────┐
#  │     RoomFactory      │     │ StandardRoom │ │DeluxeRoom│ │SuiteRoom │
#  ├──────────────────────┤     ├──────────────┤ ├──────────┤ ├──────────┤
#  │ + create_room(       │     │ $100/night   │ │$200/night│ │$500/night│
#  │   type, id): Room    │     └──────────────┘ └──────────┘ └──────────┘
#  └──────────────────────┘
#                                 ┌──────────────────────────────────────┐
#  ┌───────────────────┐          │               Reservation            │
#  │       Guest       │    1     ├──────────────────────────────────────┤
#  ├───────────────────┤──────────│ + id: str                            │
#  │ + id: str         │          │ + guest: Guest                        │
#  │ + name: str       │          │ + room: Room                          │
#  │ + email: str      │          │ + check_in_date: datetime             │
#  └───────────────────┘          │ + nights: int                         │
#                                 │ + status: ReservationStatus (enum)   │
#  ┌───────────────────┐          │ + total_amount: float                 │
#  │  PaymentStrategy  │          ├──────────────────────────────────────┤
#  │    (ABC/Iface)    │          │ + process_payment(method): bool       │
#  ├───────────────────┤          └──────────────────────────────────────┘
#  │ + pay(amt): bool  │
#  └────────┬──────────┘    ┌──────────────┐   ┌──────────────────┐
#           │               │  RoomType    │   │   RoomStatus     │
#           ▼               ├──────────────┤   ├──────────────────┤
#  ┌────────────────────┐   │ STANDARD     │   │ AVAILABLE        │
#  │ CreditCardPayment  │   │ DELUXE       │   │ OCCUPIED         │
#  └────────────────────┘   │ SUITE        │   │ MAINTENANCE      │
#                           └──────────────┘   └──────────────────┘
#
#  RELATIONSHIPS:
#  HotelManager ──*──> Room           (manages all rooms)
#  HotelManager ──*──> Reservation    (tracks all reservations)
#  Reservation  ──1──> Guest          (belongs to one guest)
#  Reservation  ──1──> Room           (reserves one room)
#  RoomFactory creates StandardRoom | DeluxeRoom | SuiteRoom (Factory Pattern)
#  StandardRoom / DeluxeRoom / SuiteRoom ──▷── Room  (inheritance)
#  CreditCardPayment ──▷── PaymentStrategy             (implements)
#  Reservation.process_payment() uses PaymentStrategy  (Strategy Pattern)
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
HOTEL MANAGEMENT SYSTEM LOW LEVEL DESIGN (INTERVIEW OPTIMIZED)
==============================================================================================

Key Features:
1. Room Management: Types (Standard, Deluxe, Suite) and Status (Available, Occupied).
2. Reservation: Booking flow, Check-In, Check-Out.
3. Concurrency: Synchronized booking using threading locks.

Design Patterns:
1. Facade: HotelManager (Central Controller).
2. Factory: RoomFactory (Creating appropriate Room subclasses).
3. Strategy: PaymentStrategy.

Class Design Diagram:
---------------------
[HotelManager] "1" *-- "*" [Room]
[HotelManager] "1" *-- "*" [Guest]
[HotelManager] "1" *-- "*" [Reservation]
[Room] <|-- [StandardRoom]
[Room] <|-- [DeluxeRoom]
[Room] <|-- [SuiteRoom]
[Reservation] "1" *-- "1" [Guest]
[Reservation] "1" *-- "1" [Room]
[Room] ..> [RoomStatus]

Class Details:
---------------------
1. HotelManager (Facade)
   - Role: Central system controller.
   - Methods: addRoom(), findAvailableRoom(), createReservation(), checkIn(), checkOut().

2. Room (Abstract)
   - Role: Physical room entity.
   - Attributes: id, type, price, status (Lock for concurrency).

3. Guest
   - Attributes: id, name, email.

4. Reservation
   - Role: Transaction record.
   - Attributes: id, guest, room, nights, status, total_amount.
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
    def pay(self, amount: float) -> bool:
        print(f"INFO: Processing credit card payment of ${amount:.2f}")
        return True

# ==========================================
# Domain Models
# ==========================================

class Guest:
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
    """Factory to create room instances by type."""
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
        if method.pay(self.total_amount):
            print(f"INFO: Payment successful for reservation {self.id}")
            return True
        return False

# ==========================================
# Manager (Facade)
# ==========================================

class HotelManager:
    """Central controller for the Hotel Management System."""
    def __init__(self):
        self.rooms: Dict[str, Room] = {}
        self.reservations: Dict[str, Reservation] = {}
        print("INFO: HotelManager initialized.")

    def add_room(self, room: Room):
        self.rooms[room.id] = room

    def find_available_room(self, room_type: RoomType) -> Optional[Room]:
        for room in self.rooms.values():
            if room.type == room_type and room.status == RoomStatus.AVAILABLE:
                return room
        return None

    def create_reservation(self, guest: Guest, room: Room, date: datetime, nights: int) -> Reservation:
        """Create a new reservation with thread safety."""
        with room._lock:
            if room.status != RoomStatus.AVAILABLE:
                raise RoomUnavailableException(f"Room {room.id} is not available.")
            room.status = RoomStatus.OCCUPIED
            res = Reservation(guest, room, date, nights)
            self.reservations[res.id] = res
            print(f"INFO: Reservation {res.id} created for {guest.name} in Room {room.id}")
            return res

    def check_in(self, reservation_id: str):
        res = self.reservations.get(reservation_id)
        if not res:
            raise ReservationNotFoundException(f"Reservation {reservation_id} not found.")
        if res.status == ReservationStatus.CONFIRMED:
            res.status = ReservationStatus.CHECKED_IN
            res.room.status = RoomStatus.OCCUPIED
            print(f"INFO: {res.guest.name} checked into Room {res.room.id}")

    def check_out(self, reservation_id: str):
        res = self.reservations.get(reservation_id)
        if not res:
            raise ReservationNotFoundException(f"Reservation {reservation_id} not found.")
        res.status = ReservationStatus.CHECKED_OUT
        res.room.status = RoomStatus.AVAILABLE
        print(f"INFO: {res.guest.name} checked out from Room {res.room.id}")

# ==========================================
# Main Execution / Demo
# ==========================================

if __name__ == "__main__":
    print("--- Starting Hotel Management System Demo ---")

    hotel = HotelManager()
    hotel.add_room(RoomFactory.create_room(RoomType.STANDARD, "101"))
    hotel.add_room(RoomFactory.create_room(RoomType.DELUXE, "201"))
    hotel.add_room(RoomFactory.create_room(RoomType.SUITE, "301"))

    guest1 = Guest("G1", "John Doe", "john@example.com")
    guest2 = Guest("G2", "Jane Smith", "jane@example.com")

    print("[Action] John searches for DELUXE room.")
    room = hotel.find_available_room(RoomType.DELUXE)
    if room:
        try:
            res = hotel.create_reservation(guest1, room, datetime.now(), 3)
            if res.process_payment(CreditCardPayment()):
                hotel.check_in(res.id)
                hotel.check_out(res.id)
        except HotelException as e:
            print(f"ERROR: {e}")

    print("[Action] Jane searches for DELUXE room (none left).")
    if not hotel.find_available_room(RoomType.DELUXE):
        print("No Deluxe rooms available for Jane.")

    print("[Action] Jane books a SUITE.")
    suite = hotel.find_available_room(RoomType.SUITE)
    if suite:
        res2 = hotel.create_reservation(guest2, suite, datetime.now(), 1)
        hotel.check_in(res2.id)
        hotel.check_out(res2.id)
