package com.stockbroker.lld;

import java.util.*;
import java.util.concurrent.*;

/*
 * ==============================================================================================
 * ONLINE STOCK BROKERAGE SYSTEM LOW LEVEL DESIGN
 * ==============================================================================================
 * 
 * Key Features:
 * 1. Trading: Buy/Sell stocks (Market Orders).
 * 2. Portfolio: Real-time calculation of holdings value.
 * 3. Market Data: Simulates live stock prices.
 * 4. Concurrency: Thread-safe order processing (Synchronized execution).
 * 
 * Design Patterns:
 * 1. Singleton: StockExchange (Central Market), BrokerService (Facade).
 * 2. Observer: (Optional) Notify users of price changes.
 * 3. Strategy: OrderExecutionStrategy (Market/Limit orders).
 * 
 * Class Design Diagram:
 * ---------------------
 * [BrokerService] "1" *-- "*" [User]
 * [BrokerService] "1" *-- "1" [StockExchange]
 * [User] "1" *-- "1" [Portfolio]
 * [User] "1" *-- "1" [Account] (Funds)
 * [User] "1" *-- "*" [Order]
 * [Portfolio] "1" *-- "*" [Holding]
 * [Order] <|-- [BuyOrder]
 * [Order] <|-- [SellOrder]
 *
 * Class Details:
 * ---------------------
 * 1. BrokerService (Facade)
 *    - Role: Main controller.
 *    - Methods: placeOrder(), getQuote().
 *
 * 2. StockExchange (Singleton)
 *    - Role: Simulated market.
 *    - Attributes: stocks (Symbol -> Price).
 *
 * 3. Order
 *    - Attributes: symbol, quantity, type, status.
 *    - Methods: execute().
 * 
 * 4. Account
 *    - Role: Managing cash.
 */

public class StockBrokerageSystem {
    public static void main(String[] args) {
        System.out.println("--- Stock Brokerage System Demo ---");
        
        BrokerService broker = BrokerService.getInstance();
        StockExchange exchange = StockExchange.getInstance(); // Init market

        // 1. Setup Users
        User buyer = new User("U1", "Buyer Bob");
        buyer.getAccount().deposit(2000); // Has Funds
        broker.registerUser(buyer);
        
        User seller = new User("U2", "Seller Sally");
        seller.getPortfolio().addStock("AAPL", 20); // Has Stocks
        broker.registerUser(seller);

        // 2. View Initial Market (Empty)
        broker.viewMarket("AAPL");

        // 3. Place Buy Limit Order (Bid)
        // Buyer wants 10 AAPL at $150
        System.out.println("\n[Action] Buyer Bob places Limit Buy 10 AAPL @ $150");
        Order buyOrder = new BuyOrder("AAPL", 10, 150.0);
        broker.placeOrder(buyer, buyOrder);
        
        broker.viewMarket("AAPL");

        // 4. Place Sell Limit Order (Ask) - HIGHER PRICE (No Match)
        // Seller wants to sell 5 AAPL at $155
        System.out.println("\n[Action] Seller Sally places Limit Sell 5 AAPL @ $155");
        Order sellOrderHigh = new SellOrder("AAPL", 5, 155.0);
        broker.placeOrder(seller, sellOrderHigh);
        
        broker.viewMarket("AAPL");
        
        // 5. Place Sell Limit Order (Ask) - MATCHING PRICE
        // Seller wants to sell 5 AAPL at $150 (Matches Bob)
        System.out.println("\n[Action] Seller Sally places Limit Sell 5 AAPL @ $150");
        Order sellOrderMatch = new SellOrder("AAPL", 5, 150.0);
        broker.placeOrder(seller, sellOrderMatch);
        
        // 6. Check Portfolios
        System.out.println("\n--- Post-Trade Holdings ---");
        buyer.getPortfolio().showHoldings(); // Should have 5 AAPL
        seller.getPortfolio().showHoldings(); // Should have 10 AAPL (20 - 5 - 5 pending)
        
        // 7. Cancel Order
        System.out.println("\n[Action] Seller cancels the high priced order");
        broker.cancelOrder(sellOrderHigh);
        broker.viewMarket("AAPL");
    }
}

// ==========================================
// Domain Models
// ==========================================

class Stock {
    String symbol;
    double price;
    public Stock(String s, double p) { this.symbol = s; this.price = p; }
}

class Account {
    double balance;
    public void deposit(double amt) { balance += amt; }
    public boolean withdraw(double amt) { 
        if(balance >= amt) { balance -= amt; return true; }
        return false;
    }
    public void showBalance() { System.out.println("Cash Balance: $" + balance); }
}

class Holding {
    String symbol;
    int quantity;
    public Holding(String s, int q) { this.symbol = s; this.quantity = q; }
}

class Portfolio {
    Map<String, Holding> holdings = new HashMap<>();
    
    public void addStock(String symbol, int qty) {
        Holding h = holdings.getOrDefault(symbol, new Holding(symbol, 0));
        h.quantity += qty;
        holdings.put(symbol, h);
    }
    
    public boolean removeStock(String symbol, int qty) {
        if(!holdings.containsKey(symbol) || holdings.get(symbol).quantity < qty) return false;
        Holding h = holdings.get(symbol);
        h.quantity -= qty;
        if(h.quantity == 0) holdings.remove(symbol);
        return true;
    }
    
    public void showHoldings() {
        System.out.println("Portfolio: ");
        holdings.values().forEach(h -> System.out.println(" - " + h.symbol + ": " + h.quantity));
    }
}

class User {
    String id, name;
    Account account;
    Portfolio portfolio;
    
