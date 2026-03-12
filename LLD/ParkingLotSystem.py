# fmt: off
# ==============================================================================
#  PARKING LOT SYSTEM — ASCII CLASS DIAGRAM
# ==============================================================================
#
#  ┌──────────────────────────────────────────────────────────────────────────┐
#  │                       PARKING LOT SYSTEM                                 │
#  └──────────────────────────────────────────────────────────────────────────┘
#
#  ┌───────────────────────────────────────────────────────────────┐
#  │                   ParkingLot  (Facade)                        │
#  ├───────────────────────────────────────────────────────────────┤
#  │ + name: str                                                   │
#  │ + levels: List[Level]                                         │
#  │ + fee_strategy: FeeStrategy                                   │
#  │ + active_tickets: Dict[plate, Ticket]                         │
#  │ - _lock: Lock                                                 │
#  ├───────────────────────────────────────────────────────────────┤
#  │ + check_in(vehicle) -> Optional[Ticket]                       │
#  │ + check_out(plate) -> float (fee)                             │
#  │ + availability_report()                                       │
#  └───────────────────────────────┬───────────────────────────────┘
#                                  │ 1..*
#                                  ▼
#  ┌───────────────────────────────────────────────────────────────┐
#  │                         Level                                 │
#  ├───────────────────────────────────────────────────────────────┤
#  │ + level_id: int                                               │
#  │ + spots: List[ParkingSpot]                                    │
#  ├───────────────────────────────────────────────────────────────┤
#  │ + find_spot(vehicle) -> Optional[ParkingSpot]                 │
#  │   ← best-fit: MOTORCYCLE→MOTORCYCLE, CAR→COMPACT/REGULAR,     │
#  │               TRUCK→LARGE (smallest fitting spot first)        │
#  │ + available_count(spot_type): int                             │
#  └────────────────────────────┬──────────────────────────────────┘
#                               │ 1..*
#                               ▼
#  ┌──────────────────────────────────────────────────────────┐
#  │                   ParkingSpot                            │
#  ├──────────────────────────────────────────────────────────┤
#  │ + spot_id: str                                           │
#  │ + spot_type: SpotType (enum)                             │
#  │ + is_occupied: bool                                      │
#  │ + vehicle: Optional[Vehicle]                             │
#  ├──────────────────────────────────────────────────────────┤
#  │ + can_fit(vehicle): bool                                 │
#  │ + park(vehicle)                                          │
#  │ + unpark()                                               │
#  └──────────────────────────────────────────────────────────┘
#
#  ┌───────────────────────────┐         ┌────────────────────────┐
#  │       Vehicle (ABC)       │         │         Ticket         │
#  ├───────────────────────────┤         ├────────────────────────┤
#  │ + plate: str              │         │ + ticket_id: str       │
#  │ + vehicle_type: VehicleT. │         │ + vehicle: Vehicle     │
#  └───────────────┬───────────┘         │ + spot: ParkingSpot   │
#                  │                     │ + entry_time: datetime │
#      ┌───────────┼───────────┐         └────────────────────────┘
#      ▼           ▼           ▼
#  ┌──────────┐ ┌──────┐ ┌───────────┐  ┌──────────────────────────────────┐
#  │Motorcycle│ │ Car  │ │   Truck   │  │       FeeStrategy (ABC)          │
#  └──────────┘ └──────┘ └───────────┘  ├──────────────────────────────────┤
#                                        │ + calculate(entry, exit): float  │
#  ┌─────────────────────┐              └─────────────────┬────────────────┘
#  │   SpotType (Enum)   │                                │
#  ├─────────────────────┤               ┌────────────────┴─────────────┐
#  │  MOTORCYCLE         │               │                              │
#  │  COMPACT            │    ┌──────────────────────┐  ┌──────────────────────┐
#  │  REGULAR            │    │   HourlyFeeStrategy  │  │  FlatRateFeeStrategy │
#  │  LARGE              │    ├──────────────────────┤  ├──────────────────────┤
#  └─────────────────────┤    │ MOTORCYCLE: $1/hr    │  │ fixed rate regardless│
#  VehicleType (Enum):   │    │ CAR:        $2/hr    │  │ of duration          │
#  MOTORCYCLE/CAR/TRUCK  │    │ TRUCK:      $4/hr    │  └──────────────────────┘
#  └─────────────────────┘    └──────────────────────┘
#
#  BEST-FIT SPOT ASSIGNMENT:
#  Motorcycle → prefers MOTORCYCLE → falls back to COMPACT → REGULAR
#  Car        → prefers COMPACT   → falls back to REGULAR → LARGE
#  Truck      → requires LARGE only
#
#  RELATIONSHIPS:
#  ParkingLot ──*──> Level             (multi-floor management)
#  ParkingLot ──1──> FeeStrategy       (pluggable pricing)
#  ParkingLot ──*──> Ticket            (active check-ins by plate)
#  Level ──*──> ParkingSpot            (physical parking spots)
#  ParkingSpot ──1──> Vehicle(optional)(currently parked vehicle)
#  Ticket ──1──> Vehicle               (checked-in vehicle)
#  Ticket ──1──> ParkingSpot           (assigned spot)
#  Motorcycle/Car/Truck ──▷── Vehicle  (class hierarchy)
#  HourlyFeeStrategy/FlatRateFeeStrategy ──▷── FeeStrategy (implements)
# ==============================================================================
# fmt: on
import threading
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

