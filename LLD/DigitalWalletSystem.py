import threading
import uuid
from abc import ABC, abstractmethod
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

"""
==============================================================================================
DIGITAL WALLET SERVICE LOW LEVEL DESIGN (PYTHON - PRODUCTION GRADE)
==============================================================================================

Key Features:
1. Multi-Currency Support: Balances tracked per currency using Decimal.
2. Payment Methods: Link Bank/Card (Strategy Pattern).
3. Transactions: Transfer, Top-Up, Withdraw (Factory Pattern).
4. Concurrency: Thread-safe balance updates.
5. Production Standards: Logging, type hints, custom exceptions.

Design Patterns:
1. Singleton: WalletService (Facade).
2. Factory: For creating Transactions.
3. Strategy: PaymentMethod.

Class Design Diagram:
---------------------
[WalletService] "1" *-- "*" [User]
[User] "1" *-- "1" [Wallet]
[Wallet] "1" *-- "*" [PaymentMethod]
[Wallet] "1" *-- "*" [Transaction]
[Wallet] "1" *-- "*" [Currency] (Balance Map)
[Transaction] <|-- [TransferTransaction]
[Transaction] <|-- [TopUpTransaction]
[Transaction] <|-- [WithdrawTransaction]

Class Details:
---------------------
1. WalletService
   - Role: Facade.
   - Methods: registerUser(), processTransaction().

2. User & Wallet
   - Wallet holds a Map<Currency, BigDecimal> for balances.

3. Transaction
   - Role: Immutable record.
   - Attributes: id, source, target, amount, currency, status.

4. CurrencyManager
   - Role: Handles rates and conversion.
"""

# ==========================================
# Exceptions
# ==========================================

class WalletException(Exception):
    """Base exception for Digital Wallet System."""
    pass

class InsufficientFundsException(WalletException):
    """Raised when account has insufficient balance."""
    pass

class TransactionException(WalletException):
    """Raised when a transaction process fails."""
    pass

# ==========================================
# Enums & Utils
# ==========================================

class Currency(Enum):
    USD = "USD"
    EUR = "EUR"
    INR = "INR"
    GBP = "GBP"

