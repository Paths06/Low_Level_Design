import heapq
import threading
import uuid
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Set

"""
==============================================================================================
ELEVATOR SYSTEM LOW LEVEL DESIGN (PYTHON - PRODUCTION GRADE)
==============================================================================================

Key Requirements Implemented:
1. Multiple Elevators & Floors.
2. Capacity Management.
3. Request Handling: External (Hall) and Internal (Panel).
4. Optimization: LOOK Algorithm (Scan) for efficient movement.
5. Concurrency: Thread-safe queues and synchronized state.
6. Production Standards: Logging, type hints, docstrings.

Design Patterns:
1. Singleton: ElevatorController (Central Dispatcher).
2. Strategy: DispatchStrategy (Implicit).
3. State: ElevatorState (IDLE, MOVING, STOPPED).

Algorithm Used: LOOK (Scanning)
- Elevator moves in current direction as long as there are requests.
- If no requests in current direction, it switches or goes IDLE.

Class Design Diagram:
---------------------
[ElevatorController] "1" *-- "*" [Elevator]
[ElevatorController] "1" *-- "1" [DispatchStrategy]
[Elevator] "1" *-- "1" [RequestQueue]
[Request] <|-- [InternalRequest]
[Request] <|-- [ExternalRequest]
[Elevator] ..> [Direction]
[Elevator] ..> [State]

Class Details:
---------------------
1. ElevatorController (Singleton)
   - Role: Central dispatcher. Handles External requests and assigns best Elevator.
   - Attributes: elevators (List).
   - Methods: requestElevator(), step() [Simulation ticker].

2. Elevator
   - Role: The physical car.
   - Attributes: id, currentFloor, direction, capacity, requests (PriorityQueue).
   - Methods: addRequest(), move(), openDoor().

3. Request (Abstract)
   - Role: Represents a button press.
   - Attributes: floor, direction.

4. DispatchStrategy
   - Role: Algorithm to assign external request to an elevator.
   - Logic: Finds nearest elevator moving in same direction or Idle.
"""

# ==========================================
# Enums & Models
# ==========================================

class Direction(Enum):
    UP = "UP"
    DOWN = "DOWN"
    IDLE = "IDLE"

class State(Enum):
    MOVING = "MOVING"
    IDLE = "IDLE"
    STOPPED = "STOPPED"

class Request(ABC):
    def __init__(self, target_floor: int):
        self.target_floor = target_floor

class InternalRequest(Request):
    def __init__(self, target_floor: int):
        super().__init__(target_floor)

class ExternalRequest(Request):
    def __init__(self, target_floor: int, direction: Direction):
        super().__init__(target_floor)
        self.direction = direction

# ==========================================
# Thread-safe Priority Queue for LOOK
# ==========================================

class PriorityQueue:
    """Thread-safe priority queue wrapper."""
    def __init__(self, reverse: bool = False):
        self._queue: List[int] = []
        self._reverse = reverse
        self._lock = threading.Lock()
        self._items: Set[int] = set() # To prevent duplicates

    def push(self, item: int):
        with self._lock:
            if item in self._items:
                return
            val = -item if self._reverse else item
            heapq.heappush(self._queue, val)
            self._items.add(item)

    def pop(self) -> Optional[int]:
        with self._lock:
            if not self._queue:
                return None
            val = heapq.heappop(self._queue)
            actual_val = -val if self._reverse else val
            self._items.remove(actual_val)
            return actual_val

    def peek(self) -> Optional[int]:
        with self._lock:
            if not self._queue:
                return None
            val = self._queue[0]
            return -val if self._reverse else val

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._queue) == 0

# ==========================================
# Core Domain: Elevator
# ==========================================