"""
==============================================================================================
PARKING LOT SYSTEM LOW LEVEL DESIGN (INTERVIEW OPTIMIZED)
==============================================================================================

Key Features Implemented:
1. Vehicle Types: Motorcycle, Car, Truck (different sizes).
2. Spot Types: Small, Medium, Large — assigned by best-fit strategy.
3. Multi-Level: Multiple floors, each with configurable spots.
4. Ticketing: Issue ticket on entry, return on exit with fee.
5. Fee Calculation: Strategy pattern for Hourly and Flat-rate pricing.
6. Concurrency: Thread-safe spot assignment and release.

Design Patterns:
1. Facade: ParkingLotSystem (Central Controller).
2. Strategy: FeeStrategy (HourlyFee, FlatFee).
3. Factory: VehicleFactory (creates vehicles by type).
4. State: SpotStatus (FREE, OCCUPIED).

Class Design Diagram:
---------------------
[ParkingLotSystem] "1" *-- "*" [Level]
[ParkingLotSystem] "1" *-- "1" [FeeStrategy]
[ParkingLotSystem] "1" *-- "*" [Ticket]
[Level] "1" *-- "*" [ParkingSpot]
[ParkingSpot] ..> [SpotType]
[ParkingSpot] ..> [SpotStatus]
[Ticket] "1" *-- "1" [Vehicle]
[Ticket] "1" *-- "1" [ParkingSpot]
[Vehicle] <|-- [Motorcycle]
[Vehicle] <|-- [Car]
[Vehicle] <|-- [Truck]
[FeeStrategy] <|-- [HourlyFeeStrategy]
[FeeStrategy] <|-- [FlatFeeStrategy]

Class Details:
---------------------
1. ParkingLotSystem (Facade)
   - Role: Entry point. Manages levels, tickets, and fee calculation.
   - Methods: parkVehicle(), exitVehicle(), getAvailableCount().

2. Level
   - Role: A single floor of the parking lot.
   - Attributes: levelId, spots (List<ParkingSpot>).
   - Methods: findAvailableSpot(), freeSpot().

3. ParkingSpot
   - Role: An individual parking space.
   - Attributes: spotId, spotType, status, vehicle (Lock for concurrency).
   - Methods: assign(), release().

4. Ticket
   - Role: Issued on vehicle entry. Used for fee calculation on exit.
   - Attributes: ticketId, vehicle, spot, level, entryTime, exitTime, fee.

5. Vehicle (Abstract)
   - Role: A vehicle entering the lot.
   - Attributes: licensePlate, vehicleType, requiredSpotType.
   - Subclasses: Motorcycle (Small), Car (Medium), Truck (Large).

6. FeeStrategy (Interface)
   - Role: Pluggable fee calculation algorithm.
   - Impls: HourlyFeeStrategy, FlatFeeStrategy.
"""

# ==========================================
# Enums
# ==========================================

class VehicleType(Enum):
    MOTORCYCLE = "MOTORCYCLE"
    CAR = "CAR"
    TRUCK = "TRUCK"

class SpotType(Enum):
    SMALL = 1    # Fits: Motorcycle
    MEDIUM = 2   # Fits: Car, Motorcycle
    LARGE = 3    # Fits: Truck, Car, Motorcycle

class SpotStatus(Enum):
    FREE = "FREE"
    OCCUPIED = "OCCUPIED"

# ==========================================
# Fee Strategies
# ==========================================

