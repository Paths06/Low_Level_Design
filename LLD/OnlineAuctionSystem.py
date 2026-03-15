# fmt: off
# ==============================================================================
#  ONLINE AUCTION SYSTEM — ASCII CLASS DIAGRAM
# ==============================================================================
#
#  ┌─────────────────────────────────────────────────────────────────────────┐
#  │                          ONLINE AUCTION SYSTEM                          │
#  └─────────────────────────────────────────────────────────────────────────┘
#
#  ┌─────────────────────────┐
#  │  OnlineAuctionSystem    │  ← Facade
#  ├─────────────────────────┤
#  │ + users: Dict           │
#  │ + auctions: Dict        │
#  ├─────────────────────────┤
#  │ + register_user()       │
#  │ + create_auction()      │
#  │ + search_auctions()     │
#  │ + place_bid()           │
#  └─────────────────────────┘
#            │          │
#        ....│..........│....
#        .   ▼          ▼   .
#  ┌──────────────┐  ┌─────────────────────────┐
#  │     User     │  │       Auction           │  ← Subject (Observer Pattern)
#  ├──────────────┤  ├─────────────────────────┤
#  │ + id: str    │  │ + id: str               │
#  │ + name: str  │  │ + item: Item            │
#  │ + email: str │  │ + seller: User          │
#  ├──────────────┤  │ + status: AuctionStatus │
#  │ + notify()   │◄─┤ + highest_bid: Bid      │
#  └──────────────┘  │ + end_time: datetime    │
#           ▲        │ + subscribers: Set[User]│
#           │        ├─────────────────────────┤
#           │        │ + place_bid()           │
#           │        │ + close_auction()       │
#           │        │ - _notify_subscribers() │
#           │        └─────────────────────────┘
#           │                     │
#           │                     ▼
#  ┌────────┴─────┐  ┌─────────────────────────┐
#  │     Bid      │  │         Item            │
#  ├──────────────┤  ├─────────────────────────┤
#  │ + id: str    │  │ + id: str               │
#  │ + bidder:User│  │ + name: str             │
#  │ + amount: flt│  │ + description: str      │
#  │ + time: dt   │  └─────────────────────────┘
#  └──────────────┘
#
#  RELATIONSHIPS:
#  OnlineAuctionSystem ──*──> User            (registered users)
#  OnlineAuctionSystem ──*──> Auction         (active and past auctions)
#  Auction ──1──> Item                        (the item being auctioned)
#  Auction ──1──> User                        (the seller)
#  Auction ──*──> Bid                         (history of bids)
#  Auction ──*──> User                        (subscribers: seller + bidders)
#  Auction -> User.notify()                   (Observer Pattern: notifies highest bid / closure)
#  Bid ──1──> User                            (who placed the bid)
# ==============================================================================
# fmt: on

import threading
import uuid
import time
from enum import Enum
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta

"""
==============================================================================================
ONLINE AUCTION SYSTEM LOW LEVEL DESIGN (INTERVIEW OPTIMIZED)
==============================================================================================

Key Features Implemented:
1. Auction Management: Create, handle state (ACTIVE, CLOSED), and close auctions.
2. Bidding: Thread-safe bid placement logic, verifying amounts against the current highest.
3. Notifications (Observer Pattern): Users involved in an auction receive notifications 
   when a new highest bid is placed or when the auction closes.
4. Concurrency: Lock mechanisms for concurrent bid placements.

Design Patterns:
1. Facade: OnlineAuctionSystem simplifies access and routes actions.
2. Observer Pattern: The Auction acts as the Subject/Publisher. Users are Observers. 
   When a new valid bid arrives, all observing Users are notified.
3. State Pattern (Modeled as Enum Transitions): Handling AuctionStatus transitions.

"""

# ==========================================
# Enums
# ==========================================

