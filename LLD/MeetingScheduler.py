# fmt: off
# ==============================================================================
#  MEETING SCHEDULER — ASCII CLASS DIAGRAM
# ==============================================================================
#
#  ┌──────────────────────────────────────────────────────────────────────────┐
#  │                        MEETING SCHEDULER                                 │
#  └──────────────────────────────────────────────────────────────────────────┘
#
#  ┌────────────────────────────────────┐
#  │         MeetingScheduler           │  ← Facade
#  ├────────────────────────────────────┤
#  │ + room_controller: MeetingRoomCtrl │
#  │ + strategy: RoomSelectionStrategy  │
#  ├────────────────────────────────────┤
#  │ + schedule(title, participants,    │
#  │            slot): Optional[Meeting]│
#  └──────────┬─────────────────────────┘
#             │ 1 uses                  │ 1 uses
#             ▼                        ▼
#  ┌──────────────────────────┐  ┌──────────────────────────────┐
#  │  MeetingRoomController   │  │    RoomSelectionStrategy     │
#  ├──────────────────────────┤  │        (ABC/Interface)       │
#  │ + rooms: Dict            │  ├──────────────────────────────┤
#  ├──────────────────────────┤  │ + select_room(rooms, count,  │
#  │ + add_room()             │  │    slot): Optional[Room]     │
#  │ + get_all_rooms()        │  └──────────────┬───────────────┘
#  └──────────┬───────────────┘                 │
#             │ 1..*                            ▼
#             ▼                  ┌──────────────────────────────┐
#  ┌──────────────────────────┐  │   FirstComeFirstServeStrategy│
#  │       MeetingRoom        │  ├──────────────────────────────┤
#  ├──────────────────────────┤  │ + select_room(): picks first │
#  │ + id: str                │  │   free room that fits count  │
#  │ + capacity: int          │  └──────────────────────────────┘
#  │ + calendar: Calendar     │
#  └──────────────────────────┘
#
#  ┌─────────────────────────────────────────┐
#  │              Meeting                    │
#  ├─────────────────────────────────────────┤
#  │ + id: str                               │
#  │ + title: str                            │
#  │ + participants: List[Participant]       │
#  │ + room: MeetingRoom                     │
#  │ + slot: TimeSlot                        │
#  └─────────────────────────────────────────┘
#
#  ┌──────────────────────┐    ┌─────────────────────────────────────┐
#  │     Participant      │    │              Calendar               │
#  ├──────────────────────┤    ├─────────────────────────────────────┤
#  │ + id: str            │    │ + bookings: List[TimeSlot]          │
#  │ + name: str          │    │ - _lock: Lock                       │
#  │ + email: str         │    ├─────────────────────────────────────┤
#  │ + calendar: Calendar │    │ + is_available(slot): bool          │
#  ├──────────────────────┤    │ + add_booking(slot)                 │
#  │ + notify(message)    │    │ + remove_booking(slot)              │
#  └──────────────────────┘    └─────────────────────────────────────┘
#
#  ┌──────────────────────────────┐
#  │          TimeSlot            │
#  ├──────────────────────────────┤
#  │ + start_time: datetime       │
#  │ + end_time: datetime         │
#  ├──────────────────────────────┤
#  │ + overlaps(other): bool      │
#  └──────────────────────────────┘
#
#  RELATIONSHIPS:
#  MeetingScheduler ──1──> MeetingRoomController   (aggregates rooms)
#  MeetingScheduler ──1──> RoomSelectionStrategy   (pluggable strategy)
#  MeetingRoomController ──*──> MeetingRoom        (manages rooms)
#  Meeting  ──1──> MeetingRoom                     (booked in a room)
#  Meeting  ──*──> Participant                     (attendees)
#  Participant ──1──> Calendar                     (personal schedule)
#  MeetingRoom ──1──> Calendar                     (room schedule)
#  TimeSlot.overlaps() detects scheduling conflicts
#  Observer: Participant.notify() called for every scheduled meeting
# ==============================================================================
# fmt: on
import threading
import uuid
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime

