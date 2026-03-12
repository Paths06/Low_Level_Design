# fmt: off
# ==============================================================================
#  SPLITWISE SYSTEM — ASCII CLASS DIAGRAM
# ==============================================================================
#
#  ┌──────────────────────────────────────────────────────────────────────────┐
#  │                         SPLITWISE SYSTEM                                 │
#  └──────────────────────────────────────────────────────────────────────────┘
#
#  ┌─────────────────────────────────────────────┐
#  │              SplitwiseService               │  ← Facade
#  ├─────────────────────────────────────────────┤
#  │ + users: Dict[str, User]                    │
#  │ + expenses: List[Expense]                   │
#  │ + balances: Dict[str, Dict[str, Decimal]]   │
#  │ - _lock: Lock                               │
#  ├─────────────────────────────────────────────┤
#  │ + add_user()                                │
#  │ + add_expense(payer, total, split, members) │
#  │ + settle_balance(paid_by, paid_to, amount)  │
#  │ + show_balances()                           │
#  └─────────────────────────────────────────────┘
#                     │
#                     │ creates
#                     ▼
#  ┌─────────────────────────────────────────────┐
#  │                 Expense                     │
#  ├─────────────────────────────────────────────┤
#  │ + id: str                                   │
#  │ + description: str                          │
#  │ + amount: Decimal                           │
#  │ + paid_by: User                             │
#  │ + split: SplitStrategy                      │
#  │ + members: List[User]                       │
#  ├─────────────────────────────────────────────┤
#  │ + compute_shares() -> Dict[User, Decimal]   │
#  └─────────────────────────────────────────────┘
#                     │ 1
#                     ▼
#  ┌─────────────────────────────────────────────┐
#  │           SplitStrategy (ABC)               │  ← Strategy Pattern
#  ├─────────────────────────────────────────────┤
#  │ + compute(amount, members): Dict[User,Dec]  │
#  └──────────────┬──────────────────────────────┘
#                 │
#       ┌─────────┼──────────┐
#       ▼         ▼          ▼
#  ┌─────────┐ ┌────────┐ ┌──────────────────────┐
#  │ Equal   │ │ Exact  │ │    PercentSplit       │
#  │  Split  │ │ Split  │ ├──────────────────────┤
#  ├─────────┤ ├────────┤ │ percentages: Dict    │
#  │ amount/n│ │fixed   │ │ (must sum to 100%)   │
#  │ each    │ │amounts │ └──────────────────────┘
#  └─────────┘ └────────┘
#
#  ┌──────────────────────────────┐
#  │            User              │
#  ├──────────────────────────────┤
#  │ + id: str                    │
#  │ + name: str                  │
#  │ + email: str                 │
#  └──────────────────────────────┘
#
#  Balance Map Structure:
#  balances[user_a_id][user_b_id] = X
#  → means user_a is OWED X by user_b (user_b owes user_a)
#  → Positive = user_a gets money FROM user_b
#  → Negative = user_a OWES user_b
#
#  RELATIONSHIPS:
#  SplitwiseService ──*──> User           (registered users)
#  SplitwiseService ──*──> Expense        (recorded expenses)
#  Expense ──1──> SplitStrategy          (how to split the bill)
#  Expense ──1──> User (payer)           (who paid)
#  Expense ──*──> User (members)         (who shares the split)
#  EqualSplit ──▷── SplitStrategy        (implements: amount/n each)
#  ExactSplit ──▷── SplitStrategy        (implements: fixed amounts)
#  PercentSplit ──▷── SplitStrategy      (implements: % based)
#  Thread-safe: _lock guards balances dict and expense list
# ==============================================================================
# fmt: on
import threading
import uuid
from abc import ABC, abstractmethod
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import List, Dict, Optional

