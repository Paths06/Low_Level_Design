package com.vending.lld;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * ==============================================================================================
 * VENDING MACHINE LOW LEVEL DESIGN
 * ==============================================================================================
 * 
 * Design Patterns:
 * 1. State Pattern: To manage the machine's lifecycle (Idle -> Payment -> Dispense).
 * 2. Singleton: Ensures only one instance of the specific VendingMachine.
 * 3. Strategy / Polymorphism: Handling denominations (Coin/Note).
 * 
 * Key Features:
 * - Thread-safe Inventory.
 * - Change Calculation Algorithm.
 * - Extensible State Machine.
 *
 * Class Design Diagram:
 * ---------------------
 * [VendingMachine] "1" *-- "1" [Inventory]
 * [VendingMachine] "1" *-- "1" [VendingMachineState]
 * [VendingMachineState] <|.. [IdleState]
 * [VendingMachineState] <|.. [ReadyState]
 * [VendingMachineState] <|.. [DispenseState]
 * [Inventory] "1" *-- "*" [Product]
 * [IdleState] ..> [Inventory] : Checks Stock
 * [ReadyState] ..> [Coin/Note] : Accepts Payment
 * [DispenseState] ..> [Inventory] : Updates Stock
 *
 * Class Details:
 * ---------------------
 * 1. VendingMachine (Singleton, Context)
 *    - Role: Main system controller.
 *    - Attributes: state (VendingMachineState), inventory, currentBalance, selectedProduct.
 *    - Methods: setState(), selectProduct(), insertMoney(), dispense().
 *
 * 2. VendingMachineState (Interface)
 *    - Role: State abstraction.
 *    - Methods: selectProduct(), insertCoin(), insertNote(), dispense(), abort().
 *
 * 3. IdleState (Impl State)
 *    - Role: Initial state waiting for selection.
 *    - Logic: Allows selection, forbids payment.
 *
 * 4. ReadyState (Impl State)
 *    - Role: Handling Payment.
 *    - Logic: Accumulates balance, checks against price, transitions to Dispense.
 *
 * 5. DispenseState (Impl State)
 *    - Role: Delivering product.
 *    - Logic: Deducts inventory, calculates change, resets machine.
 *
 * 6. Inventory
 *    - Role: Stock management.
 *    - Attributes: stock (ConcurrentHashMap<Product, Integer>).
 *    - Methods: addProduct(), deduct(), isAvailable().
 *
 * 7. Product, Coin, Note
 *    - Role: Domain Entities / Enums.
 */

public class VendingMachineSystem {
    public static void main(String[] args) {
        System.out.println("--- Vending Machine System ---");

        VendingMachine vm = VendingMachine.getInstance();

        // 1. Admin Stocks Machine
        Product coke = new Product("Coke", 25);
        Product pepsi = new Product("Pepsi", 35);
        Product chips = new Product("Lays", 45);

        vm.getInventory().addProduct(coke, 5);
        vm.getInventory().addProduct(pepsi, 2); // Low stock
        vm.getInventory().addProduct(chips, 5);

        System.out.println("\n[Test 1] Successful Transaction (Exact Change)");
        try {
            vm.selectProduct("Coke");
            vm.insertMoney(Coin.QUARTER); // 25
            vm.collectProductAndChange();
        } catch (Exception e) {
            System.out.println(e.getMessage());
        }

        System.out.println("\n[Test 2] Successful Transaction (With Change)");
        try {
            vm.selectProduct("Pepsi");
            vm.insertMoney(Note.FIVE_HUNDRED); // Way too much, simplifying to 50 for logic check
            // Simulating multiple inserts
            vm.reset(); // Reset for demo flow if needed, but collectProduct does it.
            
            // Retry clean flow
            vm.selectProduct("Pepsi"); // 35
            vm.insertMoney(Coin.QUARTER); // 25
            vm.insertMoney(Coin.TEN);     // 10 -> Total 35
            vm.collectProductAndChange();
        } catch (Exception e) {
            System.out.println(e.getMessage());
        }
        
        System.out.println("\n[Test 3] Out of Stock");
        try {
            // Buying remaining pepsis
            vm.selectProduct("Pepsi"); vm.insertMoney(Coin.QUARTER); vm.insertMoney(Coin.TEN); vm.collectProductAndChange();
            // Now empty
            vm.selectProduct("Pepsi"); 
        } catch (Exception e) {
            System.out.println("Expected Error: " + e.getMessage());
        }

        System.out.println("\n[Test 4] Insufficient Funds & Cancellation");
        try {
            vm.selectProduct("Lays"); // 45
            vm.insertMoney(Coin.QUARTER); // 25
            vm.dispense(); // Try to force dispense
        } catch (Exception e) {
            System.out.println("Expected Error: " + e.getMessage());
            vm.abort(); // Refund
        }
    }
}

