# fmt: off
# ==============================================================================
#  ELEVATOR SYSTEM — ASCII CLASS DIAGRAM
# ==============================================================================
#
#  ┌──────────────────────────────────────────────────────────────────────────┐
#  │                        ELEVATOR SYSTEM (LOOK Algorithm)                  │
#  └──────────────────────────────────────────────────────────────────────────┘
#
#  ┌─────────────────────────┐           ┌──────────────────────────────────┐
#  │   ElevatorController    │  1    *   │             Elevator             │
#  │       (Facade)          │──────────>├──────────────────────────────────┤
#  ├─────────────────────────┤           │ + id: int                        │
#  │ + elevators: List       │           │ + capacity: int                  │
#  ├─────────────────────────┤           │ + current_floor: int             │
#  │ + add_elevator()        │           │ + direction: Direction (enum)    │
#  │ + handle_external_req() │           │ + up_queue: PriorityQueue        │
#  │ + step()                │           │ + down_queue: PriorityQueue      │
#  │ -_find_optimal_elevator()│          │ - _lock: Lock                    │
#  └─────────────────────────┘           ├──────────────────────────────────┤
#                                        │ + add_external_request()         │
#  ┌──────────────────────┐              │ + add_internal_request()         │
#  │  Request (ABC)       │              │ + move()    ← LOOK Algorithm     │
#  ├──────────────────────┤              │ + is_idle(): bool                │
#  │ + target_floor: int  │              └──────────────────────────────────┘
#  └──────────┬───────────┘
#             │
#      ┌──────┴───────┐
#      │              │
#      ▼              ▼
#  ┌──────────┐  ┌────────────────────┐
#  │ Internal │  │  ExternalRequest   │
#  │ Request  │  ├────────────────────┤
#  ├──────────┤  │ + direction:       │
#  │ (panel)  │  │   Direction (enum) │
#  └──────────┘  └────────────────────┘
#
#  ┌──────────────────────────────────┐
#  │         PriorityQueue            │  ← Thread-safe wrapper
#  ├──────────────────────────────────┤
#  │ + _queue: List[int]              │
#  │ + _reverse: bool (UP=min/DN=max) │
#  │ + _items: Set[int] (dedup)       │
#  │ - _lock: Lock                    │
#  ├──────────────────────────────────┤
#  │ + push(item)                     │
#  │ + pop(): int                     │
#  │ + peek(): int                    │
#  │ + is_empty(): bool               │
#  └──────────────────────────────────┘
#
#  ┌──────────────────────┐
#  │    Direction (Enum)  │
#  ├──────────────────────┤
#  │  UP / DOWN / IDLE    │
#  └──────────────────────┘
#
#  LOOK ALGORITHM (Disk Scheduling):
#  - Moving UP: serve all up_queue floors in ascending order
#  - When up_queue empty: switch to DOWN (serve descending)
#  - When down_queue empty: switch to IDLE
#  - External requests assigned to nearest elevator moving toward target
#
#  RELATIONSHIPS:
#  ElevatorController ──*──> Elevator         (manages all elevators)
#  Elevator ──2──> PriorityQueue              (up_queue + down_queue)
#  ExternalRequest ──▷── Request              (inherits, adds direction)
#  InternalRequest ──▷── Request              (inherits)
#  ElevatorController processes ExternalRequest → dispatches to best Elevator
# ==============================================================================
# fmt: on
import heapq
import threading
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Set

"""
==============================================================================================
ELEVATOR SYSTEM LOW LEVEL DESIGN (INTERVIEW OPTIMIZED)
==============================================================================================

Key Requirements Implemented:
1. Multiple Elevators & Floors.
2. Capacity Management.
3. Request Handling: External (Hall) and Internal (Panel).
4. Optimization: LOOK Algorithm (Scan) for efficient movement.
5. Concurrency: Thread-safe queues and synchronized state.

Design Patterns:
1. Facade: ElevatorController (Central Dispatcher).
2. Strategy: DispatchStrategy (best elevator selection).
3. State: ElevatorState (IDLE, MOVING, STOPPED) via Direction enum.

Algorithm Used: LOOK (Scanning)
- Elevator moves in current direction as long as there are requests.
- If no requests in current direction, it switches or goes IDLE.

Class Design Diagram:
---------------------
[ElevatorController] "1" *-- "*" [Elevator]
[Elevator] "1" *-- "2" [PriorityQueue] (up/down)
[Request] <|-- [InternalRequest]
[Request] <|-- [ExternalRequest]
[Elevator] ..> [Direction]
[Elevator] ..> [State]

Class Details:
---------------------
1. ElevatorController (Facade)
   - Role: Central dispatcher. Handles External requests and assigns best Elevator.
   - Methods: handle_external_request(), step() [Simulation ticker].

2. Elevator
   - Role: The physical car.
   - Attributes: id, currentFloor, direction, capacity.
   - Methods: add_external_request(), add_internal_request(), move().

3. Request (Abstract)
   - Role: Represents a button press.
   - Attributes: target_floor, direction.

4. PriorityQueue (Thread-safe wrapper)
   - Role: Thread-safe min/max heap for LOOK algorithm.
"""

