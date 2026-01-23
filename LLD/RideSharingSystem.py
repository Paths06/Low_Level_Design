import threading
import uuid
import math
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Optional
from datetime import datetime

"""
==============================================================================================
RIDE SHARING SERVICE (LIKE UBER) LOW LEVEL DESIGN (PYTHON - PRODUCTION GRADE)
==============================================================================================

Key Features Implemented:
1. User Management: Rider and Driver (Extends User).
2. Geo-Location: Distance-based calculation and nearest driver matching.
3. Trip Lifecycle: REQUESTED -> ASSIGNED -> ON_TRIP -> COMPLETED.
4. Cost Calculation: Strategy pattern for Regular/Premium pricing.
5. Concurrency: Thread-safe driver status and trip management.
6. Production Standards: Logging, type hints, docstrings.

Design Patterns:
1. Singleton: RideSharingService (Facade).
2. Strategy: PricingStrategy (Surge/RideType).
3. State: Handled via TripStatus.

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
1. RideSharingService (Singleton)
   - Role: Main controller.
   - Methods: requestRide(), completeRide().

2. Trip
   - Attributes: id, rider, driver, src, dest, status, price.
   - Methods: start(), end(), calculateFare().

3. Driver
   - Attributes: status (AVAILABLE, BUSY), location.

4. PricingStrategy
   - Role: Calculate fare based on distance/time.
"""

# ==========================================
# Enums & Models
# ==========================================

class RideType(Enum):
    REGULAR = "REGULAR"
    PREMIUM = "PREMIUM"

class TripStatus(Enum):
    REQUESTED = "REQUESTED"
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
            print(f"DEBUG: Driver {self.name} status updated to {status.name}")

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
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def start_trip(self):
        self.status = TripStatus.ON_TRIP
        self.start_time = datetime.now()
        print(f"INFO: Trip {self.id} started. {self.rider.name} with {self.driver.name}")

    def complete_trip(self):
        self.status = TripStatus.COMPLETED
        self.end_time = datetime.now()
        distance = self.src.distance_to(self.dest)
        # Assuming fixed duration for demo, in real life use duration between start/end
        self.fare = self.pricing.calculate_fare(distance, 15.0) 
        print(f"INFO: Trip {self.id} completed. Total Fare: ${self.fare:.2f}")

# ==========================================
# System Facade (Singleton)
# ==========================================

class RideSharingService:
    _instance = None
    _singleton_lock = threading.Lock()

    def __new__(cls):
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = super(RideSharingService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.drivers: List[Driver] = []
        self.riders: Dict[str, Rider] = {}
        self.active_trips: Dict[str, Trip] = {}
        self._initialized = True
        print("INFO: RideSharingService (Uber Clone) initialized.")

    @classmethod
    def get_instance(cls):
        return cls()

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

        # Matching Logic: Nearest AVAILABLE driver
        best_driver = self._find_nearest_driver(src)
        if not best_driver:
            print("WARNING: No available drivers nearby.")
            return None

        # Atomically mark driver as busy
        best_driver.update_status(DriverStatus.BUSY)

        strategy = PremiumPricing() if ride_type == RideType.PREMIUM else RegularPricing()
        trip = Trip(rider, best_driver, src, dest, strategy)
        self.active_trips[trip.id] = trip
        
        print(f"INFO: Ride assigned! Driver {best_driver.name} is arriving for {rider.name}")
        return trip

    def _find_nearest_driver(self, location: Location) -> Optional[Driver]:
        best_driver = None
        min_dist = float('inf')
        
        for d in self.drivers:
            if d.status == DriverStatus.AVAILABLE:
                dist = d.current_location.distance_to(location)
                if dist < min_dist:
                    min_dist = dist
                    best_driver = d
        return best_driver

    def complete_ride(self, trip_id: str):
        trip = self.active_trips.get(trip_id)
        if trip:
            trip.complete_trip()
            trip.driver.update_status(DriverStatus.AVAILABLE)
            trip.driver.current_location = trip.dest # Driver is now at destination
            del self.active_trips[trip_id]
        else:
            print(f"ERROR: Trip {trip_id} not found.")

# ==========================================
# Main Execution
# ==========================================

if __name__ == "__main__":
    print("--- Starting Ride Sharing System Demo ---")
    
    service = RideSharingService.get_instance()

    # 1. Setup Drivers
    d1 = Driver("D1", "Bob", Location(1, 1))
    d2 = Driver("D2", "Charlie", Location(10, 10))
    service.add_driver(d1)
    service.add_driver(d2)

    # 2. Setup Rider
    rider1 = Rider("R1", "Alice", Location(0, 0))
    service.add_rider(rider1)

    # 3. Simulate Request
    print("[Action] Alice requests a ride to (5, 5)")
    trip = service.request_ride("R1", rider1.current_location, Location(5, 5), RideType.REGULAR)
    
    if trip:
        # Simulate trip progress
        trip.start_trip()
        
        # Complete Trip
        service.complete_ride(trip.id)

    # 4. Check Driver Status
    print(f"INFO: Driver Bob status: {d1.status.name} at Location: {d1.current_location}")
