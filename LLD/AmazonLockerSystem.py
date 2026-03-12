# fmt: off
# ==============================================================================
#  AMAZON LOCKER SYSTEM — ASCII CLASS DIAGRAM
# ==============================================================================
#
#  ┌──────────────────────────────────────────────────────────────────────────┐
#  │                       AMAZON LOCKER SYSTEM                               │
#  └──────────────────────────────────────────────────────────────────────────┘
#
#  ┌────────────────────────────────────────────────────────┐
#  │                   LockerSystem  (Facade)               │
#  ├────────────────────────────────────────────────────────┤
#  │ + locations: List[LockerLocation]                      │
#  │ + reservations: Dict[tracking_id, LockerReservation]   │
#  │ - _lock: Lock                                          │
#  ├────────────────────────────────────────────────────────┤
#  │ + add_location(location)                               │
#  │ + deposit_package(tracking_id, size, location_id)      │
#  │   → finds best-fit locker, generates access code       │
#  │ + pickup_package(code) → validates code + expiry       │
#  └──────────────────────────┬─────────────────────────────┘
#                             │ 1..*
#                             ▼
#  ┌─────────────────────────────────────────────┐
#  │              LockerLocation                 │
#  ├─────────────────────────────────────────────┤
#  │ + location_id: str                          │
#  │ + address: str                              │
#  │ + lockers: List[Locker]                     │
#  ├─────────────────────────────────────────────┤
#  │ + find_available_locker(min_size): Locker   │
#  │   ← best-fit: smallest locker >= min_size  │
#  └──────────────────────┬──────────────────────┘
#                         │ 1..*
#                         ▼
#  ┌───────────────────────────────────────────┐
#  │                 Locker                    │
#  ├───────────────────────────────────────────┤
#  │ + locker_id: str                          │
#  │ + size: Size (enum)                       │
#  │ + status: LockerStatus (enum)             │
#  ├───────────────────────────────────────────┤
#  │ + is_available(): bool                    │
#  │ + assign()                                │
#  │ + release()                               │
#  └───────────────────────────────────────────┘
#
#  ┌───────────────────────────────────────────┐
#  │            LockerReservation              │
#  ├───────────────────────────────────────────┤
#  │ + tracking_id: str                        │
#  │ + locker: Locker                          │
#  │ + access_code: str  (6-digit random)      │
#  │ + location_id: str                        │
#  │ + expiry_date: datetime                   │
#  ├───────────────────────────────────────────┤
#  │ + is_expired(): bool                      │
#  └───────────────────────────────────────────┘
#
#  ┌───────────────────────────────────────────┐
#  │              Package                      │
#  ├───────────────────────────────────────────┤
#  │ + tracking_id: str                        │
#  │ + size: Size (enum)                       │
#  │ + recipient_email: str                    │
#  └───────────────────────────────────────────┘
#
#  ┌─────────────────┐   ┌────────────────────────────┐
#  │   Size (Enum)   │   │    LockerStatus (Enum)     │
#  ├─────────────────┤   ├────────────────────────────┤
#  │  SMALL  = 1     │   │  AVAILABLE                 │
#  │  MEDIUM = 2     │   │  OCCUPIED                  │
#  │  LARGE  = 3     │   └────────────────────────────┘
#  └─────────────────┘
#
#  BEST-FIT MATCHING:
#  find_available_locker(min_size): returns smallest AVAILABLE locker
#  where locker.size.value >= min_size.value (avoids wasting large lockers)
#
#  RELATIONSHIPS:
#  LockerSystem ──*──> LockerLocation       (manages physical stations)
#  LockerSystem ──*──> LockerReservation    (active reservations by tracking_id)
#  LockerLocation ──*──> Locker             (physical locker units)
#  LockerReservation ──1──> Locker          (refers to reserved locker)
#  Package is transient input to deposit_package()
#  Thread-safe: LockerSystem._lock guards the deposit/pickup flow
# ==============================================================================
# fmt: on
import threading
import random
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