"""
==============================================================================================
MEETING SCHEDULER LOW LEVEL DESIGN (INTERVIEW OPTIMIZED)
==============================================================================================

Key Features:
1. Resource Management: Meeting rooms with varying capacities.
2. Participant Management: Track availability via personal calendars.
3. Scheduling Logic: Finds available rooms and checks participant conflicts.
4. Strategy Pattern: Pluggable room selection logic (e.g., FCFS, best-fit).
5. Observer Pattern: Notifies participants of scheduled meetings.
6. Thread-safety: Synchronized access to room availability and scheduling.

Design Patterns:
1. Facade: MeetingScheduler (Central Controller).
2. Strategy: RoomSelectionStrategy.
3. Observer: Participant notification.

Class Design Diagram:
---------------------
[MeetingScheduler] "1" o-- "1" [MeetingRoomController]
[MeetingScheduler] "1" o-- "1" [RoomSelectionStrategy]
[MeetingRoomController] "1" *-- "*" [MeetingRoom]
[MeetingRoom] "1" *-- "1" [Calendar]
[Meeting] "1" *-- "*" [Participant]
[Meeting] "1" *-- "1" [TimeSlot]
[Participant] ..|> [Observer] : Implements
[FirstComeFirstServeStrategy] ..|> [RoomSelectionStrategy]

Class Details:
---------------------
1. MeetingScheduler (Facade)
   - Role: Facade for scheduling logic.
   - Attributes: roomController, selectionStrategy.
   - Methods: schedule().

2. MeetingRoomController
   - Role: Manages list of rooms and filters them.
   - Methods: addMeetingRoom(), getAllRooms().

3. MeetingRoom
   - Role: Physical room entity.
   - Attributes: roomId, capacity, calendar.

4. Meeting
   - Role: Event entity.
   - Attributes: id, title, participants, timeSlot, room.

5. Calendar
   - Role: Manages availability for a room or user.
   - Attributes: bookings (List<TimeSlot>).
   - Methods: isAvailable(), addBooking().

6. Participant
   - Role: User attending meeting. Receives notifications.
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
            return not any(slot.overlaps(b) for b in self.bookings)

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
        print(f"INFO: Notification -> {self.name} ({self.email}): {message}")

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
    def select_room(self, rooms: List[MeetingRoom], count: int, slot: TimeSlot) -> Optional[MeetingRoom]:
        pass

class FirstComeFirstServeStrategy(RoomSelectionStrategy):
    """Picks the first available room that fits the participant count."""
    def select_room(self, rooms: List[MeetingRoom], count: int, slot: TimeSlot) -> Optional[MeetingRoom]:
        for room in rooms:
            if room.capacity >= count and room.calendar.is_available(slot):
                return room
        return None

# ==========================================
# Meeting Room Controller
# ==========================================

class MeetingRoomController:
    """Manages the inventory of meeting rooms."""
    def __init__(self):
        self.rooms: Dict[str, MeetingRoom] = {}

    def add_room(self, room: MeetingRoom):
        self.rooms[room.id] = room
        print(f"INFO: Added meeting room: {room.id}")

    def get_all_rooms(self) -> List[MeetingRoom]:
        return list(self.rooms.values())

# ==========================================
# Meeting Scheduler (Facade)
# ==========================================

class MeetingScheduler:
    """Facade for meeting room scheduling."""
    def __init__(self):
        self.room_controller = MeetingRoomController()
        self.strategy: RoomSelectionStrategy = FirstComeFirstServeStrategy()
        print("INFO: MeetingScheduler initialized.")

    def schedule(self, title: str, participants: List[Participant], slot: TimeSlot) -> Optional[Meeting]:
        """Schedules a meeting if a room and all participants are available."""
        # 1. Check participant availability
        for p in participants:
            if not p.calendar.is_available(slot):
                print(f"WARNING: {p.name} is busy during {slot}")
                return None

        # 2. Find an available room
        room = self.strategy.select_room(self.room_controller.get_all_rooms(), len(participants), slot)
        if not room:
            print(f"WARNING: No available room for {len(participants)} participants at {slot}")
            return None

        # 3. Book room and participants
        room.calendar.add_booking(slot)
        for p in participants:
            p.calendar.add_booking(slot)

        # 4. Create and notify
        meeting = Meeting(title, participants, room, slot)
        msg = f"Meeting '{title}' scheduled in {room.id} at {slot}."
        for p in participants:
            p.notify(msg)
        print(f"INFO: {msg}")
        return meeting

# ==========================================
# Main Execution / Demo
# ==========================================

if __name__ == "__main__":
    print("--- Starting Meeting Scheduler Demo ---")

    scheduler = MeetingScheduler()
    scheduler.room_controller.add_room(MeetingRoom("Conf-Room-A", 10))
    scheduler.room_controller.add_room(MeetingRoom("Huddle-Box-1", 3))

    p1 = Participant("Alice", "alice@corp.com")
    p2 = Participant("Bob", "bob@corp.com")
    p3 = Participant("Charlie", "charlie@corp.com")

    print("\n[Scenario 1] Alice and Bob want a 1-hour sync at 2 PM")
    slot1 = TimeSlot(datetime(2025, 1, 1, 14, 0), datetime(2025, 1, 1, 15, 0))
    scheduler.schedule("Product Sync", [p1, p2], slot1)

    print("\n[Scenario 2] Charlie wants to meet Bob at 2:30 PM (Conflict for Bob)")
    slot2 = TimeSlot(datetime(2025, 1, 1, 14, 30), datetime(2025, 1, 1, 15, 30))
    scheduler.schedule("Tech Review", [p2, p3], slot2)

    print("\n[Scenario 3] Charlie and Alice meet at 4 PM")
    slot3 = TimeSlot(datetime(2025, 1, 1, 16, 0), datetime(2025, 1, 1, 17, 0))
    scheduler.schedule("Design Brainstorm", [p1, p3], slot3)