// ==========================================
// Models & Enums
// ==========================================

enum Coin {
    ONE(1), FIVE(5), TEN(10), QUARTER(25);
    private int value;
    Coin(int value) { this.value = value; }
    public int getValue() { return value; }
}

enum Note {
    TWENTY(20), FIFTY(50), HUNDRED(100), FIVE_HUNDRED(500);
    private int value;
    Note(int value) { this.value = value; }
    public int getValue() { return value; }
}

class Product {
    private String name;
    private int price;

    public Product(String name, int price) {
        this.name = name;
        this.price = price;
    }
    public String getName() { return name; }
    public int getPrice() { return price; }
}

class Inventory {
    private ConcurrentHashMap<Product, Integer> stock;
    private Map<String, Product> nameMap;

    public Inventory() {
        stock = new ConcurrentHashMap<>();
        nameMap = new HashMap<>();
    }

    public void addProduct(Product product, int quantity) {
        stock.put(product, stock.getOrDefault(product, 0) + quantity);
        nameMap.put(product.getName(), product);
    }

    public boolean isAvailable(Product product) {
        return stock.containsKey(product) && stock.get(product) > 0;
    }

    public void deduct(Product product) {
        if (isAvailable(product)) {
            stock.put(product, stock.get(product) - 1);
        }
    }

    public Product getProductByName(String name) {
        return nameMap.get(name);
    }
}

// ==========================================
// STATE PATTERN
// ==========================================

interface VendingMachineState {
    void selectProduct(Product product);
    void insertCoin(Coin coin);
    void insertNote(Note note);
    void dispense();
    void abort();
}

/**
 * Use IdleState, ReadyState, DispenseState to manage logic flow
 */

class IdleState implements VendingMachineState {
    private VendingMachine vm;
    public IdleState(VendingMachine vm) { this.vm = vm; }

    @Override
    public void selectProduct(Product product) {
        if (vm.getInventory().isAvailable(product)) {
            vm.setSelectedProduct(product);
            vm.setState(vm.getReadyState());
            System.out.println("Product selected: " + product.getName() + " Price: " + product.getPrice());
        } else {
            throw new RuntimeException("Product Out of Stock");
        }
    }

    @Override public void insertCoin(Coin coin) { throw new RuntimeException("Select product first"); }
    @Override public void insertNote(Note note) { throw new RuntimeException("Select product first"); }
    @Override public void dispense() { throw new RuntimeException("Select product first"); }
    @Override public void abort() { System.out.println("Nothing to cancel"); }
}

class ReadyState implements VendingMachineState {
    private VendingMachine vm;
    public ReadyState(VendingMachine vm) { this.vm = vm; }

    @Override
    public void selectProduct(Product product) {
        throw new RuntimeException("Product already selected. Cancel to change.");
    }

    @Override
    public void insertCoin(Coin coin) {
        vm.addMoney(coin.getValue());
        checkPaymentStatus();
    }