"""
==============================================================================================
AMAZON LOCKER SYSTEM LOW LEVEL DESIGN (INTERVIEW OPTIMIZED)
==============================================================================================

Key Features:
1. Package Deposit: Delivery drivers can deposit a package into an available locker.
2. Customer Pickup: Customers retrieve packages using a one-time access code.
3. Locker Sizes: Lockers come in SMALL, MEDIUM, LARGE to fit packages of different sizes.
4. Code Expiry: Access codes expire after a configurable number of days.
5. Thread-Safety: All critical operations are protected with a single system-level lock.

Design Patterns:
1. Facade: LockerSystem is the single entry point for all operations.
2. State Pattern: Each Locker transitions between AVAILABLE and OCCUPIED states.
3. Best-Fit Matching: find_available_locker() picks the smallest locker that fits.

Class Design Diagram:
---------------------
[LockerSystem] "1" *-- "*" [LockerLocation]
[LockerLocation] "1" *-- "*" [Locker]
[Locker] "1" *-- "1" [Size] (Enum)
[Locker] "1" *-- "1" [LockerStatus] (Enum)
[LockerSystem] "1" *-- "*" [LockerReservation]
[LockerReservation] "1" --> "1" [Locker]
[Package] "1" *-- "1" [Size] (Enum)

Class Details:
---------------------
1. LockerSystem (Facade)
   - Role: Central coordinator. Manages locations and reservations.
   - Methods: add_location(), deposit_package(), pickup_package().

2. LockerLocation
   - Role: Represents one physical locker station (e.g., "Walmart on 5th Ave").
   - Attributes: location_id, address, lockers (List[Locker]).
   - Methods: find_available_locker(min_size) -> Optional[Locker].

3. Locker
   - Role: A single locker unit. Holds its size and current status.
   - Attributes: locker_id, size (Size), status (LockerStatus).

4. Package
   - Role: A package to be stored, with a tracking ID and size.
   - Attributes: tracking_id, size (Size), customer_email.

5. LockerReservation
   - Role: Binds a package to a locker with a one-time access code and expiry.
   - Attributes: locker, package, access_code, expiry_time, is_active.

6. Size (Enum)
   - Shared enum for both lockers and packages: SMALL=1, MEDIUM=2, LARGE=3.
   - Numeric values allow direct size comparison (locker.size >= package.size).

7. LockerStatus (Enum)
   - Values: AVAILABLE, OCCUPIED.
"""

# ==========================================
# Enums
# ==========================================

class Size(Enum):
    """Shared size enum for both lockers and packages. Ordered numerically for comparison."""
    SMALL = 1
    MEDIUM = 2
    LARGE = 3


class LockerStatus(Enum):
    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"

# ==========================================
# Core Domain Models
# ==========================================

class Package:
    """A package to be deposited at a locker station."""
    def __init__(self, tracking_id: str, size: Size, customer_email: str):
        self.tracking_id = tracking_id
        self.size = size
        self.customer_email = customer_email

    def __repr__(self):
        return f"Package({self.tracking_id}, {self.size.name})"


class Locker:
    """A single locker unit. Status transitions: AVAILABLE <-> OCCUPIED."""
    def __init__(self, locker_id: str, size: Size):
        self.locker_id = locker_id
        self.size = size
        self.status = LockerStatus.AVAILABLE

    def is_available(self) -> bool:
        return self.status == LockerStatus.AVAILABLE

    def __repr__(self):
        return f"Locker({self.locker_id}, {self.size.name}, {self.status.value})"


class LockerReservation:
    """Binds a package to a locker with a time-limited, one-time access code."""
    def __init__(self, locker: Locker, package: Package, expiry_days: int = 3):
        self.locker = locker
        self.package = package
        self.access_code = str(random.randint(100000, 999999))  # 6-digit code
        self.expiry_time = datetime.now() + timedelta(days=expiry_days)
        self.is_active = True

    def is_expired(self) -> bool:
        return datetime.now() > self.expiry_time

    def __repr__(self):
        return (f"Reservation(Locker: {self.locker.locker_id}, "
                f"Code: {self.access_code}, Expires: {self.expiry_time.date()})")


class LockerLocation:
    """A physical locker station containing lockers of various sizes."""
    def __init__(self, location_id: str, address: str):
        self.location_id = location_id
        self.address = address
        self.lockers: List[Locker] = []

    def add_locker(self, locker: Locker):
        self.lockers.append(locker)

    def find_available_locker(self, required_size: Size) -> Optional[Locker]:
        """Best-fit: find the smallest available locker that can hold the package."""
        candidates = [l for l in self.lockers
                      if l.is_available() and l.size.value >= required_size.value]
        if not candidates:
            return None
        return min(candidates, key=lambda l: l.size.value)

    def __repr__(self):
        return f"LockerLocation({self.location_id}, {self.address})"

# ==========================================
# Locker System (Central Facade)
# ==========================================