"""
==============================================================================================
SPLITWISE LOW LEVEL DESIGN (INTERVIEW OPTIMIZED)
==============================================================================================

Key Features:
1. User/Group Management: Create users, groups, and manage membership.
2. Expense Management: Supports Equal, Exact, and Percentage splits.
3. Balance Calculation: Tracks "Who owes Whom" across users.
4. Settlement: Logic to clear debts between users.
5. Concurrency: Thread-safe balance updates.
6. Precision: Decimal for financial accuracy.

Design Patterns:
1. Facade: SplitwiseService (Central Controller).
2. Strategy/Polymorphism: Split types (Equal, Exact, Percent).

Class Design Diagram:
---------------------
[SplitwiseService] "1" *-- "*" [User]
[SplitwiseService] "1" *-- "*" [Group]
[Group] "1" *-- "*" [Expense]
[Expense] "1" *-- "*" [Split]
[Expense] "1" *-- "1" [User] (PaidBy)
[Split] <|-- [EqualSplit]
[Split] <|-- [ExactSplit]
[Split] <|-- [PercentSplit]
[User] ..> [BalanceSheet] (Map<User, Decimal>)

Class Details:
---------------------
1. SplitwiseService (Facade)
   - Role: Main controller.
   - Methods: addExpense(), settleBalance(), showBalances().

2. Expense
   - Role: Represents a financial transaction shared between users.
   - Attributes: amount, paidBy, splits (List), splitType.

3. Split (Abstract)
   - Role: Represents a share of an expense for one user.
   - Subclasses: EqualSplit, ExactSplit, PercentSplit.

4. SplitType (Enum)
   - Types: EQUAL, EXACT, PERCENT.

5. User
   - Role: Participant.
   - Attributes: id, name, email.
"""

# ==========================================
# Enums & Models
# ==========================================

class SplitType(Enum):
    EQUAL = "EQUAL"
    EXACT = "EXACT"
    PERCENT = "PERCENT"

class User:
    def __init__(self, user_id: str, name: str, email: str = ""):
        self.id = user_id
        self.name = name
        self.email = email

    def __repr__(self):
        return f"User({self.name})"

# ==========================================
# Split Strategy Pattern
# ==========================================

class Split(ABC):
    def __init__(self, user: User, amount: Decimal = Decimal("0.00")):
        self.user = user
        self.amount = amount

class EqualSplit(Split):
    def __init__(self, user: User):
        super().__init__(user)

class ExactSplit(Split):
    def __init__(self, user: User, amount: Decimal):
        super().__init__(user, amount)

class PercentSplit(Split):
    def __init__(self, user: User, percent: float):
        super().__init__(user)
        self.percent = percent

# ==========================================
# Domain Models
# ==========================================

class Expense:
    """Represents a financial transaction shared between users."""
    def __init__(self, desc: str, amount: Decimal, paid_by: User, splits: List[Split], split_type: SplitType):
        self.id = str(uuid.uuid4())
        self.description = desc
        self.amount = amount
        self.paid_by = paid_by
        self.splits = splits
        self.split_type = split_type

class Group:
    def __init__(self, group_id: str, name: str):
        self.id = group_id
        self.name = name
        self.members: Dict[str, User] = {}
        self.expenses: List[Expense] = []

    def add_member(self, user: User):
        self.members[user.id] = user

    def add_expense(self, expense: Expense):
        self.expenses.append(expense)

# ==========================================
# Service Manager (Facade)
# ==========================================

