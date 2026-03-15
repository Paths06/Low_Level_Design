# fmt: off
# ==============================================================================
#  TASK MANAGEMENT SYSTEM — ASCII CLASS DIAGRAM
# ==============================================================================
#
#  ┌─────────────────────────────────────────────────────────────────────────┐
#  │                     TASK MANAGEMENT SYSTEM (Jira/Trello like)           │
#  └─────────────────────────────────────────────────────────────────────────┘
#
#  ┌─────────────────────────┐
#  │      TaskManager        │  ← Facade / Singleton Controller
#  ├─────────────────────────┤
#  │ + users: Dict           │
#  │ + tasks: Dict           │
#  ├─────────────────────────┤
#  │ + create_user()         │
#  │ + create_task()         │
#  │ + assign_task()         │
#  │ + change_task_status()  │
#  │ + search_tasks()        │
#  └─────────────────────────┘
#            │          │
#        ....│..........│....
#        .   ▼          ▼   .
#  ┌──────────────┐  ┌─────────────────────────┐
#  │     User     │  │          Task           │  ← Subject (Observer Pattern)
#  ├──────────────┤  ├─────────────────────────┤
#  │ + id: str    │  │ + id: str               │
#  │ + name: str  │  │ + title: str            │
#  │ + email: str │  │ + description: str      │
#  ├──────────────┤  │ + priority: Priority    │
#  │ + notify()   │◄─┤ + status: TaskStatus    │
#  └──────────────┘  │ + assignee: User        │
#           ▲        │ + creator: User         │
#           │        │ + followers: Set[User]  │
#           │        ├─────────────────────────┤
#           │        │ + change_status()       │
#           │        │ + add_follower()        │
#           │        │ - _notify_followers()   │
#           │        └─────────────────────────┘
#           │                     │
#           │                     ▼
#           │        ┌─────────────────────────┐
#           │        │      TaskHistory        │
#           │        ├─────────────────────────┤
#           │        │ + task_id: str          │
#           └────────┤ + changed_by: User      │
#                    │ + old_status: Status    │
#                    │ + new_status: Status    │
#                    │ + timestamp: datetime   │
#                    └─────────────────────────┘
#
#  RELATIONSHIPS:
#  TaskManager ──*──> User                    (manages directory of users)
#  TaskManager ──*──> Task                    (central repository of tasks)
#  Task ──2──> User                           (has 1 assignee, 1 creator)
#  Task ──*──> User                           (followers to notify on change)
#  Task ──*──> TaskHistory                    (audit log of changes)
#  Task ─▷ User.notify()                      (Observer: notifies followers on status change)
# ==============================================================================
# fmt: on

import uuid
import datetime
from enum import Enum
from typing import List, Dict, Optional, Set

"""
==============================================================================================
TASK MANAGEMENT SYSTEM LOW LEVEL DESIGN (INTERVIEW OPTIMIZED)
==============================================================================================

Key Features Implemented:
1. Task Lifecycle: Creation, Assignment, and State Tracking (TODO -> IN_PROGRESS -> DONE).
2. Audit Trail: Every status change creates an immutable `TaskHistory` record.
3. Notification System (Observer): If a task status changes, the creator, assignee, 
   and any explicitly added followers are notified via the Observer pattern.
4. Filtering/Search: Basic capability to search tasks by Assignee or Status.

Design Patterns:
1. Facade Pattern: `TaskManager` manages all complex sub-system interactions.
2. Observer Pattern: `Task` acts as the Publisher. `User` acts as the Subscriber. Every time
   a Task changes, it iterates its followers and calls their `notify` method.
3. State Representation: `TaskStatus` enum.
"""

# ==========================================
# Enums
# ==========================================