    public User(String id, String name) {
        this.id = id; this.name = name;
        this.account = new Account();
        this.portfolio = new Portfolio();
    }
    public Account getAccount() { return account; }
    public Portfolio getPortfolio() { return portfolio; }
}

// ==========================================
// Order Book & Matching Engine
// ==========================================

class OrderBook {
    String symbol;
    // Bids (Buys): Highest price first
    PriorityQueue<Order> buyOrders = new PriorityQueue<>((a, b) -> Double.compare(b.price, a.price));
    // Asks (Sells): Lowest price first
    PriorityQueue<Order> sellOrders = new PriorityQueue<>((a, b) -> Double.compare(a.price, b.price));
    
    public OrderBook(String symbol) { this.symbol = symbol; }

    public void addOrder(Order order) {
        if (order instanceof BuyOrder) buyOrders.add(order);
        else sellOrders.add(order);
        matchOrders(); // Try to match immediately
    }
    
    public void cancelOrder(Order order) {
        if(order instanceof BuyOrder) buyOrders.remove(order);
        else sellOrders.remove(order);
        order.status = OrderStatus.CANCELLED;
        System.out.println("Cancelled Order: " + order.orderId);
    }
    
    private void matchOrders() {
        while(!buyOrders.isEmpty() && !sellOrders.isEmpty()) {
            Order bid = buyOrders.peek();
            Order ask = sellOrders.peek();
            
            if(bid.price >= ask.price) {
                // Match Found!
                int quantity = Math.min(bid.quantity, ask.quantity);
                double price = ask.price; // Usually executes at Ask price (or some midpoint)
                
                System.out.println("MATCHED: " + quantity + " " + symbol + " @ " + price);
                
                // Execute Trade (Transfer Stocks/Funds)
                executeTrade(bid, ask, quantity, price);
                
                // Update Order Quantities
                bid.quantity -= quantity;
                ask.quantity -= quantity;
                
                if(bid.quantity == 0) { buyOrders.poll(); bid.status = OrderStatus.COMPLETED; }
                if(ask.quantity == 0) { sellOrders.poll(); ask.status = OrderStatus.COMPLETED; }
            } else {
                break; // No execution possible (Spread exists)
            }
        }
    }
    
    private void executeTrade(Order buy, Order sell, int qty, double price) {
        // In real LLD, this would call clearing service.
        // For demo, we assume funds/stocks are locked/escrowed at Order Exec time.
        // We just log completion here.
        buy.user.getPortfolio().addStock(symbol, qty);
        sell.user.getAccount().deposit(qty * price); 
        // Note: Buy funds overlap handling omitted for brevity (usually locked on execution)
    }

    public void showOrderBook() {
        System.out.println("\nOrder Book [" + symbol + "]");
        System.out.println("  Bids (Buy): " + buyOrders.size());
        buyOrders.forEach(o -> System.out.println("   $" + o.price + " x " + o.quantity + " (" + o.user.name + ")"));
        System.out.println("  Asks (Sell): " + sellOrders.size());
        sellOrders.forEach(o -> System.out.println("   $" + o.price + " x " + o.quantity + " (" + o.user.name + ")"));
    }
}

// ==========================================
// Updated System (Singleton) with OrderBook
// ==========================================

class StockExchange {
    private static StockExchange instance;
    private Map<String, OrderBook> orderBooks;

    private StockExchange() {
        orderBooks = new ConcurrentHashMap<>();
        orderBooks.put("AAPL", new OrderBook("AAPL"));
    }
    
    public static synchronized StockExchange getInstance() {
        if(instance == null) instance = new StockExchange();
        return instance;
    }
    
    public void placeOrder(Order order) {
        OrderBook book = orderBooks.computeIfAbsent(order.symbol, k -> new OrderBook(k));
        book.addOrder(order);
    }
    
    public void cancelOrder(Order order) {
        OrderBook book = orderBooks.get(order.symbol);
        if(book != null) book.cancelOrder(order);
    }
    
    public void showOrderBook(String symbol) {
        OrderBook book = orderBooks.get(symbol);
        if(book != null) book.showOrderBook();
    }
}

class BrokerService {
    private static BrokerService instance;
    private StockExchange exchange;
    
    private BrokerService() { exchange = StockExchange.getInstance(); }
    
    public static synchronized BrokerService getInstance() {
        if(instance == null) instance = new BrokerService();
        return instance;
    }
    
    public void registerUser(User u) { /* Store user logic */ }
    
    // Now just forwards to Exchange matching engine
    public void placeOrder(User user, Order order) {
        // Pre-validation (Portfolio/Funds check) could happen here
        order.setUser(user);
        exchange.placeOrder(order);
    }
    
    public void cancelOrder(Order order) {
        exchange.cancelOrder(order);
    }
    
    public void viewMarket(String symbol) {
        exchange.showOrderBook(symbol);
    }
}

// ==========================================
// Updated Orders to support Limit Price
// ==========================================

enum OrderStatus { PENDING, COMPLETED, REJECTED, CANCELLED }

abstract class Order {
    String orderId;
    User user;
    String symbol;
    int quantity;
    double price; // Limit Price
    OrderStatus status;
    
    public Order(String s, int q, double p) {
        this.orderId = UUID.randomUUID().toString();
        this.symbol = s; this.quantity = q; this.price = p;
        this.status = OrderStatus.PENDING;
    }
    public void setUser(User u) { this.user = u; }
}

class BuyOrder extends Order {
    public BuyOrder(String s, int q, double p) { super(s, q, p); }
}

class SellOrder extends Order {
    public SellOrder(String s, int q, double p) { super(s, q, p); }
}
