# fmt: off
# ==============================================================================
#  RIDE SHARING SYSTEM — ASCII CLASS DIAGRAM
# ==============================================================================
#
#  ┌──────────────────────────────────────────────────────────────────────────┐
#  │                    RIDE SHARING SYSTEM (Uber-like)                       │
#  └──────────────────────────────────────────────────────────────────────────┘
#
#  ┌────────────────────────────┐
#  │    RideSharingService      │  ← Facade
#  ├────────────────────────────┤
#  │ + riders: Dict             │
#  │ + drivers: Dict            │
#  │ + trips: Dict              │
#  │ + pricing: PricingStrategy │
#  ├────────────────────────────┤
#  │ + register_rider()         │
#  │ + register_driver()        │
#  │ + request_ride()           │
#  │ + complete_trip()          │
#  │ -_find_nearest_driver()    │
#  └────────────────────────────┘
#            │          │
#        ....│..........│....
#        .   ▼          ▼   .
#  ┌──────────────┐  ┌──────────────────────────┐
#  │    Rider     │  │         Driver           │
#  ├──────────────┤  ├──────────────────────────┤
#  │ + id: str    │  │ + id: str                │
#  │ + name: str  │  │ + name: str              │
#  │ + location   │  │ + location: (x, y)       │
#  └──────────────┘  │ + status: DriverStatus   │
#                    │   (enum)                 │
#                    ├──────────────────────────┤
#                    │ + update_location()      │
#                    └──────────────────────────┘
#
#  ┌────────────────────────────────────────────────────┐
#  │                       Trip                         │
#  ├────────────────────────────────────────────────────┤
#  │ + id: str                                          │
#  │ + rider: Rider                                     │
#  │ + driver: Driver                                   │
#  │ + pickup_loc, dropoff_loc: (x, y)                  │
#  │ + status: TripStatus (enum)                        │
#  │ + fare: float                                      │
#  │ + start_time, end_time: datetime                   │
#  ├────────────────────────────────────────────────────┤
#  │ + start()                                          │
#  │ + complete(pricing_strategy)                       │
#  └────────────────────────────────────────────────────┘
#
#  ┌─────────────────────────────────┐
#  │       PricingStrategy           │  ← Strategy Pattern
#  │         (ABC/Interface)         │
#  ├─────────────────────────────────┤
#  │ + calculate(trip): float        │
#  └─────────────────┬───────────────┘
#                    │
#             ┌──────┴──────┐
#             │             │
#             ▼             ▼
#  ┌───────────────────┐ ┌────────────────────────┐
#  │  RegularPricing   │ │   SurgePricing         │
#  ├───────────────────┤ ├────────────────────────┤
#  │ BASE=2.0 +        │ │ SURGE_MULTIPLIER=2.5   │
#  │ 1.0 per unit dist │ │ applied on top of base │
#  └───────────────────┘ └────────────────────────┘
#
#  ┌─────────────────────────┐  ┌─────────────────────┐
#  │   DriverStatus (Enum)   │  │  TripStatus (Enum)  │
#  ├─────────────────────────┤  ├─────────────────────┤
#  │  AVAILABLE              │  │  REQUESTED          │
#  │  BUSY                   │  │  IN_PROGRESS        │
#  │  OFFLINE                │  │  COMPLETED          │
#  └─────────────────────────┘  │  CANCELLED          │
#                               └─────────────────────┘
#
#  RELATIONSHIPS:
#  RideSharingService ──*──> Rider          (registered riders)
#  RideSharingService ──*──> Driver         (registered drivers)
#  RideSharingService ──*──> Trip           (active and past trips)
#  RideSharingService ──1──> PricingStrategy(swappable pricing)
#  Trip ──1──> Rider                        (who requested)
#  Trip ──1──> Driver                       (who serves)
#  RegularPricing / SurgePricing ──▷── PricingStrategy (implements)
#  Driver.status transitions: AVAILABLE → BUSY (on ride start) → AVAILABLE (on complete)
# ==============================================================================
# fmt: on
import threading
import uuid
import math
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Optional
from datetime import datetime

"""
==============================================================================================
RIDE SHARING SERVICE (LIKE UBER) LOW LEVEL DESIGN (INTERVIEW OPTIMIZED)
==============================================================================================

Key Features Implemented:
1. User Management: Rider and Driver (Extends User).
2. Geo-Location: Distance-based calculation and nearest driver matching.
3. Trip Lifecycle: REQUESTED -> ASSIGNED -> ON_TRIP -> COMPLETED.
4. Cost Calculation: Strategy pattern for Regular/Premium pricing.
5. Concurrency: Thread-safe driver status updates.

Design Patterns:
1. Facade: RideSharingService (Central Controller).
2. Strategy: PricingStrategy (Regular/Premium).
3. State: Handled via TripStatus and DriverStatus.

Class Design Diagram:
---------------------
[RideSharingService] "1" *-- "*" [Driver]
[RideSharingService] "1" *-- "*" [Rider]
[RideSharingService] "1" *-- "*" [Trip]
[Trip] "1" *-- "1" [Driver]
[Trip] "1" *-- "1" [Rider]
[Trip] "1" *-- "1" [PricingStrategy]
[Driver] <|-- [User]
[Rider] <|-- [User]
[PricingStrategy] <|-- [RegularPricing]
[PricingStrategy] <|-- [PremiumPricing]

Class Details:
---------------------
1. RideSharingService (Facade)
   - Role: Main controller.
   - Methods: requestRide(), completeRide().

2. Trip
   - Attributes: id, rider, driver, src, dest, status, fare.
   - Methods: startTrip(), completeTrip().

3. Driver
   - Attributes: status (AVAILABLE, BUSY), location.
   - Methods: updateStatus().

4. PricingStrategy
   - Role: Calculate fare based on distance and time.
   - Impls: RegularPricing, PremiumPricing.
"""