class SplitwiseService:
    """Facade for managing users, groups, and expenses."""
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.groups: Dict[str, Group] = {}
        # Balance Sheet: Map[User1_ID, Map[User2_ID, Decimal]]
        # Positive: User1 is owed by User2. Negative: User1 owes User2.
        self.balance_sheet: Dict[str, Dict[str, Decimal]] = {}
        self._lock = threading.Lock()
        print("INFO: SplitwiseService initialized.")

    def add_user(self, user: User):
        self.users[user.id] = user
        self.balance_sheet[user.id] = {}

    def add_group(self, group: Group):
        self.groups[group.id] = group

    def add_expense(self, desc: str, amount: Decimal, paid_by: User, splits: List[Split], split_type: SplitType):
        """Processes an expense and updates balances across all participants."""
        self._calculate_splits(amount, splits, split_type)

        with self._lock:
            for split in splits:
                paid_to = split.user
                if paid_by.id == paid_to.id:
                    continue
                # paidBy gets back split.amount from paid_to
                self._update_balance(paid_by.id, paid_to.id, split.amount)
                # paid_to owes split.amount to paidBy
                self._update_balance(paid_to.id, paid_by.id, -split.amount)

        print(f"INFO: Expense '{desc}' - {amount} paid by {paid_by.name}")

    def _calculate_splits(self, total: Decimal, splits: List[Split], split_type: SplitType):
        if split_type == SplitType.EQUAL:
            split_amt = (total / len(splits)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            for s in splits:
                s.amount = split_amt
            # Fix rounding remainder on first split
            total_calc = split_amt * len(splits)
            if total_calc != total:
                splits[0].amount += (total - total_calc)

        elif split_type == SplitType.PERCENT:
            for s in splits:
                if isinstance(s, PercentSplit):
                    s.amount = (total * Decimal(str(s.percent)) / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        # EXACT: s.amount is already provided

    def _update_balance(self, u1_id: str, u2_id: str, amount: Decimal):
        balances = self.balance_sheet[u1_id]
        balances[u2_id] = balances.get(u2_id, Decimal("0.00")) + amount

    def settle_balance(self, paid_by: User, paid_to: User, amount: Decimal):
        """Processes a settlement transaction between two users."""
        with self._lock:
            self._update_balance(paid_by.id, paid_to.id, amount)
            self._update_balance(paid_to.id, paid_by.id, -amount)
        print(f"INFO: Settled: {paid_by.name} paid {amount} to {paid_to.name}")

    def show_balances(self, user_id: str):
        """Prints all debts/receivables for a specific user."""
        balances = self.balance_sheet.get(user_id, {})
        user_name = self.users[user_id].name
        non_zero = [(self.users[oid].name, amt) for oid, amt in balances.items() if abs(amt) > Decimal("0.00")]
        if not non_zero:
            print(f"INFO: No pending balances for {user_name}.")
            return
        for other_name, amount in non_zero:
            if amount > 0:
                print(f"INFO: {user_name} gets back ${amount} from {other_name}")
            else:
                print(f"INFO: {user_name} owes ${abs(amount)} to {other_name}")

# ==========================================
# Main Execution / Demo
# ==========================================

if __name__ == "__main__":
    print("--- Starting Splitwise System Demo ---")

    service = SplitwiseService()

    alice = User("U1", "Alice")
    bob = User("U2", "Bob")
    charlie = User("U3", "Charlie")
    service.add_user(alice)
    service.add_user(bob)
    service.add_user(charlie)

    print("\n[Scenario 1] Alice pays 300 for Lunch (Equal split with Bob & Charlie)")
    splits1 = [EqualSplit(alice), EqualSplit(bob), EqualSplit(charlie)]
    service.add_expense("Lunch", Decimal("300"), alice, splits1, SplitType.EQUAL)
    service.show_balances("U2")  # Bob owes Alice 100

    print("\n[Scenario 2] Bob pays 100 for Cab (Alice owes 30, Bob keeps 70)")
    splits2 = [ExactSplit(alice, Decimal("30")), ExactSplit(bob, Decimal("70"))]
    service.add_expense("Cab", Decimal("100"), bob, splits2, SplitType.EXACT)
    service.show_balances("U1")  # Alice owes Bob 30

    print("\n[Scenario 3] Alice pays 100 to Bob to settle partially.")
    service.settle_balance(alice, bob, Decimal("100"))
    service.show_balances("U1")
    service.show_balances("U3")  # Charlie still owes Alice 100