class LockerSystem:
    """
    Central facade for the Amazon Locker system.
    Manages all locker stations and reservations in a thread-safe manner.
    """
    def __init__(self):
        self.locations: Dict[str, LockerLocation] = {}
        # access_code -> LockerReservation
        self.reservations: Dict[str, LockerReservation] = {}
        self._lock = threading.Lock()

    def add_location(self, location: LockerLocation):
        """Registers a new locker station."""
        self.locations[location.location_id] = location
        print(f"INFO: Added {location}")

    def deposit_package(self, location_id: str, package: Package) -> Optional[str]:
        """
        Driver deposits a package at a station.
        Assigns the best-fit locker and returns the customer's access code.
        """
        location = self.locations.get(location_id)
        if not location:
            print(f"ERROR: Location '{location_id}' not found.")
            return None

        with self._lock:
            locker = location.find_available_locker(package.size)
            if not locker:
                print(f"ERROR: No available locker for {package} at {location_id}.")
                return None

            # Atomically mark the locker and create the reservation
            locker.status = LockerStatus.OCCUPIED
            reservation = LockerReservation(locker=locker, package=package)
            self.reservations[reservation.access_code] = reservation

        print(f"INFO: {package} -> {locker} | Code: {reservation.access_code}, Expires: {reservation.expiry_time.date()}")
        return reservation.access_code

    def pickup_package(self, access_code: str) -> Optional[Package]:
        """
        Customer picks up a package using their access code.
        Validates code, checks expiry, releases the locker.
        """
        with self._lock:
            reservation = self.reservations.get(access_code)

            if not reservation:
                print(f"ERROR: Invalid code '{access_code}'.")
                return None

            if reservation.is_expired():
                # Expired — free the locker and remove the reservation
                reservation.locker.status = LockerStatus.AVAILABLE
                del self.reservations[access_code]
                print(f"ERROR: Code '{access_code}' has expired.")
                return None

            # Success: release the locker
            reservation.locker.status = LockerStatus.AVAILABLE
            package = reservation.package
            del self.reservations[access_code]

        print(f"INFO: {package} picked up from {reservation.locker.locker_id}.")
        return package

# ==========================================
# Main Execution / Demo
# ==========================================

if __name__ == "__main__":
    print("--- Starting Amazon Locker System Demo ---\n")

    system = LockerSystem()

    # Setup: one station with 2 small, 1 medium, 1 large locker
    station = LockerLocation("LOC-001", "Walmart, MG Road, Bengaluru")
    for locker in [Locker("L-S1", Size.SMALL), Locker("L-S2", Size.SMALL),
                   Locker("L-M1", Size.MEDIUM), Locker("L-L1", Size.LARGE)]:
        station.add_locker(locker)
    system.add_location(station)

    # -----------------------------------------------
    # Scenario 1: Driver deposits packages
    # -----------------------------------------------
    print("\n[Scenario 1] Driver deposits two packages")
    pkg1 = Package("PKG-001", Size.SMALL, "alice@example.com")
    pkg2 = Package("PKG-002", Size.MEDIUM, "bob@example.com")
    code1 = system.deposit_package("LOC-001", pkg1)
    code2 = system.deposit_package("LOC-001", pkg2)

    # -----------------------------------------------
    # Scenario 2: Customer picks up with correct code
    # -----------------------------------------------
    print("\n[Scenario 2] Alice picks up with correct code")
    system.pickup_package(code1)

    # -----------------------------------------------
    # Scenario 3: Invalid code
    # -----------------------------------------------
    print("\n[Scenario 3] Invalid access code")
    system.pickup_package("000000")

    # -----------------------------------------------
    # Scenario 4: Code reuse after pickup (code deleted)
    # -----------------------------------------------
    print("\n[Scenario 4] Reuse of already-consumed code")
    system.pickup_package(code1)  # code1 was deleted after pickup

    # -----------------------------------------------
    # Scenario 5: No locker available for size
    # -----------------------------------------------
    print("\n[Scenario 5] No locker available for size LARGE")
    system.deposit_package("LOC-001", Package("PKG-003", Size.SMALL, "carol@example.com"))
    system.deposit_package("LOC-001", Package("PKG-004", Size.LARGE, "dave@example.com"))
    system.deposit_package("LOC-001", Package("PKG-005", Size.LARGE, "eve@example.com"))  # should fail

    # -----------------------------------------------
    # Scenario 6: Bob picks up his package
    # -----------------------------------------------
    print("\n[Scenario 6] Bob picks up his package")
    system.pickup_package(code2)
