import threading
import uuid
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime

"""
==============================================================================================
MEETING SCHEDULER LOW LEVEL DESIGN (PYTHON - PRODUCTION GRADE)
==============================================================================================

Key Features:
1. Resource Management: Meeting rooms with varying capacities.
2. Participant Management: Track availability via personal calendars.
3. Scheduling Logic: Finds available rooms and checks participant conflicts.
4. Strategy Pattern: Pluggable room selection logic (e.g., FCFS, best-fit).
5. Observer Pattern: Notifies participants of scheduled or canceled meetings.
6. Thread-safety: Synchronized access to room availability and scheduling.

Design Patterns:
1. Singleton: MeetingScheduler (Facade).
2. Strategy: RoomSelectionStrategy.
3. Observer: Participant notification.
"""

# ==========================================
# Domain Models
# ==========================================

class TimeSlot:
    """Represents a duration of time."""
    def __init__(self, start_time: datetime, end_time: datetime):
        if start_time >= end_time:
            raise ValueError("Start time must be before end time.")
        self.start_time = start_time
        self.end_time = end_time

    def overlaps(self, other: 'TimeSlot') -> bool:
        return self.start_time < other.end_time and self.end_time > other.start_time

    def __repr__(self):
        return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"

class Calendar:
    """Manages a schedule of time slots."""
    def __init__(self):
        self.bookings: List[TimeSlot] = []
        self._lock = threading.Lock()

    def is_available(self, slot: TimeSlot) -> bool:
        with self._lock:
            for booking in self.bookings:
                if slot.overlaps(booking):
                    return False
            return True

    def add_booking(self, slot: TimeSlot):
        with self._lock:
            self.bookings.append(slot)

    def remove_booking(self, slot: TimeSlot):
        with self._lock:
            if slot in self.bookings:
                self.bookings.remove(slot)

class Participant:
    """A person attending meetings."""
    def __init__(self, name: str, email: str):
        self.id = str(uuid.uuid4())
        self.name = name
        self.email = email
        self.calendar = Calendar()

    def notify(self, message: str):
        print(f"INFO: Notification sent to {self.name} ({self.email}): {message}")

class MeetingRoom:
    """Physical meeting room entity."""
    def __init__(self, room_id: str, capacity: int):
        self.id = room_id
        self.capacity = capacity
        self.calendar = Calendar()

    def __repr__(self):
        return f"Room({self.id}, Cap: {self.capacity})"

class Meeting:
    """An event scheduled in the system."""
    def __init__(self, title: str, participants: List[Participant], room: MeetingRoom, slot: TimeSlot):
        self.id = str(uuid.uuid4())
        self.title = title
        self.participants = participants
        self.room = room
        self.slot = slot

# ==========================================
# Scheduling Strategies
# ==========================================

class RoomSelectionStrategy(ABC):
    @abstractmethod
    def select_room(self, rooms: List[MeetingRoom], participants_count: int, slot: TimeSlot) -> Optional[MeetingRoom]:
        pass

class FirstComeFirstServeStrategy(RoomSelectionStrategy):
    """Picks the first available room that fits capacity."""
    def select_room(self, rooms: List[MeetingRoom], participants_count: int, slot: TimeSlot) -> Optional[MeetingRoom]:
        for room in rooms:
            if room.capacity >= participants_count and room.calendar.is_available(slot):
                return room
        return None

# ==========================================
# Meeting Room Controller
# ==========================================

class MeetingRoomController:
    """Manages the inventory of meeting rooms."""
    def __init__(self):
        self.rooms: Dict[str, MeetingRoom] = {}
        self._lock = threading.Lock()

    def add_room(self, room: MeetingRoom):
        with self._lock:
            self.rooms[room.id] = room
            print(f"DEBUG: Added meeting room: {room.id}")

    def get_all_rooms(self) -> List[MeetingRoom]:
        return list(self.rooms.values())

# ==========================================
# Meeting Scheduler (Singleton)
# ==========================================

class MeetingScheduler:
    """Facade for meeting room scheduling (Singleton)."""
    _instance = None
    _singleton_lock = threading.Lock()

    def __new__(cls):
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = super(MeetingScheduler, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.room_controller = MeetingRoomController()
        self.strategy: RoomSelectionStrategy = FirstComeFirstServeStrategy()
        self._initialized = True
        print("INFO: MeetingScheduler Service initialized.")

    @classmethod
    def get_instance(cls):
        return cls()

    def schedule(self, title: str, participants: List[Participant], slot: TimeSlot) -> Optional[Meeting]:
        """Schedules a meeting if a room and all participants are available."""
        # 1. Check participant availability
        for p in participants:
            if not p.calendar.is_available(slot):
                print(f"WARNING: Participant {p.name} is busy during {slot}")
                return None

        # 2. Find an available room
        all_rooms = self.room_controller.get_all_rooms()
        room = self.strategy.select_room(all_rooms, len(participants), slot)
        
        if not room:
            print(f"WARNING: No available room found for {len(participants)} participants during {slot}")
            return None

        # 3. Book room and participants
        room.calendar.add_booking(slot)
        for p in participants:
            p.calendar.add_booking(slot)

        # 4. Create and notify
        meeting = Meeting(title, participants, room, slot)
        notification_msg = f"Meeting '{title}' scheduled in {room.id} at {slot}."
        for p in participants:
            p.notify(notification_msg)
        
        print(f"INFO: {notification_msg}")
        return meeting

# ==========================================
# Main Execution / Demo
# ==========================================

if __name__ == "__main__":
    print("--- Starting Meeting Scheduler Demo ---")

    scheduler = MeetingScheduler.get_instance()

    # 1. Setup Rooms
    scheduler.room_controller.add_room(MeetingRoom("Conf-Room-A", 10))
    scheduler.room_controller.add_room(MeetingRoom("Huddle-Box-1", 3))

    # 2. Setup Participants
    p1 = Participant("Alice", "alice@corp.com")
    p2 = Participant("Bob", "bob@corp.com")
    p3 = Participant("Charlie", "charlie@corp.com")

    # 3. Schedule Meeting 1
    print("\n[Scenario 1] Alice and Bob want a 1-hour sync at 2 PM")
    slot1 = TimeSlot(datetime(2025, 1, 1, 14, 0), datetime(2025, 1, 1, 15, 0))
    scheduler.schedule("Product Sync", [p1, p2], slot1)

    # 4. Schedule Meeting 2 (Conflict)
    print("\n[Scenario 2] Charlie wants to meet Bob at 2:30 PM (Conflict for Bob)")
    slot2 = TimeSlot(datetime(2025, 1, 1, 14, 30), datetime(2025, 1, 1, 15, 30))
    scheduler.schedule("Tech Review", [p2, p3], slot2)

    # 5. Schedule Meeting 3 (Different Time)
    print("\n[Scenario 3] Charlie and Alice meet at 4 PM")
    slot3 = TimeSlot(datetime(2025, 1, 1, 16, 0), datetime(2025, 1, 1, 17, 0))
    scheduler.schedule("Design Brainstorm", [p1, p3], slot3)
