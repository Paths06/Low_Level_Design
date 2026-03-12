# fmt: off
# ==============================================================================
#  STOCK BROKERAGE SYSTEM — ASCII CLASS DIAGRAM
# ==============================================================================
#
#  ┌──────────────────────────────────────────────────────────────────────────┐
#  │                      STOCK BROKERAGE SYSTEM                              │
#  └──────────────────────────────────────────────────────────────────────────┘
#
#  ┌──────────────────────────┐     ┌──────────────────────────────────────┐
#  │     BrokerageService     │     │           StockExchange              │
#  │        (Facade)          │────>│ (OrderBook + Matching Engine)        │
#  ├──────────────────────────┤     ├──────────────────────────────────────┤
#  │ + exchange: StockExch.   │     │ + order_books: Dict[sym, OrderBook]  │
#  │ + users: Dict            │     │ - _lock: Lock                        │
#  ├──────────────────────────┤     ├──────────────────────────────────────┤
#  │ + register_user()        │     │ + place_order(order)                 │
#  │ + deposit()              │     │ + get_order_book_summary()           │
#  │ + place_order()          │     │ -_match_orders(symbol)               │
#  └──────────────────────────┘     └──────────────────────────────────────┘
#                                                    │ 1..*
#                                                    ▼
#  ┌─────────────────────────────────────────────────────────────────────────┐
#  │                         OrderBook (per symbol)                          │
#  ├─────────────────────────────────────────────────────────────────────────┤
#  │ + symbol: str                                                           │
#  │ + buy_orders : MaxHeap (price DESC) ← highest bid matched first        │
#  │ + sell_orders: MinHeap (price ASC)  ← lowest ask matched first         │
#  │ + trades: List[Trade]                                                   │
#  ├─────────────────────────────────────────────────────────────────────────┤
#  │ + add_order(order)                                                      │
#  │ + match() → executes trades when buy_price >= sell_price               │
#  └─────────────────────────────────────────────────────────────────────────┘
#
#  ┌─────────────────────────────────┐   ┌────────────────────────────────┐
#  │             Order               │   │             Trade              │
#  ├─────────────────────────────────┤   ├────────────────────────────────┤
#  │ + id: str                       │   │ + trade_id: str                │
#  │ + user_id: str                  │   │ + buy_order: Order             │
#  │ + symbol: str                   │   │ + sell_order: Order            │
#  │ + order_type: OrderType (enum)  │   │ + quantity: int                │
#  │ + price: Decimal                │   │ + price: Decimal               │
#  │ + quantity: int                 │   ├────────────────────────────────┤
#  │ + remaining_quantity: int       │   │ + __repr__()                   │
#  │ + status: OrderStatus (enum)    │   └────────────────────────────────┘
#  └─────────────────────────────────┘
#
#  ┌───────────────────────────────────────────────────────────┐
#  │                        User / Portfolio                   │
#  ├───────────────────────────────────────────────────────────┤
#  │ + id, name: str                                           │
#  │ + cash_balance: Decimal                                   │
#  │ + portfolio: Dict[symbol, quantity]                       │
#  │ - _lock: Lock                                             │
#  ├───────────────────────────────────────────────────────────┤
#  │ + deposit(amount)                                         │
#  │ + deduct(amount) / add_shares() / deduct_shares()         │
#  └───────────────────────────────────────────────────────────┘
#
#  ┌──────────────────┐   ┌────────────────────┐
#  │  OrderType (Enum)│   │ OrderStatus (Enum) │
#  ├──────────────────┤   ├────────────────────┤
#  │  BUY / SELL      │   │ OPEN / PARTIAL     │
#  └──────────────────┘   │ FILLED / CANCELLED │
#                         └────────────────────┘
#
#  MATCHING ENGINE LOGIC (Price-Time Priority):
#  - BUY orders sorted by price DESC  (max-heap via negation)
#  - SELL orders sorted by price ASC  (min-heap)
#  - Match when top_bid.price >= top_ask.price
#  - Trade quantity = min(buy.remaining, sell.remaining)
#  - Partial fills supported via remaining_quantity
#
#  RELATIONSHIPS:
#  BrokerageService ──1──> StockExchange      (delegates order routing)
#  BrokerageService ──*──> User               (manages accounts)
#  StockExchange ──*──> OrderBook             (one per traded symbol)
#  OrderBook ──*──> Order (buy heap)          (open buy orders)
#  OrderBook ──*──> Order (sell heap)         (open sell orders)
#  OrderBook ──*──> Trade                     (execution history)
# ==============================================================================
# fmt: on
import heapq
import threading
import uuid
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import List, Dict, Optional, Tuple