class FeeStrategy(ABC):
    """Strategy for computing parking fees."""
    @abstractmethod
    def calculate(self, vehicle: 'Vehicle', entry_time: datetime, exit_time: datetime) -> float:
        pass

class HourlyFeeStrategy(FeeStrategy):
    """
    Charges per hour based on vehicle type.
    Rates: Motorcycle=$2/hr, Car=$4/hr, Truck=$8/hr.
    Minimum 1 hour billed; partial hours rounded up.
    """
    RATES = {
        VehicleType.MOTORCYCLE: 2.0,
        VehicleType.CAR:        4.0,
        VehicleType.TRUCK:      8.0,
    }

    def calculate(self, vehicle: 'Vehicle', entry_time: datetime, exit_time: datetime) -> float:
        delta = exit_time - entry_time
        hours = max(1, -(-delta.seconds // 3600))  # Ceiling division, min 1 hr
        rate = self.RATES.get(vehicle.vehicle_type, 4.0)
        return round(hours * rate, 2)

class FlatFeeStrategy(FeeStrategy):
    """
    Flat daily rate regardless of duration.
    Rates: Motorcycle=$10, Car=$20, Truck=$40.
    """
    RATES = {
        VehicleType.MOTORCYCLE: 10.0,
        VehicleType.CAR:        20.0,
        VehicleType.TRUCK:      40.0,
    }

    def calculate(self, vehicle: 'Vehicle', entry_time: datetime, exit_time: datetime) -> float:
        return self.RATES.get(vehicle.vehicle_type, 20.0)

# ==========================================
# Vehicles
# ==========================================

class Vehicle(ABC):
    """Abstract base class for all vehicle types."""
    def __init__(self, license_plate: str, vehicle_type: VehicleType, required_spot: SpotType):
        self.license_plate = license_plate
        self.vehicle_type = vehicle_type
        self.required_spot_type = required_spot  # Minimum spot size needed

    def __repr__(self):
        return f"{self.vehicle_type.value}({self.license_plate})"

class Motorcycle(Vehicle):
    """Fits in SMALL, MEDIUM, or LARGE spots."""
    def __init__(self, license_plate: str):
        super().__init__(license_plate, VehicleType.MOTORCYCLE, SpotType.SMALL)

class Car(Vehicle):
    """Fits in MEDIUM or LARGE spots."""
    def __init__(self, license_plate: str):
        super().__init__(license_plate, VehicleType.CAR, SpotType.MEDIUM)

class Truck(Vehicle):
    """Fits only in LARGE spots."""
    def __init__(self, license_plate: str):
        super().__init__(license_plate, VehicleType.TRUCK, SpotType.LARGE)

class VehicleFactory:
    """Factory to create vehicle instances by type."""
    @staticmethod
    def create(vehicle_type: VehicleType, license_plate: str) -> Vehicle:
        creators = {
            VehicleType.MOTORCYCLE: Motorcycle,
            VehicleType.CAR:        Car,
            VehicleType.TRUCK:      Truck,
        }
        cls = creators.get(vehicle_type)
        if not cls:
            raise ValueError(f"Unknown vehicle type: {vehicle_type}")
        return cls(license_plate)

# ==========================================
# Parking Spot
# ==========================================

class ParkingSpot:
    """
    Represents a single parking space.
    Best-fit: Only assign if spot type >= vehicle's required spot type.
    """
    def __init__(self, spot_id: str, spot_type: SpotType):
        self.id = spot_id
        self.spot_type = spot_type
        self.status = SpotStatus.FREE
        self.vehicle: Optional[Vehicle] = None
        self._lock = threading.Lock()

    def can_fit(self, vehicle: Vehicle) -> bool:
        """A spot can fit a vehicle if its type >= vehicle's required type."""
        return self.spot_type.value >= vehicle.required_spot_type.value

    def assign(self, vehicle: Vehicle) -> bool:
        """Thread-safely assign a vehicle to this spot."""
        with self._lock:
            if self.status == SpotStatus.FREE and self.can_fit(vehicle):
                self.status = SpotStatus.OCCUPIED
                self.vehicle = vehicle
                return True
            return False

    def release(self) -> Optional[Vehicle]:
        """Thread-safely release this spot."""
        with self._lock:
            freed = self.vehicle
            self.vehicle = None
            self.status = SpotStatus.FREE
            return freed

    def is_free(self) -> bool:
        return self.status == SpotStatus.FREE

    def __repr__(self):
        return f"Spot({self.id}, {self.spot_type.name}, {self.status.value})"

# ==========================================
# Ticket
# ==========================================

class Ticket:
    """Issued on vehicle entry. Holds all context needed to compute fee on exit."""
    def __init__(self, vehicle: Vehicle, spot: ParkingSpot, level_id: int):
        self.ticket_id = str(uuid.uuid4())[:8]
        self.vehicle = vehicle
        self.spot = spot
        self.level_id = level_id
        self.entry_time = datetime.now()
        self.exit_time: Optional[datetime] = None
        self.fee: float = 0.0

    def close(self, exit_time: datetime, fee: float):
        self.exit_time = exit_time
        self.fee = fee

    def __repr__(self):
        duration = (self.exit_time - self.entry_time) if self.exit_time else "ongoing"
        return (
            f"\n  Ticket ID  : {self.ticket_id}"
            f"\n  Vehicle    : {self.vehicle}"
            f"\n  Spot       : {self.spot.id} (Level {self.level_id})"
            f"\n  Entry      : {self.entry_time.strftime('%H:%M:%S')}"
            f"\n  Exit       : {self.exit_time.strftime('%H:%M:%S') if self.exit_time else 'N/A'}"
            f"\n  Fee        : ${self.fee:.2f}"
        )

# ==========================================
# Level
# ==========================================

class Level:
    """
    A single floor of the parking lot.
    Applies best-fit: find smallest spot that fits the vehicle.
    """
    def __init__(self, level_id: int, small: int, medium: int, large: int):
        self.level_id = level_id
        self.spots: List[ParkingSpot] = []
        self._lock = threading.Lock()

        # Initialize spots
        for i in range(small):
            self.spots.append(ParkingSpot(f"L{level_id}-S{i+1}", SpotType.SMALL))
        for i in range(medium):
            self.spots.append(ParkingSpot(f"L{level_id}-M{i+1}", SpotType.MEDIUM))
        for i in range(large):
            self.spots.append(ParkingSpot(f"L{level_id}-L{i+1}", SpotType.LARGE))

    def find_and_assign(self, vehicle: Vehicle) -> Optional[ParkingSpot]:
        """
        Best-fit: Sort eligible spots by spot_type value to find the
        smallest viable spot (avoids wasting large spots on motorbikes).
        Thread-safe via spot-level locks.
        """
        eligible = sorted(
            [s for s in self.spots if s.is_free() and s.can_fit(vehicle)],
            key=lambda s: s.spot_type.value
        )
        for spot in eligible:
            if spot.assign(vehicle):
                return spot
        return None

    def available_count(self) -> int:
        return sum(1 for s in self.spots if s.is_free())

    def display(self):
        print(f"  Level {self.level_id}: ", end="")
        for s in self.spots:
            icon = "[ ]" if s.is_free() else f"[{s.vehicle.vehicle_type.value[0]}]"
            print(f"{s.id}{icon}", end="  ")
        print()

# ==========================================
# Parking Lot System (Facade)
# ==========================================

class ParkingLotSystem:
    """
    Central facade for the parking lot.
    Manages levels, ticket issuance, and fee calculation.
    """
    def __init__(self, name: str, fee_strategy: FeeStrategy):
        self.name = name
        self.levels: List[Level] = []
        self.fee_strategy = fee_strategy
        self.active_tickets: Dict[str, Ticket] = {}  # license_plate -> Ticket
        self._lock = threading.Lock()
        print(f"INFO: ParkingLot '{name}' initialized.")

    def add_level(self, level: Level):
        self.levels.append(level)
        print(f"INFO: Added Level {level.level_id} "
              f"({sum(1 for s in level.spots if s.spot_type == SpotType.SMALL)} small, "
              f"{sum(1 for s in level.spots if s.spot_type == SpotType.MEDIUM)} medium, "
              f"{sum(1 for s in level.spots if s.spot_type == SpotType.LARGE)} large)")

    def park_vehicle(self, vehicle: Vehicle) -> Optional[Ticket]:
        """
        Entry point for a vehicle.
        Searches levels top-to-bottom, best-fit spot assignment.
        Returns a Ticket or None if lot is full.
        """
        with self._lock:
            if vehicle.license_plate in self.active_tickets:
                print(f"WARNING: {vehicle} is already parked!")
                return None

        for level in self.levels:
            spot = level.find_and_assign(vehicle)
            if spot:
                ticket = Ticket(vehicle, spot, level.level_id)
                with self._lock:
                    self.active_tickets[vehicle.license_plate] = ticket
                print(f"INFO: {vehicle} parked at {spot.id} | Ticket: {ticket.ticket_id}")
                return ticket

        print(f"WARNING: No available spot for {vehicle}. Lot is full!")
        return None

    def exit_vehicle(self, license_plate: str, exit_time: Optional[datetime] = None) -> Optional[Ticket]:
        """
        Exit flow: releases spot, calculates fee, closes ticket.
        exit_time is optional — defaults to now() (override for testing).
        """
        with self._lock:
            ticket = self.active_tickets.pop(license_plate, None)

        if not ticket:
            print(f"WARNING: No active parking record for plate '{license_plate}'")
            return None

        actual_exit = exit_time or datetime.now()
        fee = self.fee_strategy.calculate(ticket.vehicle, ticket.entry_time, actual_exit)
        ticket.close(actual_exit, fee)
        ticket.spot.release()

        print(f"INFO: {ticket.vehicle} exited. {ticket}")
        return ticket

    def get_available_spots(self) -> int:
        return sum(level.available_count() for level in self.levels)

    def set_fee_strategy(self, strategy: FeeStrategy):
        """Runtime-swappable fee strategy."""
        self.fee_strategy = strategy
        print(f"INFO: Fee strategy updated to {strategy.__class__.__name__}")

    def display(self):
        print(f"\n--- {self.name} Layout ---")
        for level in self.levels:
            level.display()
        print(f"Total Available: {self.get_available_spots()} spots\n")

# ==========================================
# Main Execution / Demo
# ==========================================

if __name__ == "__main__":
    print("--- Parking Lot System Demo ---\n")

    # Setup: 2-level lot, hourly pricing
    lot = ParkingLotSystem("City Centre Parking", HourlyFeeStrategy())
    lot.add_level(Level(level_id=1, small=2, medium=3, large=1))
    lot.add_level(Level(level_id=2, small=1, medium=2, large=2))
    lot.display()

    # Create vehicles
    moto1  = VehicleFactory.create(VehicleType.MOTORCYCLE, "MOTO-01")
    car1   = VehicleFactory.create(VehicleType.CAR,        "CAR-01")
    car2   = VehicleFactory.create(VehicleType.CAR,        "CAR-02")
    truck1 = VehicleFactory.create(VehicleType.TRUCK,      "TRUCK-01")
    moto2  = VehicleFactory.create(VehicleType.MOTORCYCLE, "MOTO-02")
    truck2 = VehicleFactory.create(VehicleType.TRUCK,      "TRUCK-02")

    # ----------------------------------------
    # Scenario 1: Normal park + exit (Hourly)
    # ----------------------------------------
    print("=== Scenario 1: Park & Exit (Hourly Fee) ===")
    lot.park_vehicle(moto1)
    lot.park_vehicle(car1)
    lot.park_vehicle(truck1)
    lot.display()

    # Simulate 2 hours later
    entry_plus_2h = datetime.now() + timedelta(hours=2)
    lot.exit_vehicle("CAR-01", exit_time=entry_plus_2h)
    lot.exit_vehicle("TRUCK-01", exit_time=entry_plus_2h)

    # ----------------------------------------
    # Scenario 2: Flat fee day parking
    # ----------------------------------------
    print("\n=== Scenario 2: Flat-Rate Fee ===")
    lot.set_fee_strategy(FlatFeeStrategy())
    lot.park_vehicle(car2)
    lot.exit_vehicle("CAR-02", exit_time=datetime.now() + timedelta(hours=5))

    # ----------------------------------------
    # Scenario 3: Best-fit spot assignment
    # ----------------------------------------
    print("\n=== Scenario 3: Best-Fit (Motorcycle doesn't take Car spot if Small is free) ===")
    lot.set_fee_strategy(HourlyFeeStrategy())
    lot.park_vehicle(moto2)  # Should prefer SMALL > MEDIUM > LARGE
    lot.display()

    # ----------------------------------------
    # Scenario 4: Lot full (try to park extra truck)
    # ----------------------------------------
    print("=== Scenario 4: Lot Full for Truck ===")
    # Fill all large spots
    lot.park_vehicle(truck2)
    extra = VehicleFactory.create(VehicleType.TRUCK, "TRUCK-99")
    lot.park_vehicle(extra)  # Should warn: no large spot

    # ----------------------------------------
    # Scenario 5: Duplicate entry prevention
    # ----------------------------------------
    print("\n=== Scenario 5: Duplicate Entry Prevention ===")
    lot.park_vehicle(moto1)  # Already parked
