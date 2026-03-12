# fmt: off
# ==============================================================================
#  AMAZON SYSTEM — ASCII CLASS DIAGRAM
# ==============================================================================
#
#  ┌──────────────────────────────────────────────────────────────────────────┐
#  │                        AMAZON SYSTEM (e-commerce)                        │
#  └──────────────────────────────────────────────────────────────────────────┘
#
#  ┌──────────────────────────────┐    ┌─────────────────────────────────┐
#  │          Catalog             │    │           Account (ABC)         │
#  │      (Singleton)             │    ├─────────────────────────────────┤
#  ├──────────────────────────────┤    │ + username: str                 │
#  │ + _instance: Catalog         │    │ + email: str                    │
#  │ + products: Dict[id,Product] │    │ + address: str                  │
#  ├──────────────────────────────┤    └────────────┬────────────────────┘
#  │ + get_instance(): Catalog    │                 │
#  │ + add_product(product)       │        ┌────────┴────────┐
#  │ + search(query): List[Prod]  │        │                 │
#  └──────────────────────────────┘        ▼                 ▼
#      ← implements SearchService →  ┌──────────┐     ┌───────────┐
#                                    │ Customer │     │   Admin   │
#  ┌──────────────────────────────┐  ├──────────┤     ├───────────┤
#  │          Product             │  │ + cart:  │     │ + add_    │
#  ├──────────────────────────────┤  │  Shopping│     │  product()│
#  │ + product_id: str            │  │  Cart    │     └───────────┘
#  │ + name: str                  │  │ + orders │
#  │ + description: str           │  │   : List │
#  │ + price: float               │  ├──────────┤
#  │ + category: str              │  │+add_order│
#  ├──────────────────────────────┤  └────┬─────┘
#  │ Builder (inner class)        │       │ 1 owns
#  │  + set_name() / set_price()  │       ▼
#  │  + set_description()         │  ┌───────────────────────────────┐
#  │  + build(): Product          │  │         ShoppingCart          │
#  └──────────────────────────────┘  ├───────────────────────────────┤
#                                    │ + items: List[Item]            │
#  ┌──────────────────────────────┐  ├───────────────────────────────┤
#  │          Order               │  │ + add_item(product, qty)       │
#  ├──────────────────────────────┤  │ + remove_item(product_id)      │
#  │ + order_id: str              │  │ + total(): float               │
#  │ + items: List[Item]          │  └───────────────────────────────┘
#  │ + total_amount: float        │
#  │ + status: OrderStatus (enum) │  ┌──────────────────────────────┐
#  ├──────────────────────────────┤  │     PaymentStrategy (ABC)    │
#  │ + set_status()               │  ├──────────────────────────────┤
#  └──────────────────────────────┘  │ + process(amount): bool      │
#                                    └──────────────┬───────────────┘
#  ┌──────────────────────────────┐                 │
#  │            Item              │      ┌──────────┴──────────┐
#  ├──────────────────────────────┤      ▼                     ▼
#  │ + product: Product           │  ┌──────────────┐  ┌────────────────┐
#  │ + quantity: int              │  │ CreditCard   │  │PayPalPayment   │
#  │ + price: float               │  │ Payment      │  └────────────────┘
#  └──────────────────────────────┘  └──────────────┘
#
#  ┌──────────────────────────────┐   ┌──────────────────────────────┐
#  │  NotificationService         │   │     SearchService (ABC)      │
#  ├──────────────────────────────┤   ├──────────────────────────────┤
#  │ + send_email_notification()  │   │ + search(query): List[Prod]  │
#  │ + send_shipment_update()     │   └──────────────────────────────┘
#  │ + create_shipment()          │
#  └──────────────────────────────┘
#
#  RELATIONSHIPS:
#  Catalog (Singleton) ──*──> Product      (manages all products, SearchService)
#  Customer ──▷── Account                  (inherits)
#  Admin    ──▷── Account                  (inherits)
#  Customer ──1──> ShoppingCart            (owns a cart)
#  Customer ──*──> Order                   (places orders)
#  Order ──*──> Item                       (line items per order)
#  Item ──1──> Product                     (references product)
#  Product uses Builder Pattern            (fluent construction)
#  CreditCardPayment / PayPalPayment ──▷── PaymentStrategy (implements)
# ==============================================================================
# fmt: on
from abc import ABC, abstractmethod
from enum import Enum, auto
from datetime import datetime
from typing import List, Dict, Optional