class AuctionStatus(Enum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    CANCELED = "CANCELED"

# ==========================================
# Domain Entities
# ==========================================

class User:
    def __init__(self, name: str, email: str):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.email = email

    def receive_notification(self, message: str):
        """Observer: Method called when subjected object emits an event."""
        print(f"[Email to {self.email}] {message}")

    def __repr__(self):
        return f"{self.name} ({self.id})"


class Item:
    def __init__(self, name: str, description: str):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.description = description

    def __repr__(self):
        return self.name


class Bid:
    def __init__(self, bidder: User, amount: float):
        self.id = str(uuid.uuid4())[:8]
        self.bidder = bidder
        self.amount = amount
        self.timestamp = datetime.now()

    def __repr__(self):
        return f"${self.amount:.2f} by {self.bidder.name}"


# ==========================================
# Core Domain: Auction (The Subject)
# ==========================================

class Auction:
    def __init__(self, item: Item, seller: User, starting_price: float, duration_seconds: int):
        self.id = str(uuid.uuid4())[:8]
        self.item = item
        self.seller = seller
        self.starting_price = starting_price
        
        self.status = AuctionStatus.ACTIVE
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(seconds=duration_seconds)

        self.highest_bid: Optional[Bid] = None
        
        # Thread safety for placing bids
        self._lock = threading.Lock()
        
        # Observers (Subscribers)
        self.subscribers: Set[User] = set()
        self.subscribe(seller)

    def subscribe(self, user: User):
        self.subscribers.add(user)

    def unsubscribe(self, user: User):
        if user in self.subscribers:
            self.subscribers.remove(user)

    def _notify_subscribers(self, message: str):
        for user in self.subscribers:
            user.receive_notification(message)

    def place_bid(self, bidder: User, amount: float) -> bool:
        if self.status != AuctionStatus.ACTIVE:
            print(f"WARN: Auction {self.id} is {self.status.name}. Bid rejected.")
            return False

        if datetime.now() > self.end_time:
            self.close_auction()
            print(f"WARN: Auction {self.id} has ended. Bid rejected.")
            return False

        if bidder == self.seller:
            print("WARN: Sellers cannot bid on their own items.")
            return False

        with self._lock:  # Critical section for concurrent bids
            current_highest = self.highest_bid.amount if self.highest_bid else self.starting_price

            # Must logically beat the highest bid AND the starting price
            if self.highest_bid is None and amount < self.starting_price:
                print(f"WARN: Bid must be at least the starting price of ${self.starting_price:.2f}.")
                return False

            if amount <= current_highest:
                print(f"WARN: Bid ${amount:.2f} too low. Current highest is ${current_highest:.2f}.")
                return False

            # Accepted Bid
            new_bid = Bid(bidder, amount)
            self.highest_bid = new_bid
            self.subscribe(bidder)  # Adding bidder to observer list
            
            print(f"INFO: {bidder.name} successfully placed bid of ${amount:.2f} on {self.item.name}.")
            self._notify_subscribers(f"Update on {self.item.name}: New highest bid is {new_bid}.")
            
            return True

    def close_auction(self):
        with self._lock:
            if self.status == AuctionStatus.CLOSED:
                return

            self.status = AuctionStatus.CLOSED
            if self.highest_bid:
                winner = self.highest_bid.bidder
                amount = self.highest_bid.amount
                msg = f"AUCTION CLOSED! Winner is {winner.name} with a bid of ${amount:.2f} for {self.item.name}."
                self._notify_subscribers(msg)
                
                # Mock Transaction Handling
                print(f"TRANSACTION: Processing payment of ${amount:.2f} from {winner.name} to {self.seller.name}.")
            else:
                msg = f"AUCTION CLOSED! No bids were placed for {self.item.name}."
                self._notify_subscribers(msg)


# ==========================================
# Facade: System Controller
# ==========================================

class OnlineAuctionSystem:
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.auctions: Dict[str, Auction] = {}
        print("INFO: Online Auction System initialized.")

    def register_user(self, name: str, email: str) -> User:
        user = User(name, email)
        self.users[user.id] = user
        return user

    def create_auction(self, seller_id: str, item_name: str, item_desc: str, starting_price: float, duration_seconds: int) -> Optional[Auction]:
        seller = self.users.get(seller_id)
        if not seller:
            print("ERROR: User not found.")
            return None
        
        item = Item(item_name, item_desc)
        auction = Auction(item, seller, starting_price, duration_seconds)
        self.auctions[auction.id] = auction
        print(f"INFO: {seller.name} created an auction for {item.name} starting at ${starting_price:.2f}.")
        return auction

    def get_active_auctions(self) -> List[Auction]:
        return [a for a in self.auctions.values() if a.status == AuctionStatus.ACTIVE and datetime.now() <= a.end_time]


# ==========================================
# Main Execution / Demo
# ==========================================

if __name__ == "__main__":
    print("--- Starting Online Auction System Demo ---")

    system = OnlineAuctionSystem()

    # 1. Register Users
    alice_seller = system.register_user("Alice", "alice@example.com")
    bob_buyer = system.register_user("Bob", "bob@example.com")
    charlie_buyer = system.register_user("Charlie", "charlie@example.com")

    # 2. Add an Auction (Duration 3 seconds)
    auction = system.create_auction(alice_seller.id, "Vintage Rolex", "1980 Submariner", 5000.0, 3)

    print("\n--- Bidding Starts ---")
    
    # Invalid Bid: Below Starting Price
    auction.place_bid(bob_buyer, 4000.0)

    # Bob places a valid bid
    auction.place_bid(bob_buyer, 5500.0)

    # Charlie places a valid bid
    auction.place_bid(charlie_buyer, 6000.0)
    
    # Bob tries to place a lower bid
    auction.place_bid(bob_buyer, 5800.0)

    # Charlie places a new highest bid (Outbidding himself / adding max)
    auction.place_bid(charlie_buyer, 7000.0)

    print("\n--- Waiting for auction to end (3 seconds) ---")
    time.sleep(3.1)

    # Bob tries to bid after auction closes
    auction.place_bid(bob_buyer, 8000.0)

    # Simulate CRON/System Closing the auction manually or it being triggered
    auction.close_auction()

    print("--- Demo Finished ---")