class TaskStatus(Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    IN_REVIEW = "IN_REVIEW"
    DONE = "DONE"


class TaskPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


# ==========================================
# Domain Entities: User & History
# ==========================================

class User:
    def __init__(self, name: str, email: str):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.email = email

    def notify(self, message: str):
        """Observer Pattern: Method called by the Task (Subject) when state changes."""
        print(f"[Notification -> {self.email}]: {message}")

    def __repr__(self):
        return self.name


class TaskHistory:
    """Immutable record representing a change in the task's state."""
    def __init__(self, changed_by: User, old_status: TaskStatus, new_status: TaskStatus):
        self.id = str(uuid.uuid4())[:8]
        self.changed_by = changed_by
        self.old_status = old_status
        self.new_status = new_status
        self.timestamp = datetime.datetime.now()

    def __repr__(self):
        return f"[{self.timestamp.strftime('%H:%M:%S')}] {self.changed_by.name} changed status: {self.old_status.name} -> {self.new_status.name}"


# ==========================================
# Core Domain: Task (The Subject)
# ==========================================

class Task:
    def __init__(self, title: str, description: str, creator: User, priority: TaskPriority):
        self.id = f"TASK-{str(uuid.uuid4())[:6].upper()}"
        self.title = title
        self.description = description
        self.priority = priority
        self.status = TaskStatus.TODO
        
        self.creator = creator
        self.assignee: Optional[User] = None
        
        self.history: List[TaskHistory] = []
        self.followers: Set[User] = set([creator])  # Creator inherently follows

    def assign_to(self, user: User, assigned_by: User):
        self.assignee = user
        self.add_follower(user)
        self._notify_followers(f"{assigned_by.name} assigned {self.id} to {user.name}")

    def change_status(self, new_status: TaskStatus, changed_by: User):
        if self.status == new_status:
            return

        # 1. Record History
        history_record = TaskHistory(changed_by, self.status, new_status)
        self.history.append(history_record)
        
        # 2. Update Status
        old_status_enum = self.status
        self.status = new_status
        
        # 3. Notify Observers
        curr_assignee = self.assignee.name if self.assignee else "Unassigned"
        msg = f"{self.id} moved to {new_status.name} by {changed_by.name} (Assignee: {curr_assignee})"
        self._notify_followers(msg)

    def add_follower(self, user: User):
        self.followers.add(user)

    def _notify_followers(self, message: str):
        for user in self.followers:
            user.notify(message)

    def __repr__(self):
        assignee_str = self.assignee.name if self.assignee else "Unassigned"
        return f"[{self.id}] {self.title} | {self.status.name} | {self.priority.name} | Assignee: {assignee_str}"


# ==========================================
# Facade: System Controller
# ==========================================

class TaskManager:
    """Central Controller for managing Users and Tasks."""
    
    _instance = None
    
    def __new__(cls):
        """Singleton implementation."""
        if cls._instance is None:
            cls._instance = super(TaskManager, cls).__new__(cls)
            cls._instance.users = {}
            cls._instance.tasks = {}
        return cls._instance

    def create_user(self, name: str, email: str) -> User:
        user = User(name, email)
        self.users[user.id] = user
        return user

    def create_task(self, title: str, description: str, creator: User, priority: TaskPriority = TaskPriority.MEDIUM) -> Task:
        task = Task(title, description, creator, priority)
        self.tasks[task.id] = task
        print(f"INFO: Task created -> {task.id}")
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

    # Useful queries for interviews
    def get_tasks_by_assignee(self, assignee: User) -> List[Task]:
        return [t for t in self.tasks.values() if t.assignee == assignee]

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        return [t for t in self.tasks.values() if t.status == status]


# ==========================================
# Main Execution / Demo
# ==========================================

if __name__ == "__main__":
    print("--- Starting Task Management System Demo ---")

    manager = TaskManager()

    # Create Users
    alice = manager.create_user("Alice (PM)", "alice@company.com")
    bob = manager.create_user("Bob (Dev)", "bob@company.com")
    charlie = manager.create_user("Charlie (QA)", "charlie@company.com")

    # Product Manager creates a task
    task1 = manager.create_task("Implement Login Page", "Use OAuth2", alice, TaskPriority.HIGH)
    
    # Charlie is interested and wants to follow the task
    task1.add_follower(charlie)

    print("\n--- Assigning Task ---")
    # Assign task to Bob
    task1.assign_to(bob, assigned_by=alice)

    print("\n--- Development Begins ---")
    # Bob starts working
    task1.change_status(TaskStatus.IN_PROGRESS, changed_by=bob)

    print("\n--- Moving to QA ---")
    # Bob finishes Dev
    task1.change_status(TaskStatus.IN_REVIEW, changed_by=bob)

    print("\n--- Task Details & History ---")
    print(task1)
    for record in task1.history:
        print("  *", record)

    print("\n--- Querying System ---")
    bobs_tasks = manager.get_tasks_by_assignee(bob)
    print(f"Tasks assigned to Bob: {len(bobs_tasks)}")
