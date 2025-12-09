package com.amazon.lld;

import java.util.*;

/*
 * ==============================================================================================
 * AMAZON LOW LEVEL DESIGN (LLD) - INTERVIEW REFERENCE
 * ==============================================================================================
 * 
 * Key Design Patterns Used:
 * 1. Singleton Pattern: Ensures valid global access to the Catalog (inventory).
 * 2. Builder Pattern: Manages complexity of creating Product objects with many optional fields.
 * 3. Strategy Pattern: Allows interchangeable algorithms for Payment and Search behavior.
 * 4. Factory Pattern (Implicit): Could be used for creating different Account types (omitted for brevity).
 *
 * SOLID Principles Applied:
 * - SRP (Single Responsibility): Each class (Order, Cart, Product) handles one domain aspect.
 * - OCP (Open/Closed): PaymentStrategy allows adding new payment methods without changing Order logic.
 * - LSP (Liskov Substitution): Customer/Admin can substitute the abstract Account class.
 * - ISP (Interface Segregation): Interfaces are focused (SearchService, PaymentStrategy).
 * - DIP (Dependency Inversion): High-level modules depend on abstractions (PaymentStrategy interface).
 */

public class AmazonSystem {
    public static void main(String[] args) {
        System.out.println("--- Amazon Low Level Design Demo ---");

        // SYSTEM INITIALIZATION
        // Singleton Access: Ensures only one instance of the catalog exists.
        Catalog catalog = Catalog.getInstance();
        NotificationService notificationService = new NotificationService();

        // -----------------------------------------------------
        // 1. ADMIN FLOW: ADDING PRODUCTS
        // -----------------------------------------------------
        Address adminAddr = new Address("HQ", "Seattle", "WA", "98109", "USA");
        Admin admin = new Admin("admin", "pass", "admin@amazon.com", "123", adminAddr);

        // PATTERN: BUILDER
        // Why? Product creation involves many optional parameters (desc, rating, etc.).
        // A constructor with 10 arguments is hard to read and sensitive to order errors.
        Product laptop = new Product.ProductBuilder("MacBook Pro", "P001")
                            .description("Apple MacBook Pro 16 inch")
                            .price(2500.00)
                            .availableItemCount(10)
                            .category(new ProductCategory("Electronics", "Gadgets"))
                            .build();

        admin.addProduct(laptop);
        catalog.addProduct(laptop); // Adding to global inventory

        // -----------------------------------------------------
        // 2. CUSTOMER FLOW: SEARCH & CART
        // -----------------------------------------------------
        Address custAddr = new Address("123 Main St", "New York", "NY", "10001", "USA");
        Customer customer = new Customer("john_doe", "passwd", "john@example.com", "555-0100", custAddr);

        // PATTERN: STRATEGY (in SearchService)
        // Catalog implements SearchService, allowing us to swap search logic (BS Tree, Hash Map, External Engine)
        // without affecting the client code.
        List<Product> searchResults = catalog.search("MacBook Pro");
        if (searchResults.isEmpty()) {
            System.out.println("Product not found");
            return;
        }
        Product productToBuy = searchResults.get(0);
        System.out.println("Customer found product: " + productToBuy.getName());

        Item cartItem = new Item("I001", 1, productToBuy.getPrice());
        customer.getShoppingCart().addItem(cartItem);
        System.out.println("Item added to cart.");

        // -----------------------------------------------------
        // 3. ORDER PLACEMENT
        // -----------------------------------------------------
        List<Item> orderItems = new ArrayList<>(customer.getShoppingCart().getItems());
        Order order = new Order("O-1001", orderItems, 2500.00);
        customer.addOrder(order);
        System.out.println("Order placed: " + order.getOrderNumber());

        // -----------------------------------------------------
        // 4. PAYMENT & NOTIFICATION
        // -----------------------------------------------------
        
        // PATTERN: STRATEGY (Payment)
        // We can easily switch this to new PaypalPayment(...) without changing the logic below.
        PaymentStrategy payment = new CreditCardPayment("4111-1111", "123");
        
        if(payment.processPayment(2500.00)) {
            // State Transition: Order moves to PENDING/CONFIRMED
            order.setStatus(OrderStatus.PENDING);
            System.out.println("Payment Successful via Credit Card.");
        }

        // Notification triggers (could be Observer pattern in a more complex setup where 
        // User 'subscribes' to OrderStatus changes)
        notificationService.sendOrderConfirmation(order, customer);

        // -----------------------------------------------------
        // 5. SHIPPING
        // -----------------------------------------------------
        Shipment shipment = new Shipment("S-999", new Date(), "FedEx");
        System.out.println("Shipment created with status: " + shipment.getStatus());
    }
}