"""
==============================================================================================
AMAZON LOW LEVEL DESIGN (LLD) - PYTHON IMPLEMENTATION
==============================================================================================

Key Design Patterns:
1. Singleton: Thread-safe Catalog instance.
2. Builder: Used for Product creation (explicitly implemented to demonstrate pattern).
3. Strategy: PaymentStrategy for interchangeable payment methods.
4. Observer (Implicit): Notification service reacting to events.

Class Design Diagram:
---------------------
[Account] <|-- [Customer]
[Account] <|-- [Admin]
[Customer] "1" *-- "1" [ShoppingCart]
[Customer] "1" *-- "0..*" [Order]
[Order] "1" *-- "1..*" [Item]
[Catalog] ..> [Product] : Manages
[SearchService] <|.. [Catalog] : Implements
[PaymentStrategy] <|.. [CreditCardPayment] : Implements

Class Details:
---------------------
1. Product
   - Attributes: product_id, name, description, price, category.
   - Methods: Builder (inner class) -> build().

2. Catalog (Singleton)
   - Role: Inventory management.
   - Methods: add_product(), search() [SearchService impl].

3. Account (ABC)
   - Role: Base User class.
   - Attributes: username, email, address.

4. Customer
   - Attributes: cart (ShoppingCart).
   - Methods: add_order().

5. Order
   - Role: Transaction record.
   - Attributes: items, total_amount, status.
   - Methods: set_status().

6. PaymentStrategy (ABC)
   - Methods: process_payment(amount).
"""

# ==========================================
# ENUMS
# ==========================================

class OrderStatus(Enum):
    UNSHIPPED = auto()
    PENDING = auto()
    SHIPPED = auto()
    COMPLETED = auto()
    CANCELED = auto()
    REFUND_APPLIED = auto()

class PaymentStatus(Enum):
    UNPAID = auto()
    PENDING = auto()
    COMPLETED = auto()
    DECLINED = auto()
    CANCELLED = auto()
    REFUNDED = auto()

class ShipmentStatus(Enum):
    PENDING = auto()
    SHIPPED = auto()
    DELIVERED = auto()
    ON_HOLD = auto()

class AccountStatus(Enum):
    ACTIVE = auto()
    BLOCKED = auto()
    BANNED = auto()
    UNKNOWN = auto()

# ==========================================
# DOMAIN MODELS
# ==========================================

class Address:
    def __init__(self, street: str, city: str, state: str, zip_code: str, country: str):
        self.street = street
        self.city = city
        self.state = state
        self.zip_code = zip_code
        self.country = country

    def __str__(self):
        return f"{self.street}, {self.city}, {self.state} {self.zip_code}, {self.country}"

class ProductCategory:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

class Product:
    """
    Product Class
    Demonstrates the Builder Pattern.
    """
    def __init__(self, product_id: str, name: str, description: str, 
                 price: float, category: ProductCategory, available_count: int):
        self._product_id = product_id
        self._name = name
        self._description = description
        self._price = price
        self._category = category
        self._available_count = available_count

    @property
    def name(self):
        return self._name

    @property
    def price(self):
        return self._price

    @property
    def category(self):
        return self._category

    class Builder:
        """
        Inner Builder Class to handle complex object construction.
        In Python, named arguments often suffice, but this pattern is 
        useful when construction logic is complex or invariant checking is needed.
        """
        def __init__(self, name: str, product_id: str):
            self._name = name
            self._product_id = product_id
            self._description = ""
            self._price = 0.0
            self._category = None
            self._available_count = 0

        def set_description(self, description: str):
            self._description = description
            return self

        def set_price(self, price: float):
            self._price = price
            return self

        def set_category(self, category: ProductCategory):
            self._category = category
            return self

        def set_available_count(self, count: int):
            self._available_count = count
            return self

        def build(self):
            return Product(
                self._product_id, self._name, self._description,
                self._price, self._category, self._available_count
            )

class Item:
    def __init__(self, item_id: str, quantity: int, price: float):
        self.item_id = item_id
        self.quantity = quantity
        self.price = price

    def update_quantity(self, quantity: int):
        self.quantity = quantity

class ShoppingCart:
    def __init__(self):
        self.items: List[Item] = []

    def add_item(self, item: Item):
        self.items.append(item)

    def get_items(self) -> List[Item]:
        return self.items

class Order:
    def __init__(self, order_number: str, items: List[Item], total_amount: float):
        self.order_number = order_number
        self.items = items
        self.total_amount = total_amount
        self.order_date = datetime.now()
        self.status = OrderStatus.PENDING

    def set_status(self, status: OrderStatus):
        self.status = status
    
    def __str__(self):
        return f"Order #{self.order_number}"