# ==========================================
# Enums & Models
# ==========================================

class RideType(Enum):
    REGULAR = "REGULAR"
    PREMIUM = "PREMIUM"

class TripStatus(Enum):
    ASSIGNED = "ASSIGNED"
    ON_TRIP = "ON_TRIP"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class DriverStatus(Enum):
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"

class Location:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def distance_to(self, other: 'Location') -> float:
        """Calculate Euclidean distance between two points."""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    def __repr__(self):
        return f"({self.x}, {self.y})"

# ==========================================
# Pricing Strategies
# ==========================================

class PricingStrategy(ABC):
    @abstractmethod
    def calculate_fare(self, distance: float, time_mins: float) -> float:
        pass

class RegularPricing(PricingStrategy):
    def calculate_fare(self, distance: float, time_mins: float) -> float:
        return (distance * 10.0) + (time_mins * 2.0)

class PremiumPricing(PricingStrategy):
    def calculate_fare(self, distance: float, time_mins: float) -> float:
        return (distance * 20.0) + (time_mins * 4.0)

# ==========================================
# Domain Models
# ==========================================

class User:
    def __init__(self, user_id: str, name: str):
        self.id = user_id
        self.name = name

class Rider(User):
    def __init__(self, user_id: str, name: str, location: Location):
        super().__init__(user_id, name)
        self.current_location = location

class Driver(User):
    def __init__(self, user_id: str, name: str, location: Location):
        super().__init__(user_id, name)
        self.current_location = location
        self.status = DriverStatus.AVAILABLE
        self.rating = 5.0
        self._lock = threading.Lock()

    def update_status(self, status: DriverStatus):
        with self._lock:
            self.status = status
            print(f"INFO: Driver {self.name} status -> {status.name}")

class Trip:
    """Represents a single ride journey."""
    def __init__(self, rider: Rider, driver: Driver, src: Location, dest: Location, pricing: PricingStrategy):
        self.id = str(uuid.uuid4())
        self.rider = rider
        self.driver = driver
        self.src = src
        self.dest = dest
        self.pricing = pricing
        self.status = TripStatus.ASSIGNED
        self.fare = 0.0

    def start_trip(self):
        self.status = TripStatus.ON_TRIP
        print(f"INFO: Trip {self.id[:8]}... started. {self.rider.name} with {self.driver.name}")

    def complete_trip(self):
        self.status = TripStatus.COMPLETED
        distance = self.src.distance_to(self.dest)
        self.fare = self.pricing.calculate_fare(distance, 15.0)  # 15min assumed for demo
        print(f"INFO: Trip completed. Fare: ${self.fare:.2f}")

# ==========================================
# System Facade
# ==========================================

class RideSharingService:
    def __init__(self):
        self.drivers: List[Driver] = []
        self.riders: Dict[str, Rider] = {}
        self.active_trips: Dict[str, Trip] = {}
        print("INFO: RideSharingService initialized.")

    def add_driver(self, driver: Driver):
        self.drivers.append(driver)

    def add_rider(self, rider: Rider):
        self.riders[rider.id] = rider

    def request_ride(self, rider_id: str, src: Location, dest: Location, ride_type: RideType) -> Optional[Trip]:
        """Finds the nearest driver and creates a ride request."""
        rider = self.riders.get(rider_id)
        if not rider:
            print(f"ERROR: Rider {rider_id} not registered.")
            return None

        best_driver = self._find_nearest_driver(src)
        if not best_driver:
            print("WARNING: No available drivers nearby.")
            return None

        best_driver.update_status(DriverStatus.BUSY)
        pricing = PremiumPricing() if ride_type == RideType.PREMIUM else RegularPricing()
        trip = Trip(rider, best_driver, src, dest, pricing)
        self.active_trips[trip.id] = trip
        print(f"INFO: Ride assigned! Driver {best_driver.name} -> {rider.name}")
        return trip

    def _find_nearest_driver(self, location: Location) -> Optional[Driver]:
        available = [d for d in self.drivers if d.status == DriverStatus.AVAILABLE]
        if not available:
            return None
        return min(available, key=lambda d: d.current_location.distance_to(location))

    def complete_ride(self, trip_id: str):
        trip = self.active_trips.get(trip_id)
        if trip:
            trip.complete_trip()
            trip.driver.update_status(DriverStatus.AVAILABLE)
            trip.driver.current_location = trip.dest
            del self.active_trips[trip_id]
        else:
            print(f"ERROR: Trip {trip_id} not found.")

# ==========================================
# Main Execution / Demo
# ==========================================

if __name__ == "__main__":
    print("--- Starting Ride Sharing System Demo ---")

    service = RideSharingService()

    d1 = Driver("D1", "Bob", Location(1, 1))
    d2 = Driver("D2", "Charlie", Location(10, 10))
    service.add_driver(d1)
    service.add_driver(d2)

    rider1 = Rider("R1", "Alice", Location(0, 0))
    service.add_rider(rider1)

    print("[Action] Alice requests a REGULAR ride to (5, 5)")
    trip = service.request_ride("R1", rider1.current_location, Location(5, 5), RideType.REGULAR)

    if trip:
        trip.start_trip()
        service.complete_ride(trip.id)

    print(f"INFO: Bob status: {d1.status.name} at Location: {d1.current_location}")