"""
==============================================================================================
STOCK BROKERAGE SYSTEM LOW LEVEL DESIGN (INTERVIEW OPTIMIZED)
==============================================================================================

Key Features:
1. Multi-User Support: Each user has an account (cash) and a portfolio (stocks).
2. Order Book: Limit-order matching engine using priority queues.
3. Order Lifecycle: PENDING -> COMPLETED / REJECTED.
4. Concurrency: Thread-safe matching and account/portfolio updates.
5. Financial Precision: Decimal for all monetary calculations.

Design Patterns:
1. Facade: BrokerageService (Central Gateway).
2. Strategy/Polymorphism: Order types (Buy/Sell).
3. Observer: (Implicit) Notifications via print logging.

Class Design Diagram:
---------------------
[BrokerageService] "1" *-- "*" [Account]
[BrokerageService] "1" *-- "*" [Portfolio]
[BrokerageService] "1" *-- "*" [OrderBook]
[Account] : Manages cash balance
[Portfolio] "1" *-- "*" [Holding]
[OrderBook] "1" *-- "*" [Order]
[Order] <|-- [BuyOrder]
[Order] <|-- [SellOrder]

Class Details:
---------------------
1. BrokerageService (Facade)
   - Role: Main controller.
   - Methods: registerUser(), placeOrder(), executeTrade().

2. OrderBook
   - Role: Maintains and matches buy/sell orders for a symbol.
   - Logic: Bids (max-heap), Asks (min-heap). Matches when bid >= ask.

3. Order
   - Attributes: symbol, quantity, type (BUY/SELL), price, status.

4. Account
   - Role: Manages cash balance with thread-safe deposit/withdraw.

5. Portfolio
   - Role: Manages stock holdings with thread-safe add/remove.
"""

# ==========================================
# Enums & Models
# ==========================================