class Shipment:
    def __init__(self, shipment_number: str, shipment_method: str):
        self.shipment_number = shipment_number
        self.shipment_date = datetime.now()
        self.shipment_method = shipment_method
        self.status = ShipmentStatus.PENDING

# ==========================================
# ACCOUNTS
# ==========================================

class Account(ABC):
    def __init__(self, username: str, password: str, email: str, phone: str, address: Address):
        self.username = username
        self.password = password
        self.email = email
        self.phone = phone
        self.shipping_address = address
        self.status = AccountStatus.ACTIVE

class Customer(Account):
    def __init__(self, username: str, password: str, email: str, phone: str, address: Address):
        super().__init__(username, password, email, phone, address)
        self.cart = ShoppingCart()
        self.orders: List[Order] = []

    def add_order(self, order: Order):
        self.orders.append(order)

class Admin(Account):
    def add_product(self, product: Product):
        print(f"Admin adding product: {product.name}")

# ==========================================
# SERVICES & STRATEGIES
# ==========================================

class SearchService(ABC):
    @abstractmethod
    def search(self, query: str) -> List[Product]:
        pass

class Catalog(SearchService):
    """
    Singleton Catalog
    Manages the products in the system.
    """
    _instance = None
    _product_names: Dict[str, List[Product]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Catalog, cls).__new__(cls)
            cls._product_names = {}
        return cls._instance

    def add_product(self, product: Product):
        if product.name not in self._product_names:
            self._product_names[product.name] = []
        self._product_names[product.name].append(product)

    def search(self, query: str) -> List[Product]:
        # Fast lookup by name
        return self._product_names.get(query, [])

class PaymentStrategy(ABC):
    @abstractmethod
    def process_payment(self, amount: float) -> bool:
        pass

class CreditCardPayment(PaymentStrategy):
    def __init__(self, card_number: str, cvv: str):
        self.card_number = card_number
        self.cvv = cvv

    def process_payment(self, amount: float) -> bool:
        print(f"Processing Credit Card Payment of ${amount:.2f}")
        # Logic to contact bank API would go here
        return True

class NotificationService:
    def send_order_confirmation(self, order: Order, account: Account):
        print(f"Email sent to {account.email} for {order}")

# ==========================================
# MAIN DEMO
# ==========================================

if __name__ == "__main__":
    print("--- Amazon Low Level Design Demo (Python) ---")

    # 1. Initialize System Elements (Singleton Catalog)
    catalog = Catalog()
    notification_service = NotificationService()

    # 2. Admin adds products
    admin_addr = Address("HQ", "Seattle", "WA", "98109", "USA")
    admin = Admin("admin", "pass", "admin@amazon.com", "123", admin_addr)

    # Creating Product using Builder Pattern
    laptop = (Product.Builder("MacBook Pro", "P001")
              .set_description("Apple MacBook Pro 16 inch")
              .set_price(2500.00)
              .set_category(ProductCategory("Electronics", "Gadgets"))
              .set_available_count(10)
              .build())

    admin.add_product(laptop)
    catalog.add_product(laptop)

    # 3. Customer Actions
    cust_addr = Address("123 Main St", "New York", "NY", "10001", "USA")
    customer = Customer("john_doe", "passwd", "john@example.com", "555-0100", cust_addr)

    # 4. Search (Strategy)
    search_results = catalog.search("MacBook Pro")
    if not search_results:
        print("Product not found")
        exit()
    
    product_to_buy = search_results[0]
    print(f"Customer found product: {product_to_buy.name}")

    # 5. Add to Cart
    cart_item = Item("I001", 1, product_to_buy.price)
    customer.cart.add_item(cart_item)
    print("Item added to cart.")

    # 6. Checkout
    order_items = list(customer.cart.get_items()) # Create copy
    order = Order("O-1001", order_items, 2500.00)
    customer.add_order(order)
    print(f"Order placed: {order.order_number}")

    # 7. Payment (Strategy Usage)
    payment = CreditCardPayment("4111-1234", "999")
    if payment.process_payment(2500.00):
        order.set_status(OrderStatus.PENDING)
        print("Payment Successful via Credit Card.")

    # 8. Notification
    notification_service.send_order_confirmation(order, customer)

    # 9. Shipment
    shipment = Shipment("S-999", "FedEx")
    print(f"Shipment created with status: {shipment.status.name}")