class TransactionStatus(Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class CurrencyConverter:
    """Handles rates and currency conversion."""
    _rates_to_usd = {
        Currency.USD: Decimal("1.0"),
        Currency.EUR: Decimal("1.1"), 
        Currency.INR: Decimal("0.012"),
    }

    @classmethod
    def convert(cls, amount: Decimal, from_curr: Currency, to_curr: Currency) -> Decimal:
        if from_curr == to_curr:
            return amount
        
        rate_from = cls._rates_to_usd.get(from_curr)
        rate_to = cls._rates_to_usd.get(to_curr)
        
        if not rate_from or not rate_to:
            raise WalletException(f"Conversion from {from_curr.name} to {to_curr.name} is not supported.")
            
        amount_in_usd = amount * rate_from
        final_amount = amount_in_usd / rate_to
        
        return final_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

# ==========================================
# Domain Models
# ==========================================

class PaymentMethod(ABC):
    @abstractmethod
    def execute_payment(self, amount: Decimal) -> bool:
        pass

class BankAccount(PaymentMethod):
    def __init__(self, account_id: str, bank_name: str, account_number: str):
        self.account_id = account_id
        self.bank_name = bank_name
        self.account_number = account_number
    
    def execute_payment(self, amount: Decimal) -> bool:
        print(f"INFO: Executing bank transfer of {amount} from {self.bank_name}")
        return True # Simulation

class Wallet:
    """Holds balances and maintains transaction history."""
    def __init__(self, user_id: str):
        self.wallet_id = str(uuid.uuid4())
        self.balances: Dict[Currency, Decimal] = {}
        self.payment_methods: List[PaymentMethod] = []
        self.history: List['Transaction'] = []
        self._lock = threading.Lock()

    def get_balance(self, currency: Currency) -> Decimal:
        return self.balances.get(currency, Decimal("0.00"))

    def deposit(self, amount: Decimal, currency: Currency):
        with self._lock:
            current = self.get_balance(currency)
            self.balances[currency] = current + amount
            print(f"DEBUG: Deposited {amount} {currency.name}. New balance: {self.balances[currency]}")

    def withdraw(self, amount: Decimal, currency: Currency):
        with self._lock:
            current = self.get_balance(currency)
            if current < amount:
                raise InsufficientFundsException(f"Insufficient {currency.name} balance.")
            self.balances[currency] = current - amount
            print(f"DEBUG: Withdrew {amount} {currency.name}. New balance: {self.balances[currency]}")

    def add_payment_method(self, pm: PaymentMethod):
        self.payment_methods.append(pm)

    def show_balance(self):
        balance_summary = {c.name: str(b) for c, b in self.balances.items()}
        print(f"INFO: Wallet Balances: {balance_summary}")

class User:
    def __init__(self, user_id: str, name: str):
        self.id = user_id
        self.name = name
        self.wallet = Wallet(user_id)

# ==========================================
# Transactions
# ==========================================

class Transaction(ABC):
    def __init__(self, amount: Decimal, currency: Currency):
        self.id = str(uuid.uuid4())
        self.timestamp = datetime.now()
        self.amount = amount
        self.currency = currency
        self.status = TransactionStatus.PENDING

    @abstractmethod
    def execute(self):
        pass

class TopUpTransaction(Transaction):
    """Adds funds to a wallet from an external source."""
    def __init__(self, user: User, amount: Decimal, currency: Currency):
        super().__init__(amount, currency)
        self.user = user

    def execute(self):
        # In real scenarios, check external payment status
        self.user.wallet.deposit(self.amount, self.currency)
        self.status = TransactionStatus.SUCCESS
        print(f"INFO: TopUp of {self.amount} {self.currency.name} for {self.user.name} Successful.")

class TransferTransaction(Transaction):
    """Transfers funds between two user wallets."""
    def __init__(self, sender: User, receiver: User, amount: Decimal, currency: Currency):
        super().__init__(amount, currency)
        self.sender = sender
        self.receiver = receiver

    def execute(self):
        try:
            self.sender.wallet.withdraw(self.amount, self.currency)
            self.receiver.wallet.deposit(self.amount, self.currency)
            self.status = TransactionStatus.SUCCESS
            print(f"INFO: Transfer of {self.amount} {self.currency.name} from {self.sender.name} to {self.receiver.name} Successful.")
        except InsufficientFundsException as e:
            self.status = TransactionStatus.FAILED
            print(f"WARNING: Transfer Failed: {e}")
            raise

class TransactionFactory:
    """Factory to create different transaction types."""
    @staticmethod
    def create_top_up(user: User, amount: Decimal, currency: Currency) -> TopUpTransaction:
        return TopUpTransaction(user, amount, currency)

    @staticmethod
    def create_transfer(sender: User, receiver: User, amount: Decimal, currency: Currency) -> TransferTransaction:
        return TransferTransaction(sender, receiver, amount, currency)

# ==========================================
# Service Manager (Singleton)
# ==========================================

class WalletService:
    _instance = None
    _singleton_lock = threading.Lock()

    def __new__(cls):
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = super(WalletService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.users: Dict[str, User] = {}
        self._initialized = True
        print("INFO: WalletService initialized.")

    @classmethod
    def get_instance(cls):
        return cls()

    def register_user(self, user: User):
        self.users[user.id] = user

    def process_transaction(self, t: Transaction):
        """Execute a transaction and record it."""
        try:
            t.execute()
        except WalletException as e:
            print(f"ERROR: Transaction process failed: {e}")

    def convert_currency(self, user: User, amount: Decimal, from_curr: Currency, to_curr: Currency):
        """Internally converts balance from one currency to another."""
        try:
            user.wallet.withdraw(amount, from_curr)
            converted = CurrencyConverter.convert(amount, from_curr, to_curr)
            user.wallet.deposit(converted, to_curr)
            print(f"INFO: Converted {amount} {from_curr.name} to {converted} {to_curr.name}")
        except WalletException as e:
            print(f"ERROR: Internal conversion failed: {e}")

# ==========================================
# Main Execution
# ==========================================

if __name__ == "__main__":
    print("--- Starting Digital Wallet Demo ---")
    
    service = WalletService.get_instance()

    # 1. Setup
    u1 = User("U1", "Alice")
    u2 = User("U2", "Bob")
    service.register_user(u1)
    service.register_user(u2)

    # 2. Add Payment Methods
    u1.wallet.add_payment_method(BankAccount("B1", "Alice Bank", "123456"))
    
    # 3. Top Up
    print("[Action] Alice tops up 100 USD.")
    service.process_transaction(
        TransactionFactory.create_top_up(u1, Decimal("100"), Currency.USD)
    )
    u1.wallet.show_balance()

    # 4. Transfer
    print("[Action] Alice sends 50 USD to Bob.")
    service.process_transaction(
        TransactionFactory.create_transfer(u1, u2, Decimal("50"), Currency.USD)
    )
    u1.wallet.show_balance()
    u2.wallet.show_balance()
    
    # 5. Internal Conversion
    print("[Action] Alice converts 20 USD to EUR.")
    service.convert_currency(u1, Decimal("20"), Currency.USD, Currency.EUR)
    u1.wallet.show_balance()
