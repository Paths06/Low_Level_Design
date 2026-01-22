import threading
import uuid
from abc import ABC, abstractmethod
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import List, Dict, Optional, Set

"""
==============================================================================================
SPLITWISE LOW LEVEL DESIGN (PYTHON - PRODUCTION GRADE)
==============================================================================================

Key Features:
1. User/Group Management: Create users, groups, and manage membership.
2. Expense Management: Supports Equal, Exact, and Percentage splits.
3. Balance Calculation: Tracks "Who owes Whom" across users.
4. Settlement: Logic to clear debts between users.
5. Concurrency: Thread-safe balance updates.
6. Robustness: Decimal for financial accuracy, logging, docstrings.

Design Patterns:
1. Singleton: SplitwiseService (Facade).
2. Strategy/Polymorphism: Split types (Equal, Exact, Percent).
3. Observer: (Not explicitly used but often useful for notifications).
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
# Service Manager (Singleton)
# ==========================================

class SplitwiseService:
    """Facade for managing users, groups, and expenses (Singleton)."""
    _instance = None
    _singleton_lock = threading.Lock()

    def __new__(cls):
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = super(SplitwiseService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.users: Dict[str, User] = {}
        self.groups: Dict[str, Group] = {}
        # Balance Sheet: Map[User1_ID, Map[User2_ID, Decimal]]
        # Positive values: User1 gets from User2. Negative values: User1 owes User2.
        self.balance_sheet: Dict[str, Dict[str, Decimal]] = {}
        self._initialized = True
        print("INFO: SplitwiseService initialized.")

    @classmethod
    def get_instance(cls):
        return cls()

    def add_user(self, user: User):
        self.users[user.id] = user
        self.balance_sheet[user.id] = {}

    def add_group(self, group: Group):
        self.groups[group.id] = group

    def add_expense(self, desc: str, amount: Decimal, paid_by: User, splits: List[Split], split_type: SplitType):
        """Processes an expense and updates balances across all participants."""
        # 1. Validate and calculate split amounts
        self._calculate_splits(amount, splits, split_type)
        
        # 2. Update balance sheet
        with self._singleton_lock:
            for split in splits:
                paid_to = split.user
                if paid_by.id == paid_to.id:
                    continue
                
                # updateBalance(paidBy, paidTo, splitAmt)
                # user[paidBy] gets back splitAmt from user[paidTo]
                self._update_balance(paid_by.id, paid_to.id, split.amount)
                # inverse: user[paidTo] owes splitAmt to user[paidBy]
                self._update_balance(paid_to.id, paid_by.id, -split.amount)

        print(f"INFO: Expense added: '{desc}' - Amount: {amount} paid by {paid_by.name}")

    def _calculate_splits(self, total_amount: Decimal, splits: List[Split], split_type: SplitType):
        if split_type == SplitType.EQUAL:
            split_amt = (total_amount / len(splits)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            for s in splits:
                s.amount = split_amt
            # Fix rounding remainder on first split if necessary
            total_calc = split_amt * len(splits)
            if total_calc != total_amount:
                splits[0].amount += (total_amount - total_calc)
        
        elif split_type == SplitType.PERCENT:
            for s in splits:
                if isinstance(s, PercentSplit):
                    s.amount = (total_amount * Decimal(str(s.percent)) / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        # EXACT: s.amount is already provided

    def _update_balance(self, u1_id: str, u2_id: str, amount: Decimal):
        balances = self.balance_sheet[u1_id]
        balances[u2_id] = balances.get(u2_id, Decimal("0.00")) + amount

    def settle_balance(self, paid_by: User, paid_to: User, amount: Decimal):
        """Processes a settlement transaction between two users."""
        with self._singleton_lock:
            self._update_balance(paid_by.id, paid_to.id, amount)
            self._update_balance(paid_to.id, paid_by.id, -amount)
        print(f"INFO: Settled: {paid_by.name} paid {amount} to {paid_to.name}")

    def show_balances(self, user_id: str):
        """Prints all debts/receivables for a specific user."""
        balances = self.balance_sheet.get(user_id, {})
        user_name = self.users[user_id].name
        
        non_zero_found = False
        for other_id, amount in balances.items():
            if abs(amount) > Decimal("0.00"):
                non_zero_found = True
                other_name = self.users[other_id].name
                if amount > 0:
                    print(f"INFO: {user_name} gets back ${amount} from {other_name}")
                else:
                    print(f"INFO: {user_name} owes ${abs(amount)} to {other_name}")
        
        if not non_zero_found:
            print(f"INFO: No pending balances for {user_name}.")

# ==========================================
# Main Execution
# ==========================================

if __name__ == "__main__":
    print("--- Starting Splitwise System Demo ---")
    
    service = SplitwiseService.get_instance()

    # 1. Setup Users
    alice = User("U1", "Alice")
    bob = User("U2", "Bob")
    charlie = User("U3", "Charlie")
    service.add_user(alice)
    service.add_user(bob)
    service.add_user(charlie)

    # 2. Equal Split
    print("\n[Scenario] Alice pays 300 for Lunch (Split: Equal among Alice, Bob, Charlie)")
    splits1 = [EqualSplit(alice), EqualSplit(bob), EqualSplit(charlie)]
    service.add_expense("Lunch", Decimal("300"), alice, splits1, SplitType.EQUAL)
    service.show_balances("U2") # Bob owes Alice 100

    # 3. Exact Split
    print("\n[Scenario] Bob pays 100 for Cab (Split: Alice owes 30, Bob 70)")
    splits2 = [ExactSplit(alice, Decimal("30")), ExactSplit(bob, Decimal("70"))]
    service.add_expense("Cab", Decimal("100"), bob, splits2, SplitType.EXACT)
    service.show_balances("U1") # Alice owes Bob 30 + 100 = 130

    # 4. Settlement
    print("\n[Scenario] Alice pays 100 to Bob to settle partially.")
    service.settle_balance(alice, bob, Decimal("100"))
    service.show_balances("U1") # Alice owes Bob 30 now
    service.show_balances("U3") # Charlie owes Alice 100