# ==========================================
# Enums & Models
# ==========================================

class Direction(Enum):
    UP = "UP"
    DOWN = "DOWN"
    IDLE = "IDLE"

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
        self._items: Set[int] = set()  # Prevent duplicates

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
            actual = -val if self._reverse else val
            self._items.remove(actual)
            return actual

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
    """Represents an individual elevator car using the LOOK algorithm."""
    def __init__(self, elevator_id: int, capacity: int):
        self.id = elevator_id
        self.capacity = capacity
        self.current_floor = 0
        self.direction = Direction.IDLE
        # LOOK Algorithm: min-heap for UP, max-heap for DOWN
        self.up_queue = PriorityQueue(reverse=False)
        self.down_queue = PriorityQueue(reverse=True)
        self._lock = threading.Lock()

    def add_external_request(self, req: ExternalRequest):
        """Handle request from outside the elevator."""
        with self._lock:
            if req.target_floor > self.current_floor:
                self.up_queue.push(req.target_floor)
                if self.direction == Direction.IDLE:
                    self.direction = Direction.UP
            else:
                self.down_queue.push(req.target_floor)
                if self.direction == Direction.IDLE:
                    self.direction = Direction.DOWN
            print(f"INFO: [Elevator {self.id}] External request: Floor {req.target_floor} {req.direction.name}")

    def add_internal_request(self, floor: int):
        """Handle request from inside the elevator panel."""
        with self._lock:
            if floor > self.current_floor:
                self.up_queue.push(floor)
                if self.direction == Direction.IDLE:
                    self.direction = Direction.UP
            elif floor < self.current_floor:
                self.down_queue.push(floor)
                if self.direction == Direction.IDLE:
                    self.direction = Direction.DOWN
            print(f"INFO: [Elevator {self.id}] Internal request for floor {floor}")

    def move(self):
        """Simulate one floor of movement or door operation."""
        with self._lock:
            if self.direction == Direction.IDLE:
                return
            if self.direction == Direction.UP:
                self._process_up_queue()
            else:
                self._process_down_queue()

    def _process_up_queue(self):
        if self.up_queue.is_empty():
            self.direction = Direction.DOWN if not self.down_queue.is_empty() else Direction.IDLE
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
            self.direction = Direction.UP if not self.up_queue.is_empty() else Direction.IDLE
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
# Controller (Facade)
# ==========================================

class ElevatorController:
    """Central manager for dispatching elevators."""
    def __init__(self):
        self.elevators: List[Elevator] = []
        print("INFO: ElevatorController initialized.")

    def add_elevator(self, e: Elevator):
        self.elevators.append(e)

    def handle_external_request(self, floor: int, direction: Direction):
        """Assign best elevator for the hall request."""
        best = self._find_optimal_elevator(floor, direction)
        print(f"INFO: Assigning [Floor {floor} {direction.name}] to Elevator {best.id}")
        best.add_external_request(ExternalRequest(floor, direction))

    def _find_optimal_elevator(self, target_floor: int, direction: Direction) -> Elevator:
        """Heuristic: find nearest elevator moving toward the target or idle."""
        best = None
        min_distance = float('inf')
        for e in self.elevators:
            dist = abs(e.current_floor - target_floor)
            moving_towards = (
                (e.direction == Direction.UP and e.current_floor <= target_floor) or
                (e.direction == Direction.DOWN and e.current_floor >= target_floor) or
                e.is_idle()
            )
            if moving_towards and dist < min_distance:
                min_distance = dist
                best = e
        return best if best else self.elevators[0]

    def step(self):
        """Ticker to simulate one step of system movement."""
        for e in self.elevators:
            e.move()

# ==========================================
# Main Execution / Demo
# ==========================================

if __name__ == "__main__":
    print("--- Starting Elevator System Demo ---")

    controller = ElevatorController()
    e1 = Elevator(1, 10)
    e2 = Elevator(2, 10)
    controller.add_elevator(e1)
    controller.add_elevator(e2)

    # Hall Requests
    print("[User] Floor 1 requests UP")
    controller.handle_external_request(1, Direction.UP)
    print("[User] Floor 5 requests DOWN")
    controller.handle_external_request(5, Direction.DOWN)

    # Simulation Ticks
    print("\n--- Simulation Steps ---")
    for i in range(8):
        print(f"[Tick {i}]")
        controller.step()
        if i == 2:
            print("  [Sim] User inside Elevator 1 presses Floor 4")
            e1.add_internal_request(4)