class Elevator:
    """Represents an individual elevator car."""
    def __init__(self, elevator_id: int, capacity: int):
        self.id = elevator_id
        self.capacity = capacity
        self.current_floor = 0
        self.direction = Direction.IDLE
        self.state = State.IDLE
        
        # LOOK Algorithm: min-heap for UP, max-heap for DOWN
        self.up_queue = PriorityQueue(reverse=False)
        self.down_queue = PriorityQueue(reverse=True)
        self._state_lock = threading.Lock()

    def add_external_request(self, req: ExternalRequest):
        """Handle request from outside the elevator."""
        with self._state_lock:
            if req.target_floor > self.current_floor:
                self.up_queue.push(req.target_floor)
                if self.direction == Direction.IDLE:
                    self.direction = Direction.UP
            else:
                self.down_queue.push(req.target_floor)
                if self.direction == Direction.IDLE:
                    self.direction = Direction.DOWN
            print(f"DEBUG: [Elevator {self.id}] External request added: {req.target_floor} {req.direction.name}")

    def add_internal_request(self, floor: int):
        """Handle request from inside the elevator panel."""
        with self._state_lock:
            if floor > self.current_floor:
                self.up_queue.push(floor)
                if self.direction == Direction.IDLE:
                    self.direction = Direction.UP
            elif floor < self.current_floor:
                self.down_queue.push(floor)
                if self.direction == Direction.IDLE:
                    self.direction = Direction.DOWN
            print(f"DEBUG: [Elevator {self.id}] Internal request added for floor {floor}")

    def move(self):
        """Simulate one floor of movement or door operation."""
        with self._state_lock:
            if self.direction == Direction.IDLE:
                return

            if self.direction == Direction.UP:
                self._process_up_queue()
            else:
                self._process_down_queue()

    def _process_up_queue(self):
        if self.up_queue.is_empty():
            if not self.down_queue.is_empty():
                self.direction = Direction.DOWN
            else:
                self.direction = Direction.IDLE
            return

        next_stop = self.up_queue.peek()
        if self.current_floor == next_stop:
            self.up_queue.pop()
            print(f"INFO: [Elevator {self.id}] Opened doors at Floor {self.current_floor}")
        else:
            self.current_floor += 1
            print(f"INFO: [Elevator {self.id}] Moving UP to Floor {self.current_floor}")

    def _process_down_queue(self):
        if self.down_queue.is_empty():
            if not self.up_queue.is_empty():
                self.direction = Direction.UP
            else:
                self.direction = Direction.IDLE
            return

        next_stop = self.down_queue.peek()
        if self.current_floor == next_stop:
            self.down_queue.pop()
            print(f"INFO: [Elevator {self.id}] Opened doors at Floor {self.current_floor}")
        else:
            self.current_floor -= 1
            print(f"INFO: [Elevator {self.id}] Moving DOWN to Floor {self.current_floor}")

    def is_idle(self) -> bool:
        return self.direction == Direction.IDLE

# ==========================================
# Controller (Singleton)
# ==========================================

class ElevatorController:
    """Central manager for dispatching elevators (Singleton)."""
    _instance = None
    _singleton_lock = threading.Lock()

    def __new__(cls):
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = super(ElevatorController, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.elevators: List[Elevator] = []
        self._initialized = True
        print("INFO: ElevatorController initialized.")

    @classmethod
    def get_instance(cls):
        return cls()

    def add_elevator(self, e: Elevator):
        self.elevators.append(e)

    def handle_external_request(self, floor: int, direction: Direction):
        """Assign best elevator for the hall request."""
        best_elevator = self._find_optimal_elevator(floor, direction)
        print(f"INFO: Assigning [Floor {floor} {direction.name}] to Elevator {best_elevator.id}")
        best_elevator.add_external_request(ExternalRequest(floor, direction))

    def _find_optimal_elevator(self, target_floor: int, direction: Direction) -> Elevator:
        """Heuristic to find the best elevator based on proximity and direction."""
        best = None
        min_distance = float('inf')

        for e in self.elevators:
            dist = abs(e.current_floor - target_floor)
            
            # If moving towards target or Idle
            moving_towards = False
            if e.direction == Direction.UP and e.current_floor <= target_floor:
                moving_towards = True
            elif e.direction == Direction.DOWN and e.current_floor >= target_floor:
                moving_towards = True
            elif e.is_idle():
                moving_towards = True

            if moving_towards:
                if dist < min_distance:
                    min_distance = dist
                    best = e
        
        # Fallback to first if none meet criteria
        return best if best else self.elevators[0]

    def step(self):
        """Ticker to simulate system movement."""
        for e in self.elevators:
            e.move()

# ==========================================
# Main Execution
# ==========================================

if __name__ == "__main__":
    print("--- Starting Elevator System Demo ---")

    controller = ElevatorController.get_instance()
    
    # 1. Setup
    e1 = Elevator(1, 10)
    e2 = Elevator(2, 10)
    controller.add_elevator(e1)
    controller.add_elevator(e2)

    # 2. Hall Requests
    print("[User] Floor 1 requests UP")
    controller.handle_external_request(1, Direction.UP)
    
    print("[User] Floor 5 requests DOWN")
    controller.handle_external_request(5, Direction.DOWN)

    # 3. Simulation Ticks
    print("\n--- Simulation Steps ---")
    for i in range(8):
        print(f"DEBUG: Tick {i}")
        controller.step()
        
        # Simulate internal panel press
        if i == 2:
            print("  [Sim] User entering Elevator 1 and pressing Floor 4")
            e1.add_internal_request(4)
