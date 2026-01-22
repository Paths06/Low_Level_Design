import threading
from abc import ABC, abstractmethod
from decimal import Decimal
from enum import Enum
from typing import Dict, Optional, Any

"""
==============================================================================================
VENDING MACHINE LOW LEVEL DESIGN (PYTHON - PRODUCTION GRADE)
==============================================================================================

Key Features:
1. State Pattern: Manages machine lifecycle (Idle -> Ready -> Dispense -> SoldOut).
2. Strategy/Polymorphism: Handles payment denominations (Coin/Note).
3. Thread-safe Inventory: Concurrent access to stock updates.
4. Financial Precision: Uses Decimal for all currency calculations.
5. Production Standards: Logging, type hints, docstrings, and robust error handling.

Design Patterns:
1. State Pattern: Encapsulates state-specific behavior.
2. Singleton: VendingMachine (Context).
3. Strategy: Implicitly handled via State transitions.
"""

# ==========================================
# Enums & Models
# ==========================================

class Coin(Enum):
    PENNY = Decimal("0.01")
    NICKEL = Decimal("0.05")
    DIME = Decimal("0.10")
    QUARTER = Decimal("0.25")

class Note(Enum):
    ONE = Decimal("1.00")
    FIVE = Decimal("5.00")
    TEN = Decimal("10.00")
    TWENTY = Decimal("20.00")

class Product:
    """Represents an item available in the vending machine."""
    def __init__(self, name: str, price: Decimal):
        self.name = name
        self.price = price

    def __repr__(self):
        return f"{self.name} (${self.price})"

class Inventory:
    """Manages stock of products in the machine."""
    def __init__(self):
        self._stock: Dict[str, int] = {}
        self._products: Dict[str, Product] = {}
        self._lock = threading.Lock()

    def add_product(self, product: Product, quantity: int):
        with self._lock:
            self._products[product.name] = product
            self._stock[product.name] = self._stock.get(product.name, 0) + quantity

    def is_available(self, product_name: str) -> bool:
        return self._stock.get(product_name, 0) > 0

    def deduct(self, product_name: str):
        with self._lock:
            if self.is_available(product_name):
                self._stock[product_name] -= 1

    def get_product(self, product_name: str) -> Optional[Product]:
        return self._products.get(product_name)

# ==========================================
# State Pattern Implementation
# ==========================================

class VendingMachineState(ABC):
    """Abstract base class for all vending machine states."""
    
    @abstractmethod
    def select_product(self, product_name: str):
        pass

    @abstractmethod
    def insert_money(self, amount: Decimal):
        pass

    @abstractmethod
    def dispense(self):
        pass

    @abstractmethod
    def abort(self):
        pass

class IdleState(VendingMachineState):
    """Machine is waiting for a product selection."""
    def __init__(self, vm: 'VendingMachine'):
        self.vm = vm

    def select_product(self, product_name: str):
        product = self.vm.inventory.get_product(product_name)
        if not product:
            print(f"ERROR: Invalid product selection: {product_name}")
            return
        
        if self.vm.inventory.is_available(product_name):
            self.vm.selected_product = product
            self.vm.set_state(self.vm.ready_state)
            print(f"INFO: Product selected: {product.name}. Price: ${product.price}")
        else:
            print(f"WARNING: Product out of stock: {product_name}")

    def insert_money(self, amount: Decimal):
        print("WARNING: Please select a product first.")

    def dispense(self):
        print("WARNING: Select product and pay first.")

    def abort(self):
        print("INFO: Nothing to cancel.")