class OrderStatus(Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class OrderType(Enum):
    BUY = "BUY"
    SELL = "SELL"

class Account:
    """Manages cash balance for a user."""
    def __init__(self, initial_balance: Decimal = Decimal("0.00")):
        self.balance = initial_balance
        self._lock = threading.Lock()

    def deposit(self, amount: Decimal):
        with self._lock:
            self.balance += amount
            print(f"INFO: Deposited {amount}. New balance: {self.balance}")

    def withdraw(self, amount: Decimal) -> bool:
        with self._lock:
            if self.balance >= amount:
                self.balance -= amount
                return True
            return False

class Portfolio:
    """Manages stock holdings for a user."""
    def __init__(self):
        self.holdings: Dict[str, int] = {}
        self._lock = threading.Lock()

    def add_stock(self, symbol: str, quantity: int):
        with self._lock:
            self.holdings[symbol] = self.holdings.get(symbol, 0) + quantity

    def remove_stock(self, symbol: str, quantity: int) -> bool:
        with self._lock:
            current = self.holdings.get(symbol, 0)
            if current >= quantity:
                self.holdings[symbol] = current - quantity
                if self.holdings[symbol] == 0:
                    del self.holdings[symbol]
                return True
            return False

# ==========================================
# Order Models
# ==========================================

class Order:
    """Represents a trading order."""
    def __init__(self, user_id: str, symbol: str, quantity: int, price: Decimal, order_type: OrderType):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.symbol = symbol
        self.quantity = quantity
        self.price = price
        self.type = order_type
        self.status = OrderStatus.PENDING

    def __lt__(self, other):
        return self.price < other.price

# ==========================================
# Order Book & Matching Engine
# ==========================================

class OrderBook:
    """Maintains and matches orders for a specific symbol."""
    def __init__(self, symbol: str):
        self.symbol = symbol
        # Bids (Buys): Max-heap (stored as negative prices)
        self.bids: List[Tuple[Decimal, Order]] = []
        # Asks (Sells): Min-heap
        self.asks: List[Tuple[Decimal, Order]] = []
        self._lock = threading.Lock()

    def add_order(self, order: Order, service: 'BrokerageService'):
        with self._lock:
            if order.type == OrderType.BUY:
                heapq.heappush(self.bids, (-order.price, order))
            else:
                heapq.heappush(self.asks, (order.price, order))
            self._match_orders(service)

    def _match_orders(self, service: 'BrokerageService'):
        """Tries to match top bid and top ask."""
        while self.bids and self.asks:
            top_bid_neg, top_bid = self.bids[0]
            top_ask_price, top_ask = self.asks[0]
            top_bid_price = -top_bid_neg

            if top_bid_price >= top_ask_price:
                trade_qty = min(top_bid.quantity, top_ask.quantity)
                if service.execute_trade(top_bid.user_id, top_ask.user_id, self.symbol, trade_qty, top_ask_price):
                    print(f"INFO: TRADE EXECUTED: {trade_qty} {self.symbol} @ {top_ask_price}")
                    top_bid.quantity -= trade_qty
                    top_ask.quantity -= trade_qty
                    if top_bid.quantity == 0:
                        top_bid.status = OrderStatus.COMPLETED
                        heapq.heappop(self.bids)
                    if top_ask.quantity == 0:
                        top_ask.status = OrderStatus.COMPLETED
                        heapq.heappop(self.asks)
                else:
                    print("ERROR: Trade failed. Removing problematic order.")
                    heapq.heappop(self.bids)
                    break
            else:
                break

    def get_summary(self):
        with self._lock:
            return {
                "bids": len(self.bids),
                "asks": len(self.asks),
                "top_bid": -self.bids[0][0] if self.bids else None,
                "top_ask": self.asks[0][0] if self.asks else None
            }

# ==========================================
# Brokerage Service (Facade)
# ==========================================

class BrokerageService:
    """Central gateway for the stock brokerage system."""
    def __init__(self):
        self.accounts: Dict[str, Account] = {}
        self.portfolios: Dict[str, Portfolio] = {}
        self.order_books: Dict[str, OrderBook] = {}
        print("INFO: Brokerage Service initialized.")

    def register_user(self, user_id: str, name: str):
        self.accounts[user_id] = Account()
        self.portfolios[user_id] = Portfolio()
        print(f"INFO: User {name} ({user_id}) registered.")

    def place_order(self, order: Order):
        """Validates and places an order into the appropriate order book."""
        if order.type == OrderType.BUY:
            total_cost = order.price * order.quantity
            acc = self.accounts.get(order.user_id)
            if not acc or acc.balance < total_cost:
                print(f"ERROR: Insufficient funds for order {order.id}")
                order.status = OrderStatus.REJECTED
                return
        else:
            port = self.portfolios.get(order.user_id)
            if not port or port.holdings.get(order.symbol, 0) < order.quantity:
                print(f"ERROR: Insufficient stocks for order {order.id}")
                order.status = OrderStatus.REJECTED
                return

        if order.symbol not in self.order_books:
            self.order_books[order.symbol] = OrderBook(order.symbol)

        print(f"INFO: Order Placed: {order.type.value} {order.quantity} {order.symbol} @ {order.price}")
        self.order_books[order.symbol].add_order(order, self)

    def execute_trade(self, buyer_id: str, seller_id: str, symbol: str, qty: int, price: Decimal) -> bool:
        """Atomically transfers funds and stocks between users."""
        total_cost = price * Decimal(qty)
        if not self.accounts[buyer_id].withdraw(total_cost):
            return False
        if not self.portfolios[seller_id].remove_stock(symbol, qty):
            self.accounts[buyer_id].deposit(total_cost)  # Rollback
            return False
        self.portfolios[buyer_id].add_stock(symbol, qty)
        self.accounts[seller_id].deposit(total_cost)
        return True

# ==========================================
# Main Execution / Demo
# ==========================================

if __name__ == "__main__":
    print("--- Starting Stock Brokerage Demo ---")

    broker = BrokerageService()

    broker.register_user("U1", "Buyer Bob")
    broker.register_user("U2", "Seller Sally")

    broker.accounts["U1"].deposit(Decimal("5000.00"))
    broker.portfolios["U2"].add_stock("AAPL", 100)

    print("\n[Scenario] Bob wants to buy 10 AAPL @ 150. Sally sells 5 AAPL @ 150 (Partial fill).")
    broker.place_order(Order("U1", "AAPL", 10, Decimal("150.00"), OrderType.BUY))
    broker.place_order(Order("U2", "AAPL", 5, Decimal("150.00"), OrderType.SELL))

    print(f"\nBob's Balance: ${broker.accounts['U1'].balance}")
    print(f"Bob's Portfolio: {broker.portfolios['U1'].holdings}")
    print(f"Sally's Balance: ${broker.accounts['U2'].balance}")
    print(f"Sally's Portfolio: {broker.portfolios['U2'].holdings}")

    print("\n[Scenario] Sally sells at 160 (No Match - spread)")
    broker.place_order(Order("U2", "AAPL", 20, Decimal("160.00"), OrderType.SELL))
    print(f"Order Book Summary: {broker.order_books['AAPL'].get_summary()}")