// ==========================================
// CORE ENUMS (State Management)
// ==========================================

enum OrderStatus {
    UNSHIPPED, PENDING, SHIPPED, COMPLETED, CANCELED, REFUND_APPLIED
}

enum PaymentStatus {
    UNPAID, PENDING, COMPLETED, FILLED, DECLINED, CANCELLED, REFUNDED
}

enum ShipmentStatus {
    PENDING, SHIPPED, DELIVERED, ON_HOLD
}

enum AccountStatus {
    ACTIVE, BLOCKED, BANNED, COMPROMISED, ARCHIVED, UNKNOWN
}

// ==========================================
// DOMAIN MODELS
// ==========================================

// Value Object: Address is immutable in practice (though here fields are simplified)
class Address {
    private String streetAddress;
    private String city;
    private String state;
    private String zipCode;
    private String country;

    public Address(String streetAddress, String city, String state, String zipCode, String country) {
        this.streetAddress = streetAddress;
        this.city = city;
        this.state = state;
        this.zipCode = zipCode;
        this.country = country;
    }

    @Override
    public String toString() {
        return streetAddress + ", " + city + ", " + state + " " + zipCode + ", " + country;
    }
}

class ProductCategory {
    private String name;
    private String description;

    public ProductCategory(String name, String description) {
        this.name = name;
        this.description = description;
    }

    public String getName() { return name; }
}

/**
 * Product Class
 * Uses Builder Pattern to handle complex object construction.
 * Implements immutability effectively by using private constructor.
 */
class Product {
    private String productID;
    private String name;
    private String description;
    private double price;
    private ProductCategory category;
    private int availableItemCount;

    // Private constructor forces use of Builder
    private Product(ProductBuilder builder) {
        this.productID = builder.productID;
        this.name = builder.name;
        this.description = builder.description;
        this.price = builder.price;
        this.category = builder.category;
        this.availableItemCount = builder.availableItemCount;
    }

    public String getName() { return name; }
    public double getPrice() { return price; }
    public ProductCategory getCategory() { return category; }

    // Static Inner Builder Class
    public static class ProductBuilder {
        // Mandatory fields
        private String productID;
        private String name;
        
        // Optional fields
        private String description;
        private double price;
        private ProductCategory category;
        private int availableItemCount;

        public ProductBuilder(String name, String productID) {
            this.name = name;
            this.productID = productID;
        }

        public ProductBuilder description(String description) {
            this.description = description;
            return this;
        }
        public ProductBuilder price(double price) {
            this.price = price;
            return this;
        }
        public ProductBuilder category(ProductCategory category) {
            this.category = category;
            return this;
        }
        public ProductBuilder availableItemCount(int count) {
            this.availableItemCount = count;
            return this;
        }
        public Product build() {
            return new Product(this);
        }
    }
}

class Item {
    private String itemID;
    private int quantity;
    private double price;

    public Item(String itemID, int quantity, double price) {
        this.itemID = itemID;
        this.quantity = quantity;
        this.price = price;
    }

    public void updateQuantity(int quantity) {
        this.quantity = quantity;
    }
}

class ShoppingCart {
    private List<Item> items;

    public ShoppingCart() {
        this.items = new ArrayList<>();
    }

    public void addItem(Item item) {
        this.items.add(item);
    }
    
    public List<Item> getItems() {
        return items;
    }
}

class Order {
    private String orderNumber;
    private OrderStatus status;
    private Date orderDate;
    private List<Item> items;
    private double totalAmount;