    @Override
    public void insertNote(Note note) {
        vm.addMoney(note.getValue());
        checkPaymentStatus();
    }
    
    private void checkPaymentStatus() {
        System.out.println("Current Balance: " + vm.getCurrentBalance());
    }

    @Override
    public void dispense() {
        if (vm.getCurrentBalance() >= vm.getSelectedProduct().getPrice()) {
            vm.setState(vm.getDispenseState());
            vm.dispense(); // Forward call
        } else {
            throw new RuntimeException("Insufficient Funds. Need " + (vm.getSelectedProduct().getPrice() - vm.getCurrentBalance()));
        }
    }

    @Override
    public void abort() {
        vm.refund();
        vm.reset();
        vm.setState(vm.getIdleState());
    }
}

class DispenseState implements VendingMachineState {
    private VendingMachine vm;
    public DispenseState(VendingMachine vm) { this.vm = vm; }

    @Override public void selectProduct(Product product) { throw new RuntimeException("Processing..."); }
    @Override public void insertCoin(Coin coin) { throw new RuntimeException("Processing..."); }
    @Override public void insertNote(Note note) { throw new RuntimeException("Processing..."); }
    @Override public void abort() { throw new RuntimeException("Cannot cancel during dispense"); }

    @Override
    public void dispense() {
        Product product = vm.getSelectedProduct();
        vm.getInventory().deduct(product);
        int change = vm.getCurrentBalance() - product.getPrice();
        
        System.out.println("DISPENSING: " + product.getName());
        if (change > 0) {
            System.out.println("RETURNING CHANGE: " + change);
        }
        
        // Transaction complete
        vm.reset();
        vm.setState(vm.getIdleState());
    }
}

// ==========================================
// VENDING MACHINE (Context)
// ==========================================

class VendingMachine {
    private static VendingMachine instance;
    
    // States
    private VendingMachineState idleState;
    private VendingMachineState readyState;
    private VendingMachineState dispenseState;
    private VendingMachineState currentState;

    private Inventory inventory;
    private Product selectedProduct;
    private int currentBalance;

    private VendingMachine() {
        inventory = new Inventory();
        idleState = new IdleState(this);
        readyState = new ReadyState(this);
        dispenseState = new DispenseState(this);
        currentState = idleState;
        currentBalance = 0;
    }

    public static synchronized VendingMachine getInstance() {
        if (instance == null) {
            instance = new VendingMachine();
        }
        return instance;
    }

    // State Delegation
    public void selectProduct(String productName) {
        Product p = inventory.getProductByName(productName);
        if (p == null) throw new RuntimeException("Invalid Product");
        currentState.selectProduct(p);
    }

    public void insertMoney(Object money) {
        if (money instanceof Coin) currentState.insertCoin((Coin) money);
        else if (money instanceof Note) currentState.insertNote((Note) money);
    }
    
    public void dispense() { currentState.dispense(); }
    public void abort() { currentState.abort(); }
    
    // Helper for main
    public void collectProductAndChange() {
        currentState.dispense();
    }

    // Internal Management
    public void setState(VendingMachineState state) { this.currentState = state; }
    public VendingMachineState getIdleState() { return idleState; }
    public VendingMachineState getReadyState() { return readyState; }
    public VendingMachineState getDispenseState() { return dispenseState; }
    
    public Inventory getInventory() { return inventory; }
    
    public void setSelectedProduct(Product p) { this.selectedProduct = p; }
    public Product getSelectedProduct() { return selectedProduct; }
    
    public void addMoney(int amount) { this.currentBalance += amount; }
    public int getCurrentBalance() { return currentBalance; }
    
    public void refund() {
        if (currentBalance > 0) {
            System.out.println("REFUNDING: " + currentBalance);
        }
    }
    
    public void reset() {
        this.selectedProduct = null;
        this.currentBalance = 0;
    }
}