class ReadyState(VendingMachineState):
    """Product selected, waiting for sufficient payment."""
    def __init__(self, vm: 'VendingMachine'):
        self.vm = vm

    def select_product(self, product_name: str):
        print("WARNING: Product already selected. Abort to change selection.")

    def insert_money(self, amount: Decimal):
        self.vm.current_balance += amount
        print(f"INFO: Inserted: ${amount}. Current balance: ${self.vm.current_balance}")
        
        if self.vm.current_balance >= self.vm.selected_product.price:
            print("INFO: Sufficient funds inserted.")

    def dispense(self):
        if not self.vm.selected_product:
             print("ERROR: No product selected!")
             self.vm.set_state(self.vm.idle_state)
             return

        if self.vm.current_balance >= self.vm.selected_product.price:
            self.vm.set_state(self.vm.dispense_state)
            self.vm.current_state.dispense() # Forward call
        else:
            needed = self.vm.selected_product.price - self.vm.current_balance
            print(f"WARNING: Insufficient funds. Need ${needed} more.")

    def abort(self):
        print(f"INFO: Aborting transaction. Refunding: ${self.vm.current_balance}")
        self.vm.reset()
        self.vm.set_state(self.vm.idle_state)

class DispenseState(VendingMachineState):
    """Processing the vending and calculating change."""
    def __init__(self, vm: 'VendingMachine'):
        self.vm = vm

    def select_product(self, product_name: str):
        print("WARNING: Dispensing in progress...")

    def insert_money(self, amount: Decimal):
        print("WARNING: Dispensing in progress...")

    def dispense(self):
        product = self.vm.selected_product
        self.vm.inventory.deduct(product.name)
        
        change = self.vm.current_balance - product.price
        print(f"INFO: DISPENSING: {product.name}")
        if change > 0:
            print(f"INFO: RETURNING CHANGE: ${change}")
        
        self.vm.reset()
        self.vm.set_state(self.vm.idle_state)

    def abort(self):
        print("ERROR: Cannot abort during dispensing process.")

# ==========================================
# Vending Machine Context (Singleton)
# ==========================================

class VendingMachine:
    """Context class representing the Vending Machine (Singleton)."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(VendingMachine, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self.inventory = Inventory()
        
        # States
        self.idle_state = IdleState(self)
        self.ready_state = ReadyState(self)
        self.dispense_state = DispenseState(self)
        
        self.current_state = self.idle_state
        self.selected_product: Optional[Product] = None
        self.current_balance = Decimal("0.00")
        
        self._initialized = True
        print("INFO: Vending Machine initialized.")

    @classmethod
    def get_instance(cls):
        return cls()

    def set_state(self, state: VendingMachineState):
        self.current_state = state

    def select_product(self, name: str):
        self.current_state.select_product(name)

    def insert_money(self, money: Any):
        amount = Decimal("0.00")
        if isinstance(money, (Coin, Note)):
            amount = money.value
        elif isinstance(money, (int, float, str, Decimal)):
            amount = Decimal(str(money))
        
        self.current_state.insert_money(amount)

    def dispense(self):
        self.current_state.dispense()

    def abort(self):
        self.current_state.abort()

    def reset(self):
        self.selected_product = None
        self.current_balance = Decimal("0.00")

# ==========================================
# Main Execution / Demo
# ==========================================

if __name__ == "__main__":
    print("--- Starting Vending Machine Demo ---")

    vm = VendingMachine.get_instance()

    # 1. Setup Inventory
    vm.inventory.add_product(Product("Coke", Decimal("1.25")), 5)
    vm.inventory.add_product(Product("Pepsi", Decimal("1.50")), 1)
    vm.inventory.add_product(Product("Chips", Decimal("0.75")), 10)

    # 2. Test Transaction: Successful with exact change
    print("\n[Scenario 1] Buying Coke with exact change")
    vm.select_product("Coke")
    vm.insert_money(Note.ONE)
    vm.insert_money(Coin.QUARTER)
    vm.dispense()

    # 3. Test Transaction: Successful with excess change
    print("\n[Scenario 2] Buying Chips with $5 Note")
    vm.select_product("Chips")
    vm.insert_money(Note.FIVE)
    vm.dispense()

    # 4. Test Transaction: Sold Out
    print("\n[Scenario 3] Buying last Pepsi")
    vm.select_product("Pepsi")
    vm.insert_money(Note.FIVE)
    vm.dispense()
    
    print("\n[Scenario 4] Attempting to buy Pepsi again (Sold Out)")
    vm.select_product("Pepsi")

    # 5. Test Abort
    print("\n[Scenario 5] Selecting Coke and then Aborting")
    vm.select_product("Coke")
    vm.insert_money(Coin.QUARTER)
    vm.abort()