    public Order(String orderNumber, List<Item> items, double totalAmount) {
        this.orderNumber = orderNumber;
        this.items = items;
        this.totalAmount = totalAmount;
        this.orderDate = new Date();
        this.status = OrderStatus.PENDING;
    }

    public void setStatus(OrderStatus status) {
        this.status = status;
        // In a real system, setting status might notify observers (User, Warehouse)
    }
    
    public String getOrderNumber() { return orderNumber; }
    
    @Override
    public String toString() {
        return "Order #" + orderNumber;
    }
}

class Shipment {
    private String shipmentNumber;
    private Date shipmentDate;
    private String shipmentMethod;
    private ShipmentStatus status;

    public Shipment(String shipmentNumber, Date shipmentDate, String shipmentMethod) {
        this.shipmentNumber = shipmentNumber;
        this.shipmentDate = shipmentDate;
        this.shipmentMethod = shipmentMethod;
        this.status = ShipmentStatus.PENDING;
    }

    public ShipmentStatus getStatus() { return status; }
}

/**
 * Account - Abstract Base Class
 * Supports Open/Closed Principle. New account types (e.g. Vendor, PrimeMember) 
 * can be added by extending this class without modifying existing code.
 */
abstract class Account {
    private String userName;
    private String password;
    private AccountStatus status;
    protected String email;
    private String phone;
    private Address shippingAddress;

    public Account(String userName, String password, String email, String phone, Address address) {
        this.userName = userName;
        this.password = password;
        this.email = email;
        this.phone = phone;
        this.shippingAddress = address;
        this.status = AccountStatus.ACTIVE;
    }

    public String getEmail() { return email; }
}

class Customer extends Account {
    private ShoppingCart cart;
    private List<Order> orders;

    public Customer(String userName, String password, String email, String phone, Address address) {
        super(userName, password, email, phone, address);
        this.cart = new ShoppingCart();
        this.orders = new ArrayList<>();
    }

    public ShoppingCart getShoppingCart() { return cart; }
    public void addOrder(Order order) { orders.add(order); }
}

class Admin extends Account {
    public Admin(String userName, String password, String email, String phone, Address address) {
        super(userName, password, email, phone, address);
    }

    public void addProduct(Product product) {
        // Admin specific logic for adding products
        System.out.println("Admin adding product: " + product.getName());
    }
}

// ==========================================
// SERVICES & INTERFACES
// ==========================================

/**
 * Interface Segregation Principle:
 * Clients depend on specific interfaces (SearchService) rather than a monolithic class.
 */
interface SearchService {
    List<Product> search(String query);
}

/**
 * Singleton Pattern
 * Why? We need a single source of truth for the Product Catalog in memory.
 * Thread Safety: 'synchronized' ensures two threads don't create duplicate instances.
 */
class Catalog implements SearchService {
    private static Catalog instance;
    private Map<String, List<Product>> productNames;

    // Private constructor prevents direct instantiation
    private Catalog() {
        productNames = new HashMap<>();
    }

    public static synchronized Catalog getInstance() {
        if (instance == null) {
            instance = new Catalog();
        }
        return instance;
    }

    public void addProduct(Product product) {
        productNames.computeIfAbsent(product.getName(), k -> new ArrayList<>()).add(product);
    }

    @Override
    public List<Product> search(String query) {
        return productNames.containsKey(query) ? productNames.get(query) : new ArrayList<>();
    }
}

/**
 * Strategy Pattern
 * Encapsulates a family of algorithms (Payment methods) and makes them interchangeable.
 * The Client (Order processing) doesn't need to know the details of Paypal vs CreditCard.
 */
interface PaymentStrategy {
    boolean processPayment(double amount);
}

class CreditCardPayment implements PaymentStrategy {
    private String cardNumber;
    private String cvv;

    public CreditCardPayment(String cardNumber, String cvv) {
        this.cardNumber = cardNumber;
        this.cvv = cvv;
    }

    @Override
    public boolean processPayment(double amount) {
        System.out.println("Processing Credit Card Payment of $" + amount);
        return true;
    }
}

class NotificationService {
    public void sendOrderConfirmation(Order order, Account account) {
        System.out.println("Email sent to " + account.getEmail() + " for Order " + order);
    }
}
